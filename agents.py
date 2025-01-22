from openai import OpenAI
import sqlparse

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
    You are an intelligent AI assistant who can perform multiple task using functions.
    You classify the user prompt into either of the two sepcific task:
    - IMP view : Provide a link for the view on a database requested by the user. This task just works on fetching the link and nothing else. This will call the function link_generator.
    - Business Object Creation : Generate the SQL query requested by the user. This will call the function sql_generator.
    Make sure you follow these steps:
    1. Plan first : Decide which one of the two task is needed to be performed.
    2. Specify only one function that needs to be called based on the task.
    3. Assume the reponse by the functions is accurate and up-to-date.
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


def is_sql_statement(sql_text):
  try:
    statements = sqlparse.parse(sql_text)
    if not statements:
      return False
    for statement in statements:
      stmt_type = statement.get_type()
      if stmt_type == 'UNKNOWN':
        return False
    return True
  except Exception:
    return False

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