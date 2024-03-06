from pathlib import Path
import streamlit as st
from streamlit_chatbox import *
from loguru import logger
import requests
from openai import AzureOpenAI
import json


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

    # Tell the model to not just make a hard go/nogo decision, decide the criticality of an error and use the documentation to decide what the craft should do moving forward
    instructions = {
        "style": "proactive",  #  A keyword to remind the model
        "considerations": [
            "You are a subject matter expert for the Ingenuity rover and you have all the relevant documentaion to act as such and make informed decisions"
            "Analyze the situation and potential consequences of the problem.",
            "If there's no immediate danger, suggest actions to mitigate or preemptively address the issue. If the danger is immediate and likely to cause a crash soon, land now",
            "Explain your reasoning briefly. Use First person perspective, 'I' and 'My' in all of your responses."
            "Cite the source of your information including the document or snippet to validate your responses."
            "Emphasize proactive suggestions over immediate actions."
            "Use conditional language ('if', 'when') to guide the user."
        ],
        "example": {
            "query": "Battery level is at 25%.",
            "response": "My battery is getting low. I'll continue the current task, but I should start scanning for potential landing zones to ensure a safe return. Based on [document], this is not a critical issue"
        }
    }


    # -call AI API-
    prompt = (
        # prompt engineer here
        f"Relevant documents: {docs}. Based on these, answer the user query: {query}. Craft your responses based on these instructions {instructions}"
    )
    response = client.chat.completions.create(
        model=deployment_name,
        messages=[{"role": "system", "content": prompt}],
        temperature=callTemperature
    )

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
