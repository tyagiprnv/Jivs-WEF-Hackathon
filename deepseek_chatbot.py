from openai import OpenAI
import sqlparse
import os

api_key = os.getenv("DEEPSEEK_API_KEY")

client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")

system_prompt_tmp = """
You are a SQL expert. Your task is to generate valid SQL queries based on user requests. You will also validate the request against the following database schema:

Database Schema:
{schema}

Rules:
1. If the user request is unclear or cannot be translated into a valid SQL query, ask clarifying questions.
2. Only generate SQL queries if the request makes sense for the database schema.
3. Format the SQL query properly.

Examples:
- User: "Retrieve all data from the table LFB5."
  SQL: SELECT * FROM LFB5;

- User: "Show all contact persons for vendors in ascending order of their IDs."
  SQL: SELECT KNVK.*, ADR6.* FROM KNVK LEFT JOIN ADR6 ON KNVK.MANDT = ADR6.CLIENT AND KNVK.PRSNR = ADR6.PERSNUMBER WHERE KNVK.LIFNR <> '' ORDER BY KNVK.MANDT ASC, KNVK.LIFNR ASC;

"""

with open("data/schema.txt", 'r') as infile:
    content = infile.read()

system_prompt = {"role": "system", "content": system_prompt_tmp.format(schema=content)}

conversation = [system_prompt]

def generate_sql(user_input):
    message = {"role": "user", "content": user_input}
    conversation.append(message)
    response = client.chat.completions.create(
    model="deepseek-chat",
    messages=conversation,
    stream=False
    )
    conversation.append(response.choices[0].message)
    return response.choices[0].message.content


def validate_sql(sql_query):
    try:
        parsed = sqlparse.parse(sql_query)
        if not parsed:
            return False
        return True
    except Exception as e:
        print("SQL Validation Error:", e)
        return False

def interact_with_user():
    user_input = input("Enter your request: ")
    while True:
        if user_input.lower() in ["exit", "quit"]:
            print("Chatbot: Goodbye!")
            break
        response = generate_sql(user_input)
        if response.startswith("SQL:"):
            sql_query = response.replace("SQL:", "").strip()
            if validate_sql(sql_query):
                print("Generated SQL Query:", sql_query)
                break
            else:
                print("Generated SQL Query is invalid.")
            break
        else:
            print("Clarifying Question:", response)
            user_input = input("Your response: ")

if __name__ == "__main__":
    interact_with_user()

