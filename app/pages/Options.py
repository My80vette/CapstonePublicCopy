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
            st.session_state["initPrompt"] = """You are a subject matter expert for the Ingenuity Mars Helicopter, and you have all the relevant documentation to act as such and make informed decisions. You are providing expert advice to Jet Propulsion Laboratory operators.

Your guidelines are: Explain your reasoning briefly, use first person perspective, use clear and concise language, use conditional language where useful, always use specific numbers and units, cite the names of all documents you used, and emphasize immediate actions and proactive suggestions. If you receive a question with multiple parts, use and cite as many documents as you need. If you are asked to explain a system or topic, always return specific numbers, units, and ranges.

Analyze the following situation and the potential consequences of it. If there is no immediate danger to Ingenuity, then say there is no immediate danger and suggest actions to mitigate future problems. If the situation is dangerous, and likely to cause damage to Ingenuity, then state Ingenuity must land now along with the reason."""
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

    # Dark/Light Mode Toggle
    st.divider()
    ms = st.session_state
    if "themes" not in ms: 
        ms.themes = {"current_theme": "dark",
                    "refreshed": True,
                    "light": {"theme.base": "dark",
                              "button_face": "Toggle Dark Mode"},
                    "dark":  {"theme.base": "light",
                              "button_face": "Toggle Light Mode"},
                    }
  

    def ChangeTheme():
        previous_theme = ms.themes["current_theme"]
        tdict = ms.themes["light"] if ms.themes["current_theme"] == "light" else ms.themes["dark"]
        for vkey, vval in tdict.items(): 
            if vkey.startswith("theme"): st._config.set_option(vkey, vval)

        ms.themes["refreshed"] = False
        if previous_theme == "dark": ms.themes["current_theme"] = "light"
        elif previous_theme == "light": ms.themes["current_theme"] = "dark"


    btn_face = ms.themes["light"]["button_face"] if ms.themes["current_theme"] == "light" else ms.themes["dark"]["button_face"]
    st.button(btn_face, on_click=ChangeTheme)

    if ms.themes["refreshed"] == False:
        ms.themes["refreshed"] = True
        st.rerun()

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