import random

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