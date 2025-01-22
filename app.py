import streamlit as st
import random
import time
from utils import ai_greetings, task2_greeting, check_for_tool, tools
from agents import task_classifier, sql_system_prompt, is_sql_statement
from dotenv import dotenv_values
from openai import OpenAI


config = dotenv_values(".env")

client = OpenAI(api_key=config["OPENAI_KEY"])
tool_counter = 0

def new_chat():
    st.session_state.messages = [
        {
            "role": "system",
            "content": task_classifier()
        },
        {
            "role": "assistant",
            "content": f"{ai_greetings()}, I'm J ! How can I help you ?"
        }
    ]

def sql_generator(user_query):
    if "sql_gen_messages" not in st.session_state.keys():
        st.session_state.sql_gen_messages = [
            {
                "role": "system",
                "content": sql_system_prompt()
            }
        ]
    
    sql_gen_msgs = {
            "role" : "user",
            "content" : user_query
        }
    st.session_state.sql_gen_messages.append(sql_gen_msgs)
    # st.session_state.messages.append(sql_gen_msgs)

    response = client.chat.completions.create(
        model = "gpt-4o-mini",
        messages = st.session_state.sql_gen_messages
    )
    update_msg = {
        "role":"assistant",
        "content":response.choices[0].message.content
    }
    st.session_state.sql_gen_messages.append(update_msg)
    st.session_state.messages.append(update_msg)
    # if is_sql_statement(response.choices[0].message.content):
    #     st.markdown(response.choices[0].message.content)
    # else:
    #     st.markdown(response.choices[0].message.content)
        
    return response.choices[0].message.content

st.markdown("""
    <div style='text-align: center;'>
        <h1> Welcome to SQL </h1>
    </div>
""", unsafe_allow_html=True)


col1, col2, col3 = st.columns([1, 5, 1])
col3.button("New Chat", on_click=new_chat)

# Initialize chat history
if "messages" not in st.session_state.keys():
    st.session_state.messages = [
        {
            "role": "system",
            "content": task_classifier()
        },
        {
            "role": "assistant",
            "content": f"{ai_greetings()}, I'm ZENIX ! How can I help you ?"
        }
    ]

# Display chat messages from history on app rerun
for message in st.session_state.messages:
    if message["role"] == "system":
        pass
    elif message["role"] == "assistant":
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    else:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

# Accept user input
if prompt := st.chat_input():
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})
    # Display user message in chat message container
    with st.chat_message("user"):
        st.markdown(prompt)

# 
if st.session_state.messages[-1]["role"] not in ["assistant"]:
    with st.chat_message("assistant"):
        if tool_counter == 0:
            tool_check =  check_for_tool(client, prompt, tools)
            tool_counter = 1

        print("tool_check:", tool_check)

        if tool_check.finish_reason == "tool_calls":
            if tool_check.message.tool_calls[0].function.name == "sql_generator":
                    
                print("===========")
                # llm_response = task_classifier(prompt, st.session_state.messages, config["OPENAI_KEY"])
                # sql_generator(prompt)
                
                with st.spinner("Generating SQL query..."):
                    response = sql_generator(prompt)
                    st.markdown(response)
                    print("response:",response)
                    if is_sql_statement(response):
                        print("generating xml")
                        tool_counter = 0

                        # Can you write sql query to merge table LMF1 and LMF2
                        # Inner join on both columns
                    
                    # print("Printing response in main")
                    # print(response)
                    # st.markdown(response)
                    # return_messages = {
                        # "role": "assistant",
                        # "content": response
                    # }

    # st.session_state.messages.extend(return_messages)







