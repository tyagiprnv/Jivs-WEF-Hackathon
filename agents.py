from sentence_transformers import SentenceTransformer
import chromadb
from typing import List, Dict
import os
import ast
import re

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
                - Do not return any additional information"""}]
    
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
                response_content = f"Here's the link to the related view: {url}"
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
                    - If you have enough information: Return only one SQL query.
                    - If you do not have enough information: Return a clarifying question or list of questions to the user, asking them to specify the missing details.
            Only return one SQL query as text or the question you want to ask. Do not provide any additional explantion or information''' 
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
        
        
# Agent 1
def llm_guardrail(user_query):
    # client = OpenAI(api_key="API_KEY")
    system_prompt = f""" You are an assistant for the company Data Migration Internation who is an expert in 
    data management, application retirement, and migration. You should be able to expertly classify a given query 
    as RELEVANT to the Data Migration Internation company or not solely on the user query.
    
    Response: Classify the query as RELEVANT or NOTRELEVANT
    """
    return system_prompt


# Agent 1
def task_classifier():
    system_prompt = f""" 
    You are an intelligent AI assistant who classifies tasks and returns the function to be selected as a function call.
    You classify the user prompt into either of the two sepcific task:
    - IMP view : Provide a link to the view on a database requested by the user. This task just works on fetching the link and nothing else. This will return the link_generator function.
    - Business Object Creation : Generate the SQL query requested by the user. This will return the function sql_generator.
    Make sure you follow these steps:
    1. Plan first : Decide which one of the two task is needed to be performed.
    2. Specify only one function that needs to be called based on the task.
    3. Do not run the function, just return it as a tool_call.
    """
    return system_prompt


# Agent 2
# def sql_generator(prompt, messages):
#     messages = [msg for msg in st.sess]

#     sql_user_prompt(prompt)
#     return response

def sql_system_prompt():
    with open("data/schema.txt", 'r') as infile:
        schema = infile.read()

    system_message = f'''You are a SQL expert. Your task is to generate valid SQL queries based on user requests. You do not respond to anything else. You just generate valid executable SQL queries.
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
    3. Check the join conditions (if any):
        - If the join type is not mentioned, ask the user to clarify which type of join they need.
        - If the columns to join are not mentioned (e.g. they say "merge tables A and B"), then using the schema of the tables, strictly respond with the name of the columns on which these tables can be joined.
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
        - If you have enough information: Return only one SQL query.
        - If you do not have enough information: Return a clarifying question or list of questions to the user, asking them to specify the missing details.
        
    Only return one SQL query as text or the question you want to ask. Do not provide any additional explantion or information'''

    return system_message

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