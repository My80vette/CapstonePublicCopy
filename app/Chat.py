from pathlib import Path
import streamlit as st
from streamlit_chatbox import *
from loguru import logger
# import sys
# import openai
# import os
# from tenacity import retry, wait_random_exponential


# # Configure Azure OpenAI Service API
# openai.api_type = "azure"
# openai.api_version = "2023-03-15-preview"
# openai.api_base = os.getenv('OPENAI_API_BASE')
# openai.api_key = os.getenv("OPENAI_API_KEY")
# #openai.log = "debug"

# # generate a response
# @retry(wait=wait_random_exponential(multiplier=1, max=60))
# def generate_response(prompt):
#     st.session_state['messages'].append({"role": "user", "content": prompt})

#     completion = openai.ChatCompletion.create(
#         engine=model,
#         messages=st.session_state['messages']
#     )
#     response = completion.choices[0].message.content
#     st.session_state['messages'].append({"role": "assistant", "content": response})

#     print(st.session_state['messages'])
#     total_tokens = completion.usage.total_tokens
#     prompt_tokens = completion.usage.prompt_tokens
#     completion_tokens = completion.usage.completion_tokens
#     return response

# app title on sidebar
def add_title():
    st.markdown(
        """
        <style>
            [data-testid="stSidebarNav"]::before {
                content: "AI SME";
                margin-left: 20px;
                margin-bottom: 20px;
                font-size: 30px;
                position: relative;
                text-decoration: underline;
                top: 100px;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


# logger for user actions
def initlogger():
    logger.configure(
        handlers=[
            # dict(sink=sys.stderr, format="[{time}][{level}] {message}"),
            dict(sink="log.txt", format="[{time}][{level}] {message}"),
        ]
    )
    logger.info("User selected chat view")


# config for this page
st.set_page_config(page_title="Chat")

# simple chat box structure
chat_box = ChatBox()
chat_box.init_session()
chat_box.output_messages()
if query := st.chat_input("input your question here", key="chatBox"):
    chat_box.user_say(query)
    logger.info("User sent message: " + query)
    chat_box.ai_say("you said: " + query)

# init page
add_title()
if "chatInit" not in st.session_state:
    if "chatHistoryInit" in st.session_state:
        del st.session_state["chatHistoryInit"]
    if "optionsInit" in st.session_state:
        del st.session_state["optionsInit"]
    st.session_state["chatInit"] = True
    logger.remove()
    initlogger()

# run the app
# st.run()