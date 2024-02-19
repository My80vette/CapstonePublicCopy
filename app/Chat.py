from pathlib import Path
import streamlit as st
from streamlit_chatbox import *
from loguru import logger
import requests
from openai import AzureOpenAI
import json

#TextAnalyticsApiKeyCredential

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

    # -call AI API-
    prompt = (
        # prompt engineer here
        f"Relevant documents: {docs}. Based on these, answer the user query: {query}"
    )
    response = client.chat.completions.create(
        model=deployment_name,
        messages=[{"role": "system", "content": prompt}],
    )

    # -display response-
    chat_box.ai_say(response.choices[0].message.content)
    # # AI API
    # prompt = (
    #     f"Relevant documents: {docs}. Based on these, answer the user query: {query}"
    # )

    input_data = {  
    "language": "en",  
    "text": query,  
    }  

    documents = [{"id": "1", "language": "en", "text": query}]
    
    
    # Extract key phrases
    poller = client.begin_analyze_actions(
        documents=documents,
        actions=[ExtractKeyPhrasesAction()],
        show_stats=True
    )
    result = poller.result()

    # Retrieve key phrases from the result
    key_phrases = [phrase for doc in result for action in doc for phrase in action.key_phrases]

    # Use the key phrases in your prompt
    prompt = f"User asked: {query}. Based on concepts like {key_phrases}, provide a helpful response:"


    openai_request = {
        "prompt": prompt,
        "max_tokens": 100,
        "stop": "\n",
    }
    
    response = requests.post("https://ingenuityai.openai.azure.com", headers={"Authorization": f"Bearer {credentials}"}, json=openai_request)


    response_json = response.json()
    gpt_response = response_json["choices"][0]["text"] 
    chat_box.ai_say(gpt_response)

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
