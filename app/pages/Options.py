import streamlit as st
from streamlit_chatbox import *
from loguru import logger as loguruLogger
from log_setup import logger, upload_error_log, logs_container_client
from streamlit_modal import Modal
from azure.storage.blob import BlobServiceClient
import json

# Error handling
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
        loguruLogger.info("User selected options view")


    # get current options (from blob storage)
    def get_options(container_name, blob_name):
        blob_service_client = BlobServiceClient(
            account_url="https://ingenuitycontextstorage.blob.core.windows.net/",
            credential="RZkbZbqbW3FGkhz/wcwsWBqzZbmncBZaj5dRDSwrMOJo0xsGDobNIIdpXyLk86iQNNyrYsk6xUgF+AStDtSz6w==",
        )
        container_client = blob_service_client.get_container_client(
            container=container_name
        )
        blob_list = container_client.list_blobs()
        # only do anything if there is a blob
        for blob in blob_list:
            # initialize options
            st.session_state["loadedOptions"] = []
            # download options blob as string
            blob_client = blob_service_client.get_blob_client(
                container=container_name, blob=blob_name
            )
            downloader = blob_client.download_blob(max_concurrency=1, encoding="UTF-8")
            st.session_state["loadedOptions"] = json.loads(downloader.readall())


    def save_options():
        blob_service_client = BlobServiceClient(
            account_url="https://ingenuitycontextstorage.blob.core.windows.net/",
            credential="RZkbZbqbW3FGkhz/wcwsWBqzZbmncBZaj5dRDSwrMOJo0xsGDobNIIdpXyLk86iQNNyrYsk6xUgF+AStDtSz6w==",
        )
        blob_client = blob_service_client.get_blob_client(
            container="stored-options", blob="options.txt"
        )
        new_options = [st.session_state["tempTemperature"], st.session_state["tempPrompt"]]
        input_stream = json.dumps(new_options)
        blob_client.upload_blob(input_stream, blob_type="BlockBlob", overwrite=True)


    # config for this page
    st.set_page_config(page_title="Options")
    if "optionsInit" not in st.session_state:
        get_options("stored-options", "options.txt")
        if "loadedOptions" not in st.session_state:
            # tempurature (default)
            st.session_state["initTemperature"] = 0.20
            # prompt (default)
            st.session_state["initPrompt"] = """You are a subject matter expert for the Ingenuity mars helicopter and you have all the relevant documentation to act as such and make informed decisions.
Analyze the situation and potential consequences of the problem.
If there's no immediate danger, suggest actions to mitigate or preemptively address the issue. If the danger is immediate and likely to cause a crash soon, land now.
Explain your reasoning briefly. Use First person perspective, 'I' and 'My' in all of your responses.
At the end of each response, create a newline then cite your source, including the document title where the information came from.
If you receive a multi-part question that involves multiple subsystems, pick the relevant info from each document, then cite them all, don't use just one document per response.
Emphasize proactive suggestions over immediate actions.
Use conditional language ('if', 'when') to guide the user.
When asked to explain a system or topic, return specifics including numbers, units, etc., do not generalize or use placeholders, you are an engineer providing precise technical information."""
        else:
            # tempurature (custom)
            st.session_state["initTemperature"] = st.session_state["loadedOptions"][0]
            # prompt (custom)
            st.session_state["initPrompt"] = st.session_state["loadedOptions"][1]

    # options (page body) 

    # setup popup/modal for full history view
    modal = Modal(
        "Debug Logs",
        key="debugModal",
        padding=20,
        max_width=744
    )

    # temp slider
    st.session_state["tempTemperature"] = st.slider("Response Temperature", 0.00, 2.00, st.session_state["initTemperature"])
    if st.session_state["tempTemperature"] != st.session_state["initTemperature"]:
        # on-change block
        loguruLogger.info("User selected response temperature: " + str(st.session_state["tempTemperature"]))
        save_options()

    # view debug log 
    st.divider()
    if st.button("View Debug Logs", key="showDebug"):
        loguruLogger.info("User opened debug log")
        modal.open()
    if modal.is_open():
        with modal.container():
            f = open("log.txt", "r")
            currentDebug = f.read()
            f.close()
            f = open("error.log", "r")
            currentError = f.read()
            f.close()
            st.text_area(
                "Debug Log",
                currentDebug,
                disabled=True,
                height=400
            )
            st.text_area(
                "Error Log",
                currentError,
                disabled=True,
                height=400
            )

    # editable prompt
    st.divider()
    st.session_state["tempPrompt"] = st.text_area(
        "Edit AI Prompt",
        st.session_state["initPrompt"],
        height=300
    )
    if st.session_state["tempPrompt"] != st.session_state["initPrompt"]:
        # on-change block
        loguruLogger.info("User edited AI prompt: " + st.session_state["tempPrompt"])
        save_options()


    # init page
    css_fix()
    if "optionsInit" not in st.session_state:
        if "chatInit" in st.session_state:
            del st.session_state["chatInit"]
        if "chatHistoryInit" in st.session_state:
            del st.session_state["chatHistoryInit"]
        st.session_state["optionsInit"] = True
        loguruLogger.remove()
        init_logger()

except Exception as e:
    logger.error(f'An error occurred: {e}')
    upload_error_log(logs_container_client)