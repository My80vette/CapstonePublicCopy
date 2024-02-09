from pathlib import Path
import streamlit as st
from streamlit_chatbox import *
from loguru import logger
import sys


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
            dict(sink=sys.stderr, format="[{time}][{level}] {message}"),
            dict(sink="log.txt", format="[{time}][{level}] {message}"),
        ]
    )
    logger.info("User selected chat history view")


# config for this page
st.set_page_config(page_title="Chat History")

# chat history body
st.write("This is the Chat History View")

# init page
add_title()
if "chatHistoryInit" not in st.session_state:
    if "chatInit" in st.session_state:
        del st.session_state["chatInit"]
    if "optionsInit" in st.session_state:
        del st.session_state["optionsInit"]
    st.session_state["chatHistoryInit"] = True
    logger.remove()
    initlogger()
