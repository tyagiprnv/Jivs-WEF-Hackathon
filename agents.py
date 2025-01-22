
from openai import OpenAI

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
def task_classifier(user_query, messages, api_key):
    client = OpenAI(api_key= api_key)
    system_prompt = f""" 
    You are an assistant who is an expert in classifying a user prompt. 
    Analyze the user prompt: {user_query}

    If the user queries or prompts regarding views then classify it as TASK1 else if the user queries regarding helping with a 
    SQL query classify it as TASK2. The Answer should either be TASK1 or TASK2
    """
    # print(system_prompt)
    messages.append(
        {
            "role": "developer",
            "content": system_prompt
        }
    )
    # print("Before calling the LLM")
    # print(messages)
    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        messages = messages
    )
    result = completion.choices[0].message.content
    print(result)
    client.close()
    return result


# Agent 2
def sql_generator(user_query, messages, api_key):
    client = OpenAI(api_key= api_key)
    system_prompt = f""" 
    You are an assistant who is an expert in helping a user write a sql query. 
    Analyze the user prompt: {user_query} .
    Now help the user write the SQL query.
    """
    # print(system_prompt)
    messages.append(
        {
            "role": "sql_classification_system",
            "content": system_prompt
        }
    )
    # print("Before calling the LLM")
    # print(messages)
    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        messages = messages
    )
    result = completion.choices[0].message.content
    print(result)
    client.close()
    return result