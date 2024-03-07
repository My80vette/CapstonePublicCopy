import streamlit as st
from streamlit_chatbox import *
from loguru import logger


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
    logger.info("User selected options view")


# config for this page
st.set_page_config(page_title="Options")

# tempurature slider (page body) 
# (other options may be placed here)
temperature = st.slider("Response Temperature", 0.00, 2.00, 0.20)
if "temperature" not in st.session_state:
    st.session_state["temperature"] = temperature
if temperature != st.session_state.get("temperature"):
    # on-change block
    logger.info("User selected response temperature: " + str(temperature))
    st.session_state["temperature"] = temperature

# init page
css_fix()
if "optionsInit" not in st.session_state:
    if "chatInit" in st.session_state:
        del st.session_state["chatInit"]
    if "chatHistoryInit" in st.session_state:
        del st.session_state["chatHistoryInit"]
    st.session_state["optionsInit"] = True
    logger.remove()
    init_logger()