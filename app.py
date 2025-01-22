import streamlit as st
import random
import time
import json
from utils import ai_greetings, is_url, is_sql_statement
from agents import TaskDetectingAgent, SemanticSearch, EasyNavAgent, SQLXMLGenAgent
from dotenv import dotenv_values
from openai import OpenAI

def initialize_env_variables():
    if "client" not in st.session_state:
        config = dotenv_values(".env")
        st.session_state.client = OpenAI(api_key=config["OPENAI_KEY"])

    if "task_detector_agent" not in st.session_state:
        print("Task Detect Agent Started")
        st.session_state.task_detector_agent = TaskDetectingAgent(st.session_state.client) 

    if "easy_nav_agent" not in st.session_state:
        print("Easy Nav Agent Started")
        st.session_state.search_system = SemanticSearch()
        st.session_state.easy_nav_agent = EasyNavAgent(st.session_state.client, st.session_state.search_system)

    if "sql_xml_gen_agent" not in st.session_state:
        print("SQL XML Gen Agent Started")
        st.session_state.sql_xml_gen_agent = SQLXMLGenAgent(st.session_state.client)
        
    if "tool_counter" not in st.session_state:
        st.session_state.tool_counter = 0
    
    if "tool_check" not in st.session_state:
        st.session_state.tool_check = None

initialize_env_variables()

def new_chat():
    st.session_state.task_detector_agent = TaskDetectingAgent(st.session_state.client)
    st.session_state.search_system = SemanticSearch()
    st.session_state.easy_nav_agent = EasyNavAgent(st.session_state.client, st.session_state.search_system)
    st.session_state.sql_xml_gen_agent = SQLXMLGenAgent(st.session_state.client)
    st.session_state.tool_counter = 0
    st.session_state.tool_check = None
    
    st.session_state.messages = [
        st.session_state.task_detector_agent.task_detector_convo[0],
        {
            "role": "assistant",
            "content": f"{ai_greetings()}, I'm J ! How can I help you ?"
        }
    ]

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
        st.session_state.task_detector_agent.task_detector_convo[0],
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
        if message["content"] == "Calling Function":
            pass
        else:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
    elif message["role"] == "tool":
        with st.chat_message("assistant"):
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
if st.session_state.messages[-1]["role"] not in ["assistant","tool"]:
    with st.chat_message("assistant"):
        
        if st.session_state.tool_counter == 0:
            # tool_check = check_for_tool(client, prompt, tools)
            st.session_state.tool_check = st.session_state.task_detector_agent.generate_response(prompt)
            st.session_state.tool_counter = 1
            print("Tool Checker Response:", st.session_state.tool_check)

        if st.session_state.tool_check.finish_reason == "tool_calls":
            function_name = st.session_state.tool_check.message.tool_calls[0].function.name 
            # function_args = json.loads(st.session_state.tool_check.message.tool_calls[0].function.arguments)
            
            if function_name == "link_generator":
                print()
                print(f"Entering Function:{function_name}")
                
                with st.spinner("Finding a related view"):
                    
                    assistant_response = {
                        "role":"assistant",
                        "content":f"Calling Function",
                        "tool_calls": [{"id":st.session_state.tool_check.message.tool_calls[0].id,
                                        "type":"function",
                                        "function":{"arguments":str(prompt),
                                                    "name":function_name}}]
                    }
                    st.session_state.messages.append(assistant_response)
                    
                    response = st.session_state.easy_nav_agent.generate_response(prompt)
                    st.markdown(response)
                    
                    tool_response = {
                        "role": "tool",
                        "content": response,
                        "tool_call_id": st.session_state.tool_check.message.tool_calls[0].id,
                        "name": function_name
                    }
                    st.session_state.messages.append(tool_response)
                    
                    if is_url(response):
                        st.session_state.tool_counter = 0
                    
            elif function_name == "sql_generator":
                print()
                print(f"Entering Function:{function_name}")    
                # print("===========")
                # llm_response = task_classifier(prompt, st.session_state.messages, config["OPENAI_KEY"])
                # sql_generator(prompt)
                
                with st.spinner("Generating SQL query..."):
                    
                    assistant_response = {
                        "role":"assistant",
                        "content":f"Calling Function",
                        "tool_calls": [{"id":st.session_state.tool_check.message.tool_calls[0].id,
                                        "type":"function",
                                        "function":{"arguments":prompt,
                                                    "name":function_name}}]
                    }
                    st.session_state.messages.append(assistant_response)
                    
                    response = st.session_state.sql_xml_gen_agent.generate_response(prompt)
                    st.markdown(response)
                    
                    # print("response:",response)
                    tool_response = {
                        "role": "tool",
                        "content": response,
                        "tool_call_id": st.session_state.tool_check.message.tool_calls[0].id,
                        "name": function_name
                    }
                    st.session_state.messages.append(tool_response)
                    
                    if is_sql_statement(response):
                        print("generating xml")
                        st.session_state.tool_counter = 0

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







