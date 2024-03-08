import streamlit as st
from streamlit_chatbox import *
from loguru import logger
import requests
from openai import AzureOpenAI
from datetime import datetime
import json
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient
import os


# app title on sidebar, remove deploy buttton(mostly)
def css_fix():
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
            .reportview-container {
                margin-top: -2em;
            }
            #MainMenu {
                visibility: hidden;
            }
            .stDeployButton {
                display:none;
            }
            footer {
                visibility: hidden;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


# logger for user actions
def init_logger():
    logger.configure(
        handlers=[
            ## dict(sink=sys.stderr, format="[{time}][{level}] {message}"),
            dict(sink="log.txt", format="[{time}][{level}] {message}"),
        ]
    )
    logger.info("User selected chat view")


# file upload(chat history only currently)(potentially multipurpose for logging)
def upload_blob_file(
    blob_service_client: BlobServiceClient, container_name: str, filename: str
):
    container_client = blob_service_client.get_container_client(
        container=container_name
    )
    with open(file=os.path.join(".\\", filename), mode="rb") as data:
        container_client.upload_blob(name=filename, data=data, overwrite=True)


# config for this page
st.set_page_config(page_title="Chat")

# simple chat box structure (page body)
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
        model="ingenuityEmbedder", input=query, encoding_format="float"
    )
    ## st.sidebar.write(embeddings.data[0].embedding)

    # -get search results-
    endpoint = "https://ingenuity-ai-search.search.windows.net/"
    index_name = "vector-1707238357310"
    api_version = "2023-11-01"
    api_key = "nmnRajq7Ydh4epVjBkBwyRvfrvWDCfjPf7Amf4bRm6AzSeCqIxtX"
    search_url = f"{endpoint}indexes/{index_name}/docs/search?api-version={api_version}"
    headers = {"Content-Type": "application/json", "api-key": api_key}
    params = {
        # modify search here
        "vectorQueries": [
            {
                "vector": embeddings.data[0].embedding,
                "k": 7,
                "fields": "vector",
                "kind": "vector",
                "exhaustive": True,
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
        temperature=callTemperature,
    )

    # -display response-
    chat_box.ai_say(response.choices[0].message.content)

    # update chat memory(post-response)
    del st.session_state["chatMemory"][-2]
    st.session_state["chatMemory"].append(
        {"role": "assistant", "content": response.choices[0].message.content}
    )

    # save chat history(after each response)
    # timestamp and title only on first message
    if "timeStamp" not in st.session_state:
        st.session_state["timeStamp"] = datetime.now().strftime("%m-%d-%Y_%H'%M'%S")
        # chat title creation (breif description for viewing conveniece)
        getTitlePrompt = [
            {
                "role": "system",
                "content": "The following is the first prompt from a user to an LLM in a chat. Provide a title for this chat in 4 words or less, without punctuation, maximum of 15 characters per word.",
            },
            st.session_state["chatMemory"][0],
        ]
        titleResponse = client.chat.completions.create(
            model=deployment_name,
            messages=getTitlePrompt,
            temperature=0.20,
        )
        st.session_state["aiChatTitle"] = titleResponse.choices[0].message.content
    # write to local file
    stringChat = json.dumps(st.session_state["chatMemory"], separators=(",", ":"))
    f = open(st.session_state["timeStamp"] + ".txt", "a")
    f.write(st.session_state["aiChatTitle"] + "\n\n" + stringChat)
    f.close()
    # upload to blob storage
    storageClient = BlobServiceClient(
        account_url="https://ingenuitycontextstorage.blob.core.windows.net/",
        credential="RZkbZbqbW3FGkhz/wcwsWBqzZbmncBZaj5dRDSwrMOJo0xsGDobNIIdpXyLk86iQNNyrYsk6xUgF+AStDtSz6w==",
    )
    upload_blob_file(
        storageClient, "chat-logs", (st.session_state["timeStamp"] + ".txt")
    )
    # delete local file
    os.unlink(st.session_state["timeStamp"] + ".txt")


# init page
css_fix()
if "chatInit" not in st.session_state:
    if "chatHistoryInit" in st.session_state:
        del st.session_state["chatHistoryInit"]
    if "optionsInit" in st.session_state:
        del st.session_state["optionsInit"]
    st.session_state["chatInit"] = True
    logger.remove()
    init_logger()
