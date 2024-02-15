from pathlib import Path
import streamlit as st
from streamlit_chatbox import *
from loguru import logger
import requests
from openai import OpenAI


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

    # embedding
    api_key = "2f8c4fc6fba44228b5a9a268cc579fe5"  
    endpoint = "https://ingenuityai.openai.azure.com"  
    client = OpenAI(api_key=api_key, base_url=endpoint)  

    embeddings = client.embeddings.create(
    model="text-embedding-ada-002",
    input=query,
    encoding_format="float"
    )

    # get search results
    search_request = {"embedding": embeddings}
    search_url = "https://ingenuity-ai-search.search.windows.net/indexes/vector-1707238357310/docs"
    search_results = requests.post(search_url, json=search_request)
    results = search_results.json()["value"]
    docs = [r["content"] for r in results[:5]]

    # AI API
    prompt = (
        f"Relevant documents: {docs}. Based on these, answer the user query: {query}"
    )

    input_data = {  
    "language": "en",  
    "text": prompt,  
    }  
    # Send the request to the Azure OpenAI API  
    response = client.predict(input_data)  

    # response = openai.Completion.create(
    #     engine="gpt-35-turbo:1106", prompt=prompt, max_tokens=1000
    # )
    # gpt_response = response.choices[0].text

    chat_box.ai_say(response)

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
