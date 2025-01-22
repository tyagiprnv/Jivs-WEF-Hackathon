import random
import re
import sqlglot

def ai_greetings():
    greetings = ["Hello", "Hi there", "Greetings", "Good Day", "Nice to meet you"]
    greeting = random.choice(greetings)
    return greeting

def task2_greeting():
    task2_resps = ["Hi there! Sure, I'd be happy to help with your SQL queries. What do you have in mind?",
                 "Hello! Let’s tackle your SQL questions together. How can I assist you today?",
                 "Hi there! SQL can get tricky sometimes, but I'm here to help. What's the task at hand?"]
    task2_resp = random.choice(task2_resps)
    return task2_resp

tools = [
    {
        "type" : "function",
        "function":{
            "name": "link_generator",
            "description": """Task is to fetch the URL for the view based on user request. This function retrives the link to a view on a database.
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
        "function":{
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

def check_for_tool(client, user_query, tools, model = "gpt-4o-mini"):
    check_for_tool = client.chat.completions.create(
        model = model,
        messages = [{"role": "user", "content": user_query}],
        tools = tools
    )

    return check_for_tool.choices[0]

def is_url(text):
    """
    Check if the provided text is a valid URL using regular expressions.

    Args:
        text (str): The text to validate as a URL.

    Returns:
        bool: True if text is a valid URL, False otherwise.
    """
    # Define a regex pattern for validating URLs
    url_pattern = re.compile(
        r'^(https?|ftp)://'  # http://, https://, or ftp://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+'  # Domain name
        r'[A-Z]{2,6}\.?|'  # Top-level domain
        r'localhost|'  # localhost
        r'\d{1,3}(?:\.\d{1,3}){3})'  # ...or IPv4 address
        r'(?::\d+)?'  # Optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)

    return re.match(url_pattern, text)

def is_sql_statement(sql_text):
  try:
    parsed = sqlglot.parse_one(sql_text)
    return True
  except Exception:
    return False