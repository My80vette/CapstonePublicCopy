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
    # lengthy, strangely formatted default value will be removed to a separate file in a future ticket (temp slider bug fix)(check comments on ticket)
    if "promptingInstructions" not in st.session_state:
        st.session_state["promptingInstructions"] = """You are a subject matter expert for the Ingenuity mars helicopter and you have all the relevant documentation to act as such and make informed decisions.
Analyze the situation and potential consequences of the problem.
If there's no immediate danger, suggest actions to mitigate or preemptively address the issue. If the danger is immediate and likely to cause a crash soon, land now.
Explain your reasoning briefly. Use First person perspective, 'I' and 'My' in all of your responses.
At the end of each response, create a newline then cite your source, including the document title where the information came from.
If you receive a multi-part question that involves multiple subsystems, pick the relevant info from each document, then cite them all, don't use just one document per response.
Emphasize proactive suggestions over immediate actions.
Use conditional language ('if', 'when') to guide the user.
When asked to explain a system or topic, return specifics including numbers, units, etc., do not generalize or use placeholders, you are an engineer providing precise technical information."""
    st.session_state["promptingInstructions"] = st.text_area(
        "Edit AI Prompt",
        st.session_state["promptingInstructions"],
        height=300
    )


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