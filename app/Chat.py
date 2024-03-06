from pathlib import Path
import streamlit as st
from streamlit_chatbox import *
from loguru import logger
import requests
from openai import AzureOpenAI
import json
from log_setup import logger, upload_error_log, logs_container_client


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
            ## dict(sink=sys.stderr, format="[{time}][{level}] {message}"),
            dict(sink="log.txt", format="[{time}][{level}] {message}"),
        ]
    )
    logger.info("User selected chat view")


# config for this page
st.set_page_config(page_title="Chat")

# Start error logging
try:


    # simple chat box structure
    chat_box = ChatBox()
    chat_box.init_session()
    chat_box.output_messages()
    if query := st.chat_input("input your question here", key="chatBox"):

        # -log input-
        chat_box.user_say(query)
        logger.info("User sent message: " + query)

        # -init client-
        client = AzureOpenAI(
            api_key="2f8c4fc6fba44228b5a9a268cc579fe5",
            api_version="2023-07-01-preview",
            azure_endpoint="https://ingenuityai.openai.azure.com/",
        )
        deployment_name = "ingenuityGPT"

        # -embedding-
        embeddings = client.embeddings.create(
            model="ingenuityEmbedder",
            input=query,
            encoding_format="float"
        )
        ## st.sidebar.write(embeddings.data[0].embedding)

        # -get search results-
        endpoint = "https://ingenuity-ai-search.search.windows.net/"
        index_name = "vector-1707238357310"
        api_version = "2023-11-01"
        api_key = "nmnRajq7Ydh4epVjBkBwyRvfrvWDCfjPf7Amf4bRm6AzSeCqIxtX"
        search_url = f"{endpoint}indexes/{index_name}/docs/search?api-version={api_version}"
        headers = {
            "Content-Type": "application/json",
            "api-key": api_key
        }
        params = {
            # modify search here
            "vectorQueries": [
                {
                    "vector": embeddings.data[0].embedding,
                    "k": 7,
                    "fields": "vector",
                    "kind": "vector",
                    "exhaustive": True
                }
            ]
        }
        searchResponse = requests.post(search_url, headers=headers, json=params)
        if searchResponse.status_code == 200:
            search_results = searchResponse.json()
            ## st.sidebar.write(search_results["value"][0])
        else:
            st.sidebar.write("Failed to retrieve search results:", searchResponse.text)
            ## st.sidebar.write(searchResponse.status_code)
        # only use first chunk from result (token reasons)(might need to expand this)
        docs = search_results["value"][0]

        # set temperature (not pipeline-related)
        if "temperature" not in st.session_state:
            callTemperature = 0.20
        else:
            callTemperature = st.session_state.get("temperature")

        # update chat memory
        systemPrompt = (
            # prompt engineer here
            f"Relevant documents: {docs}. Based on these, answer the following user query."
        )
        if "chatMemory" not in st.session_state:
            st.session_state["chatMemory"] = []
        st.session_state["chatMemory"].append({"role": "system", "content": systemPrompt})
        st.session_state["chatMemory"].append({"role": "user", "content": query})

        # -call AI API-
        response = client.chat.completions.create(
            model=deployment_name,
            messages=st.session_state["chatMemory"],
            temperature=callTemperature
        )

        # update chat memory(post-response)
        del st.session_state["chatMemory"][-2]
        st.session_state["chatMemory"].append({"role": "assistant", "content": response.choices[0].message.content})

        # -display response-
        chat_box.ai_say(response.choices[0].message.content)

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

# If an error occurs above (anywhere after site initialization) we will log it.
except Exception as e:
    logger.error(f'An error occurred: {e}')
    upload_error_log(logs_container_client)