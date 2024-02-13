import streamlit as st
from streamlit_chatbox import *

chat_box = ChatBox()

# tabs relocated to sidebar (nonfunctional currently)
with st.sidebar:
    st.title('Mars Ingenuity SME')
    st.button('Chat', key='chatTab')
    st.button('Chat History', key='chatHistoryTab')

# simple chat box structure
chat_box.init_session()
chat_box.output_messages()

if query := st.chat_input('input your question here'):
    chat_box.user_say(query)
    chat_box.ai_say('you said: ' + query)

print("PHOBOS")
# working on tempurature slider
# temperature = st.slider('Response Temperature', 0, 100, 50)