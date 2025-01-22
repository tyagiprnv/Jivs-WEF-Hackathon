import streamlit as st
import random
import time
import json
from utils import ai_greetings, is_url, is_sql_statement
from agents import TaskDetectingAgent, SemanticSearch, EasyNavAgent, SQLXMLGenAgent, SQLtoXML
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
    
    if 'xml_data' not in st.session_state:
        st.session_state['xml_data'] = {}
    
    if 'xml_step' not in st.session_state:
        st.session_state['xml_step'] = 0
        
    if 'generating_xml' not in st.session_state:
        st.session_state['generating_xml'] = {}
        
    if 'generated_query' not in st.session_state:
        st.session_state['generated_query'] = None

initialize_env_variables()

st.set_page_config(
    initial_sidebar_state = "expanded",
    page_title = "AppName",
    layout = "wide"
)

with st.sidebar:
    st.title("AppName")
    # st.image("")
    
    # st.subheader("Select which LLM you want to use:")
    options = ["GPT-4o-Mini", "LLaMa 3.2B (Still in Development)"]
    selected_model_name = st.sidebar.selectbox(
        "Select which LLM to use",
        options,
        key = "selected_model"
    )
    mapping = {
        "GPT-4o-Mini":"gpt-4o-mini",
        "LLaMa 3.2B (Still in Development)": "llama3"
    }
    selected_model = mapping.get(selected_model_name)
    if selected_model == "llama3":
        selected_model = "gpt-4o-mini"
        
def new_chat():
    
    st.session_state.task_detector_agent = TaskDetectingAgent(st.session_state.client)
    st.session_state.search_system = SemanticSearch()
    st.session_state.easy_nav_agent = EasyNavAgent(st.session_state.client, st.session_state.search_system)
    st.session_state.sql_xml_gen_agent = SQLXMLGenAgent(st.session_state.client)
    st.session_state.tool_counter = 0
    st.session_state.tool_check = None
    st.session_state.xml_data = {}
    st.session_state.generating_xml = False
    st.session_state.xml_step = 0
    st.session_state.generated_query = None
    
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
                        print("Link Generated")
                        st.session_state.tool_counter = 0
                    
            elif function_name == "sql_generator":
                print()
                print(f"Entering Function:{function_name}")    
                
                if not st.session_state.generating_xml:
                    
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
                        
                        query_to_check = str(response).replace("```","").replace("sql","")
                        
                        if is_sql_statement(query_to_check):
                            print("SQL Done")
                            st.session_state.generated_query = query_to_check         
                            print("Lets Generate XML")
                            st.session_state.generating_xml = True
                            if st.session_state.xml_step == 0:
                                question = "To generate an XML, Please give a name for this new view"
                                st.markdown(question)
                                st.session_state.messages.append({"role":"assistant", "content": question})
                                st.session_state.xml_step += 1
                                
                    
                else:
                    with st.spinner("Generating XML"):    
                        if st.session_state.xml_step == 1:
                            st.session_state['xml_data']['viewName'] = prompt
                            question = "Please tell me what does this view mean"
                            st.markdown(question)
                            st.session_state.messages.append({"role":"assistant", "content": question})
                            st.session_state.xml_step += 1
                        else:
                            st.session_state['xml_data']['viewDesc'] = prompt
                            filename = str(st.session_state['xml_data']['viewName'])
                            with open(f"config/{filename}.sql", 'w') as f:
                                f.write(str(st.session_state.generated_query))
                                
                            with open('config/view.json', 'w') as json_file:
                                json.dump(st.session_state['xml_data'], json_file)
                                
                                
                            xml_creator = SQLtoXML(st.session_state.client)
                            xml_creator.convert_sql_to_xml()
                            st.markdown("XML Successfully Generated")
                            st.session_state.messages.append({"role":"assistant", "content": "XML Successfully Generated"})
                                                        
                            st.session_state.generating_xml = False
                            st.session_state.xml_step = 0
                            st.session_state['xml_data'] = {}
                            st.session_state.tool_counter = 0
                            st.session_state.generated_query = ""

                        # Can you write sql query to merge table LFM1 and LFM2
                        # Inner join on both columns
                    
                    # print("Printing response in main")
                    # print(response)
                    # st.markdown(response)
                    # return_messages = {
                        # "role": "assistant",
                        # "content": response
                    # }

    # st.session_state.messages.extend(return_messages)







