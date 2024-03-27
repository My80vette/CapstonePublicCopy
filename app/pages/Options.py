import streamlit as st
from streamlit_chatbox import *
from loguru import logger as loguruLogger
from log_setup import logger, upload_error_log, logs_container_client
from streamlit_modal import Modal

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


    # config for this page
    st.set_page_config(page_title="Options")

    # options (page body) 

    # setup popup/modal for full history view
    modal = Modal(
        "Debug Logs",
        key="debugModal",
        padding=20,
        max_width=744
    )

    # temp slider
    temperature = st.slider("Response Temperature", 0.00, 2.00, 0.20)
    if "temperature" not in st.session_state:
        st.session_state["temperature"] = temperature
    if temperature != st.session_state.get("temperature"):
        # on-change block
        loguruLogger.info("User selected response temperature: " + str(temperature))
        st.session_state["temperature"] = temperature

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
    st.text_area(
        "Edit AI Prompt",
        "test",
        height=300
    )
    st.sidebar.write(st.session_state)


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