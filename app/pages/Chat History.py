import streamlit as st
from streamlit_chatbox import *
from loguru import logger
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient


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
            #stDecoration {
                display:none;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


# logger for user actions
def init_logger():
    logger.configure(
        handlers=[
            # dict(sink=sys.stderr, format="[{time}][{level}] {message}"),
            dict(sink="log.txt", format="[{time}][{level}] {message}"),
        ]
    )
    logger.info("User selected chat history view")


# get full list of histories (titles, timestamps, message structures)
def get_history_list(blob_service_client: BlobServiceClient, container_name):
    # finish comments
    st.session_state["historyList"] = []

    container_client = blob_service_client.get_container_client(
        container=container_name
    )
    blob_list = container_client.list_blobs()
    for blob in blob_list:
        st.sidebar.write(blob.name)


# config for this page
st.set_page_config(page_title="Chat History")

# chat history (page body)
st.write("This is the Chat History View")

# init page
css_fix()
if "chatHistoryInit" not in st.session_state:
    if "chatInit" in st.session_state:
        del st.session_state["chatInit"]
    if "optionsInit" in st.session_state:
        del st.session_state["optionsInit"]
    st.session_state["chatHistoryInit"] = True
    logger.remove()
    init_logger()

    # load histories (only on first time opening the page)
    if "historyList" not in st.session_state:
        storageClient = BlobServiceClient(
            account_url="https://ingenuitycontextstorage.blob.core.windows.net/",
            credential="RZkbZbqbW3FGkhz/wcwsWBqzZbmncBZaj5dRDSwrMOJo0xsGDobNIIdpXyLk86iQNNyrYsk6xUgF+AStDtSz6w==",
        )
        get_history_list(storageClient, "chat-logs")
