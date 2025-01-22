import streamlit as st
import random
import time
from utils import ai_greetings, task2_greeting
from agents import task_classifier
from dotenv import dotenv_values

config = dotenv_values(".env")

def new_chat():
    st.session_state.messages = [
        {
            "role": "system",
            "content": ""
        },
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
        {
            "role": "system",
            "content": ""
        },
        {
            "role": "assistant",
            "content": f"{ai_greetings()}, I'm J ! How can I help you ?"
        }
    ]

# Display chat messages from history on app rerun
for message in st.session_state.messages:
    if message["role"] == "system":
        pass
    elif message["role"] == "assistant":
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            # st.markdown("Im in here")
    elif message["role"] == "developer":
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            # st.markdown("Im with task classification agent")

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
        with st.spinner("Thinking..."):
            
            print("===========")
            llm_response = task_classifier(prompt, st.session_state.messages, config["OPENAI_KEY"])
            
            if llm_response.strip(" ") == "TASK2":
                task2_resp = task2_greeting()
                st.session_state.messages.append({"role": "developer", "content": task2_resp})
                st.markdown(task2_resp)
                print(st.session_state.messages)







