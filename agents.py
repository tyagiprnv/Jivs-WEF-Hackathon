from sentence_transformers import SentenceTransformer
import chromadb
from xmlschema import XMLSchema
import sqlglot
import xml.etree.ElementTree as ET
from typing import List, Dict
import os
import ast
import re
import json

#MAIN AGENT
class TaskDetectingAgent:
    
    def __init__(self, client, schema_file = "data/schema.txt"):
        self.llm = client
        with open(schema_file, 'r') as infile:
            schema = infile.read()
            
        self.task_detector_convo = [{
            "role":"system",
            "content":f"""
            You are an intelligent Database AI assistant.
            This is our database schema: {schema}
            Your main task is classify the user prompt into either of the two sepcific task:
                - IMP view : Provide a link to the view/table on a database requested by the user. If the user wants to look at the data of a table/view, this task needs to be selected. This will call the function link_generator.
                - Business Object Creation : Generate the SQL query requested by the user. This will call the function sql_generator.
            Make sure you follow these steps:
                1. Plan first : Decide which one of the two task is needed to be performed. In case the table is not in our schema, mention the available tables.
                2. Return only one function call that needs to be called based on the task.
                3. Assume the reponse by the functions is accurate and up-to-date.
            """
        }]
        
        self.tools = [
            {
                "type" : "function",
                "function":
                    {
                    "name": "link_generator",
                    "description": """Task is to fetch the URL for the view/table based on user request. This function retrives the link to a view/table on a database.
                    Fetch valid links for views from given a user request.""",
                    "parameters":
                        {
                        "type": "object",
                        "properties":
                            {
                                "prompt":
                                    {
                                        "type": "string",
                                        "description": "The prompt required to fetch required view link"
                                    }
                            },
                        "required": ["prompt"]
                        }
                    }
            },
            {
                "type" : "function",
                "function":
                    {
                        "name": "sql_generator",
                        "description": """Task is to create business objects that simplifies and automates the creation of SQL queries and their XML files.
                        This function is focused on generating SQL queries and converting them to an XML.
                        Generate valid SQL queries given a user request.""",
                        "parameters":
                            {
                                "type": "object",
                                "properties": 
                                    {
                                        "prompt": 
                                            {
                                                "type": "string",
                                                "description": "The prompt required to generate SQL query"
                                            }
                                    },
                                "required": ["prompt"]
                            }
                    }
            }
]
    
    def generate_response(self, user_query):
        
        self.task_detector_convo.append({"role": "user", "content": user_query})
        
        response = self.llm.chat.completions.create(
            model = "gpt-4o-mini",  
            messages=self.task_detector_convo,
            tools = self.tools
        )
        if response.choices[0].finish_reason == "tool_calls":
            assistant_response = {
                "role":"assistant",
                "content":f"Calling Function",
                "tool_calls": [{"id":response.choices[0].message.tool_calls[0].id,
                                "type":"function",
                                "function":{"arguments":str(user_query),
                                            "name":response.choices[0].message.tool_calls[0].function.name }}]
                    }
        else:
            assistant_response =  {"role": "assistant", "content": response.choices[0].message.content}
            
        self.task_detector_convo.append(assistant_response)
        
        return response.choices[0]
    
class SemanticSearch:
    def __init__(self, persist_dir: str = "chroma_db"):
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        self.client = chromadb.PersistentClient(path=persist_dir)
        self.collection = self.client.get_collection(name="views")
    
    def find_relevant_views(self, query: str, top_k: int = 2) -> List[Dict]:
        query_embedding = self.model.encode([query]).tolist()
        results = self.collection.query(
            query_embeddings=query_embedding,
            n_results=top_k
        )

        relevant_views = []
        if results and results.get("metadatas") and results["metadatas"][0]:
            for i in range(len(results["ids"][0])):
                view_name = results["metadatas"][0][i].get("view_name")
                fields_str = results["metadatas"][0][i].get("fields")
                if view_name and fields_str:
                    try:
                        fields = ast.literal_eval(fields_str)
                        relevant_views.append({
                            "view_name": view_name,
                            "fields": fields
                        })
                    except (ValueError, SyntaxError) as e:
                        print(f"Error parsing fields: {e}")
        else:
            print("No relevant views found or metadata is missing.")

        return relevant_views
    
class EasyNavAgent:
    
    def __init__(self, client, search_system: SemanticSearch):
        
        self.search_system = search_system
        self.llm = client
        self.nagivation_conversation = [
            {"role": "system", 
             "content": """You are a SQL expert and a helpful assistant for the JIVS IMP system. 
             Your task is to help users find the correct view/table.
             Please follow the following steps:
                - Based on the Available views and the fields of the views you get, select the view you find the most relevant according to the user query.
                - If you are unsure about the user's query, ask clarifying questions.
                - Only return one view name when you are confident about the correct view.
                - If confident, strictly follow this reponse format:
                    view, confident
                - Do not return any additional information
                - If the user hints at aborting or cancelling his request, strictly respond quit."""}]
    
    def generate_response(self, prompt: str) -> str:
        
        relevant_views = self.search_system.find_relevant_views(prompt)
        
        prompt = f"""User query: {prompt}
        
        Available views:
        {[v['view_name'] for v in relevant_views]}
        
        Fields in views:
        {[v['fields'] for v in relevant_views]}
        
        Please follow the following steps:
            - Based on the Available views and the fields of the views you get, select the view you find the most relevant according to the user query.
            - If you are unsure about the user's query, ask clarifying questions.
            - Only return one view name when you are confident about the correct view.
            - If confident, strictly follow this reponse format:
                view, confident
            - Do not return any additional information"""
        
        # print(prompt)
        
        self.nagivation_conversation.append({"role": "user", "content": prompt})
        
        response = self.llm.chat.completions.create(
            model="gpt-4o-mini",  
            messages=self.nagivation_conversation
        )
        response_content = response.choices[0].message.content
        # print(response_content)

        if "confident" in str(response_content).lower():
            view_name = str(response_content).split(',')[0]
            print(view_name)
            if view_name:
                url = self.generate_url(view_name)
                print("Generated URL:", url)
                # response_content = f"Here's the link to the related view: {url}"
                response_content = url
            else:
                print("Could not extract a valid view name from the response.")
        else:
            print("The chatbot is unsure. Please provide more details or clarify your query.")
        
        self.nagivation_conversation.append({"role": "assistant", "content": response_content})
        
        return response_content
    
    def generate_url(self, view_name: str) -> str:
        return f"https://wef2025.cloud.jivs.com/jivs/getSearchForm.do?viewName={view_name}&packageName=sap.ecc60kjl"

    def extract_view_name(self, response: str) -> str:
        match = re.search(r"\.([A-Za-z0-9]+)\.", response) 
        if match:
            return match.group(1)  
        return None
    
class SQLXMLGenAgent:
    
    def __init__(self, client, schema_file = "data/schema.txt"):
        self.llm = client
        with open(schema_file, 'r') as infile:
            schema = infile.read()
            
        self.sql_gen_messages = [{
            "role": "system",
            "content": f'''You are a SQL expert. Your task is to generate valid SQL queries based on user requests. You do not respond to anything else. You just generate valid executable SQL queries.
            Given an input question, create a syntactically correct SQL query. Do not provide any explanation.
            Database Schema: {schema}
            Follow these steps:
                1. Check for Table Name:
                    - Identify if the user has specified a table name.
                    - If the user has not given a table name, or if the provided table name is not in the known schema, ask the user to choose a table name from the valid table list.
                2. Check for Required Columns and Conditions:
                    - Identify the columns or attributes the user wants to select, filter on, group by, or order by.
                    - If the user hasn't specified which columns to select, then select all columns by default.
                    - If the user hasn't specified conditions clearly (e.g., they say “get me the info” without specifying which fields), ask the user to clarify.
                    - If the user mentions columns that don't exist in the selected table, ask them to confirm or correct the column names by giving them the list of columns.
                3. Check the join or merge conditions:
                    - If the columns to join or merge are not mentioned (e.g. they say "merge tables A and B"), then using the schema of the tables, strictly respond with the name of the columns on which these tables can be joined.
                    - If the join type is not mentioned, ask the user to clarify which type of join they need.
                4. Check for Missing or Ambiguous Details: 
                    - Does the user want any filtering (e.g., a WHERE clause)? If yes, but they haven't provided the filter details (e.g., “get data from table X after a certain date” without specifying the date), prompt them to clarify.
                    - Do they mention any aggregation or grouping (e.g., “sum of sales”)? If so, ensure that group-by columns and aggregate functions are specified. If not, ask for clarification.
                    - Do they mention any ordering or limiting requirements (e.g., “sort by price,” or “top 10 results”)? If so, verify you have all the details (column name for ordering, the limit number, etc.). If unclear, ask for more information.
                5. Ask Clarifying Questions if Needed:
                    - If any crucial piece of information is missing or ambiguous (table name, columns, filters, groupings, etc.), ask only for that missing or ambiguous information.
                    - Do not proceed to generate a SQL query if you do not have enough information.
                6. Generate the SQL Query:
                    - Once you have confirmed the table name is valid and all required details are present, generate the SQL query in the correct SQL syntax.
                    - Ensure the query is as concise as possible and accurately reflects the user's requirements.
                    - Only respond with the query and do not provide any extra information.
                7. Final Response Format:
                    - If you have enough information: Return only one SQL query as a text. No other information.
                    - If you do not have enough information: Return a clarifying question or list of questions to the user, asking them to specify the missing details.
                8. If the user hints at aborting or cancelling his request, strictly respond quit.
            Only return one SQL query as text or the question you want to ask or quit if the user wants to cancel or change his request. Do not provide any additional explantion or information''' 
            }]
    
    def generate_response(self, prompt):
        
        self.sql_gen_messages.append({"role": "user", "content": prompt})
        
        response = self.llm.chat.completions.create(
            model = "gpt-4o-mini",  
            messages = self.sql_gen_messages
        )
        
        self.sql_gen_messages.append({"role": "assistant", "content": response.choices[0].message.content})
        # print(self.sql_gen_messages)
        return response.choices[0].message.content

class SQLtoXML:
    
    def __init__(self, client):
    
        self.llm = client
        self.mapping_sql_xmlschema = {'select': 'SqlFunctions', 'all_tables': 'TableObjects', 'all_joins': 'StaticJoinOptions', 'individual_joins': 'Joins', 'where': 'ValueFilters', 'order': 'SortOptions', 'group': 'AggregateOptions'}
        self.schema_dict = XMLSchema.meta_schema.decode("config/standard.xsd")
        self.components_schema = {}
        for i, sch in enumerate(self.schema_dict['xs:complexType']):
            self.components_schema[sch['@name']] = self.schema_dict['xs:complexType'][i]
    
    def ask_gpt(self, msg):
        completion = self.llm.chat.completions.create(
            model="gpt-4o", 
            messages=[{"role": "user", "content": msg}])
        
        result = completion.choices[0].message.content.split(",")
        
        return result[0]
        
    def get_sql(self, filepath):
        try:
            with open(filepath, 'r', encoding='utf-8') as file:
                return file.read()
        except FileNotFoundError:
            return "The file could not be found."
        except Exception as e:
            return f"An error occurred: {str(e)}"
    
    def is_well_formed(self, xml_text):
        try:
            ET.fromstring(xml_text)
            return True
        except ET.ParseError as e:
            # print(f"Regenerating Bad xml")
            return False
    
    def get_selects(self, vals):
        
        if vals is None:
            return 'NA'
        select_xsd = self.components_schema[self.mapping_sql_xmlschema['select']]
        msg = f'''For a given SQL SELECT clause and xsd definition as json
        {select_xsd}
        write the xml entries only with case sensitive tags. Please do not provide any explanations. Do not specify xml anywhere.
    
        {vals}
        '''
        resp = self.ask_gpt(msg)
        return resp

    def get_distincts(self, vals):
        if vals is None:
            return False
        return True

    def get_TableObjects(self, vals):
        if vals is None:
            return False
        TableObjects_xsd = self.components_schema[self.mapping_sql_xmlschema['all_tables']]
        msg = f'''For a given table names: {vals.split(' ')}.
        And xsd definition as json
        {TableObjects_xsd}
        write the xml entries only with case sensitive tags. Please do not provide any explanations. Do not specify xml anywhere.
        '''
        resp = self.ask_gpt(msg)
        return resp

    def get_joins(self, vals):
        
        if vals is None:
            return False
        staticJoin_xsd = self.components_schema[self.mapping_sql_xmlschema['all_joins']]
        individual_xsd = self.components_schema[self.mapping_sql_xmlschema['individual_joins']]
        msg = f'''For a given SQL JOIN clauses and xsd definition as json
        {staticJoin_xsd} and {individual_xsd}
        write the xml entries only with case sensitive tags. Please do not provide any explanations. Do not specify xml anywhere.
    
        {vals}
        '''
        resp = self.ask_gpt(msg)
        return resp

    def get_where(self, vals):
        if vals is None:
            return False
        where_xsd = self.components_schema[self.mapping_sql_xmlschema['where']]
        msg = f'''For a given SQL WHERE clause and xsd definition as json
        {where_xsd}
        write the xml entries only with case sensitive tags. Please do not provide any explanations. Do not specify xml anywhere.
    
        {vals}
        '''
        resp = self.ask_gpt(msg)
        return resp

    def get_order(self, vals):
        if vals is None:
            return False
        order_xsd = self.components_schema[self.mapping_sql_xmlschema['order']]
        msg = f'''For a given SQL ORDER BY clause and xsd definition as json
        {order_xsd}
        write the xml entries only with case sensitive tags. Please do not provide any explanations. Do not specify xml anywhere.
    
        {vals}
        '''
        resp = self.ask_gpt(msg)
        return resp
    
    def get_group(self, vals):
        if vals is None:
            return False
        group_xsd = self.components_schema[self.mapping_sql_xmlschema['group']]
        msg = f'''For a given SQL GROUP BY clause and xsd definition as json
        {group_xsd}
        write the xml entries only with case sensitive tags. Please do not provide any explanations. Do not specify xml anywhere.
    
        {vals}
        '''
        resp = self.ask_gpt(msg)
        return resp
        
    def generate_child_xmls(self, sql):
        parsed = sqlglot.parse_one(sql)
        parsed_dict = parsed.args
        components = {}
        
        flag = True
        resp = None
        while flag:
            resp = self.get_selects(parsed_dict['expressions']).replace("```","").replace("xml","")
            if self.is_well_formed(resp):
                flag = False
                components['select'] = resp
        
        components['distinct'] = False if parsed_dict['distinct'] is None else True
        
        qsn = f"List all tables used in this sql :{sql}. Return only table names separated by single whitespace in that same order mentioned. Do not provide any explanations."
        all_tables_involved = self.ask_gpt(qsn)
        flag = True
        resp = None
        while flag:
            resp = self.get_TableObjects(all_tables_involved).replace("```","").replace("xml","")
            if self.is_well_formed(resp):
                flag = False
                components['all_tables'] = resp 
        
        flag = True
        resp = None
        while flag:
            if 'joins' not in parsed_dict.keys():
                flag = False
                continue
            resp = self.get_joins(parsed_dict['joins']).replace("```","").replace("xml","")
            if self.is_well_formed(resp):
                flag = False
                components['staticJoinOption'] = resp
        
        flag = True
        resp = None
        while flag:
            if 'where' not in parsed_dict.keys():
                flag = False
                continue
            resp = self.get_joins(parsed_dict['where']).replace("```","").replace("xml","")
            if self.is_well_formed(resp):
                flag = False
                components['where'] = resp
        
        flag = True
        resp = None
        while flag:
            if 'order' not in parsed_dict.keys():
                flag = False
                continue
            resp = self.get_joins(parsed_dict['order']).replace("```","").replace("xml","")
            if self.is_well_formed(resp):
                flag = False
                components['order'] = resp
                
        flag = True
        resp = None
        while flag:
            if 'group' not in parsed_dict.keys():
                flag = False
                continue
            resp = self.get_group(parsed_dict['group']).replace("```","").replace("xml","")
            if self.is_well_formed(resp):
                flag = False
                components['group'] = resp
        
        return components
    
    def get_view_details(self):
        with open("config/view.json", 'r') as json_file:
            data = json.load(json_file)
            return data['viewName'], data['viewDesc']
    
    def create_final_xml(self, sql, child_xml):
        ns = self.schema_dict['@xmlns:xs']
        ET.register_namespace("@xmlns:xs", ns)
        if 'join' not in sql.lower():
            root = ET.Element("BusinessObjectSingle")
        else:
            root = ET.Element("BusinessObjectJoined")
        
        # Get view detail from user input saved in view.json
        viewName, viewDesc = self.get_view_details()
        # Add elements now
        BusinessObjectName = viewName
        BusinessObjectType = 'JOINED' if 'join' in sql.lower() else 'SINGLE'
        BusinessObjectDescription = viewDesc
        iso_lang = ['de', 'en', 'es', 'fr', 'pt']
        IsoText = {}
        IsoText['en'] = BusinessObjectDescription
        for i in iso_lang:
            msg = f"Translate this text into {i} language as it is without extra explanation. Provide only the translation and not other description or explanation.\n{BusinessObjectDescription}"
            IsoText[i] = self.ask_gpt(msg)
            
        BusinessObjectInMenue = 'true'
        ModuleName = 'FI-AP'
        viewReferenceName = BusinessObjectName
        viewReferenceTargetUrl = f"https://wef2025.cloud.jivs.com/jivs/getSearchForm.do?viewName={BusinessObjectName}&packageName=sap.ecc60kjl"
        viewReferenceTargetViewName = f'viewName={BusinessObjectName}'
        UseTheDistinctClauseInSqlSelectQuery = str(child_xml['distinct']).lower()
        
        # Create the Tree now
        ET.SubElement(root, "BusinessObjectName").text = BusinessObjectName
        ET.SubElement(root, "BusinessObjectType").text = BusinessObjectType
        bot = ET.SubElement(root, "BusinessObjectText")
        for i in iso_lang:
            isotext = ET.SubElement(bot, "IsoText")
            ET.SubElement(isotext, "IsoCode").text = i
            ET.SubElement(isotext, "Text").text = IsoText[i]
            
        bost = ET.SubElement(root, "BusinessObjectShortText")
        for i in iso_lang:
            isotext = ET.SubElement(bost, "IsoText")
            ET.SubElement(isotext, "IsoCode").text = i
            ET.SubElement(isotext, "Text").text = IsoText[i]
            
        bodesc = ET.SubElement(root, "BusinessObjectDescr")
        for i in iso_lang:
            isotext = ET.SubElement(bodesc, "IsoText")
            ET.SubElement(isotext, "IsoCode").text = i
            ET.SubElement(isotext, "Text").text = IsoText[i]
            
        ET.SubElement(root, "BusinessObjectInMenue").text = BusinessObjectInMenue
        ET.SubElement(root, "ModuleName").text = ModuleName
        
        vr = ET.SubElement(root, "viewReference")
        ET.SubElement(vr, "viewReferenceName").text = viewReferenceName
        vrt = ET.SubElement(vr, "viewReferenceText")
        for i in iso_lang:
            isotext = ET.SubElement(vrt, "IsoText")
            ET.SubElement(isotext, "IsoCode").text = i
            ET.SubElement(isotext, "Text").text = IsoText[i]
        vrd = ET.SubElement(vr, "viewReferenceDescription")
        for i in iso_lang:
            isotext = ET.SubElement(vrd, "IsoText")
            ET.SubElement(isotext, "IsoCode").text = i
            ET.SubElement(isotext, "Text").text = IsoText[i]
        ET.SubElement(vr, "viewReferenceTargetUrl").text = viewReferenceTargetUrl
        ET.SubElement(vr, "viewReferenceTargetViewName").text = viewReferenceTargetViewName
        
        sqlFunction = ET.fromstring(child_xml['select'].replace('\n', '').strip())
        root.append(sqlFunction)
        
        ET.SubElement(root, "UseTheDistinctClauseInSqlSelectQuery").text = UseTheDistinctClauseInSqlSelectQuery
        
        TableObjects = ET.fromstring(child_xml['all_tables'].replace('\n', '').strip())
        root.append(TableObjects)
        
        if BusinessObjectType == "JOINED":
            staticJoinOptions = ET.fromstring(child_xml['staticJoinOption'].replace('\n', '').strip())
            root.append(staticJoinOptions)
        
        if 'where' in child_xml.keys():
            valueFilters = ET.fromstring(child_xml['where'].replace('\n', '').strip())
            root.append(valueFilters)
        
        if 'order' in child_xml.keys():
            sortOptions = ET.fromstring(child_xml['order'].replace('\n', '').strip())
            root.append(sortOptions)
            
        if 'group' in child_xml.keys():
            aggregateOptions = ET.fromstring(child_xml['group'].replace('\n', '').strip())
            root.append(aggregateOptions)
        
        return root
    
    def convert_sql_to_xml(self):
        
        viewName, _ = self.get_view_details()
        sql = self.get_sql(f"config/{viewName}.sql")
        child_xml_dict = self.generate_child_xmls(sql)

        rt = self.create_final_xml(sql, child_xml_dict)
        tree = ET.ElementTree(rt) 
        
        output_xml_file = f"config\{viewName}.xml"
        tree.write(output_xml_file, encoding="utf-8", xml_declaration=True)
        current_wd = os.getcwd()
        return os.path.join(current_wd, output_xml_file)
        
        
    
    

# def generate_sql(user_input, api_key):
#     client = OpenAI(api_key= api_key)
#     message = {"role": "user", "content": user_input}
#     convo.append(message)
#     response = client.chat.completions.create(
#     model = "gpt-4o-mini",
#     messages = convo,
#     stream = False
#     )
#     convo.append(response.choices[0].message)
#     return response.choices[0].message.content

# def interact_with_user():
#     user_input = input("Enter your request: ")
#     while True:
#         if user_input.lower() in ["exit", "quit"]:
#             print("Chatbot: Goodbye!")
#             break
#         response = generate_sql(user_input)
#         if is_sql_statement(response):
#           print("Generated SQL Query:", response)
#           break
#         else:
#           print("Generated SQL Query is invalid.")
#           print("Clarifying Question:", response)
#           user_input = input("Your response: ")