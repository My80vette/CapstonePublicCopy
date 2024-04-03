import streamlit as st
from streamlit_chatbox import *
from loguru import logger as loguruLogger
from log_setup import logger, upload_error_log, logs_container_client
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient
import json
from datetime import datetime
from streamlit_modal import Modal

# Error Detection
try:

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
        loguruLogger.configure(
            handlers=[
                # dict(sink=sys.stderr, format="[{time}][{level}] {message}"),
                dict(sink="log.txt", format="[{time}][{level}] {message}"),
            ]
        )
        loguruLogger.info("User selected chat history view")


    # get full list of histories (titles, timestamps, message structures)
    def get_history_list(blob_service_client: BlobServiceClient, container_name):
        # initialize history list
        st.session_state["historyList"] = []
        # get list of blob names
        container_client = blob_service_client.get_container_client(
            container=container_name
        )
        blob_list = container_client.list_blobs()
        for blob in blob_list:
            # download blobs
            blob_client = blob_service_client.get_blob_client(
                container=container_name, blob=blob.name
            )
            downloader = blob_client.download_blob(max_concurrency=1, encoding="UTF-8")
            blob_text = downloader.readall()
            # add formatted histories to history list
            timeStampParse = blob.name.split(".")[0].split("_")
            dateParse = timeStampParse[0].split("-")
            timeParse = timeStampParse[1].split("'")
            blobFields = blob_text.split("\n")
            st.session_state["historyList"].insert(
                0,
                {
                    "title": blobFields[0],
                    "timeStamp": datetime(
                        int(dateParse[2]),
                        int(dateParse[0]),
                        int(dateParse[1]),
                        int(timeParse[0]),
                        int(timeParse[1]),
                        int(timeParse[2]),
                    ),
                    "messages": json.loads(blobFields[2]),
                },
            )


    # config for this page
    st.set_page_config(page_title="Chat History")

    # init page
    css_fix()
    if "chatHistoryInit" not in st.session_state:
        if "chatInit" in st.session_state:
            del st.session_state["chatInit"]
        if "optionsInit" in st.session_state:
            del st.session_state["optionsInit"]
        st.session_state["chatHistoryInit"] = True
        loguruLogger.remove()
        init_logger()

        # load histories (only on first time opening the page)
        if "historyList" not in st.session_state:
            storageClient = BlobServiceClient(
                account_url="https://ingenuitycontextstorage.blob.core.windows.net/",
                credential="RZkbZbqbW3FGkhz/wcwsWBqzZbmncBZaj5dRDSwrMOJo0xsGDobNIIdpXyLk86iQNNyrYsk6xUgF+AStDtSz6w==",
            )
            get_history_list(storageClient, "chat-logs")

    # chat history (page body)
            
    # setup popup/modal for full history view
    modal = Modal(
        "Chat History Details",
        key="chat-history-details",
        padding=20,
        max_width=744
    )
            
    # get number of rows
    colCount = 2
    displayRows = [st.columns(colCount)]
    for history in st.session_state["historyList"]:
        if (st.session_state["historyList"].index(history) + 1) % colCount == 0:
            displayRows.append(st.columns(colCount))

    # layout containers
    historyIndex = 0
    for col in sum(displayRows[1:], displayRows[0]):
        if historyIndex < len(st.session_state["historyList"]):
            # individual tiles for each history
            tile = col.container(border=True, height=225)
            tile.subheader(st.session_state["historyList"][historyIndex]["title"], divider="red")
            tile.write(st.session_state["historyList"][historyIndex]["timeStamp"].strftime("%A %B %d, %Y | %I:%M %p"))
            # open modal button
            if tile.button("View Chat :eye-in-speech-bubble:", key=historyIndex):
                loguruLogger.info("User opened chat history from " + st.session_state["historyList"][historyIndex]["timeStamp"].strftime("%A %B %d, %Y | %I:%M %p"))
                st.session_state["selectedHistoryIndex"] = historyIndex
                modal.open()
        historyIndex += 1

    # details modal content
    if modal.is_open():
        with modal.container():
            # title and timestamp
            selectedTitle = st.session_state["historyList"][st.session_state["selectedHistoryIndex"]]["title"]
            selectedTimeStamp = st.session_state["historyList"][st.session_state["selectedHistoryIndex"]]["timeStamp"].strftime("%A %B %d, %Y | %I:%M %p")
            st.write(selectedTitle + " | " + selectedTimeStamp)
            # loop through messages
            history_box = ChatBox(session_key="history-chat")
            history_box.init_session()
            history_box.output_messages()
            for message in st.session_state["historyList"][st.session_state["selectedHistoryIndex"]]["messages"]:
                if message["role"] == "user":
                    history_box.user_say(message["content"])
                elif message["role"] == "assistant":
                    history_box.ai_say(message["content"])
            history_box.reset_history()

except Exception as e:
    logger.error(f'An error occurred: {e}')
    upload_error_log(logs_container_client)