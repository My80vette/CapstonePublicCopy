import streamlit as st
from streamlit_chatbox import *
from loguru import logger as loguruLogger
import requests
from openai import AzureOpenAI
from datetime import datetime
import json
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient
import os
from log_setup import logger, upload_error_log, logs_container_client
from openai import RateLimitError
import pytz 


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
            ## dict(sink=sys.stderr, format="[{time}][{level}] {message}"),
            dict(sink="log.txt", format="[{time}][{level}] {message}"),
        ]
    )
    loguruLogger.info("User selected chat view")


# blob upload(chat history)
def upload_blob_stream(blob_service_client: BlobServiceClient, container_name, file_name, input_stream):
    blob_client = blob_service_client.get_blob_client(
        container=container_name, blob=(file_name + ".txt")
    )
    blob_client.upload_blob(input_stream, blob_type="BlockBlob")


# get current options (from blob storage)
def get_options(blob_service_client: BlobServiceClient, container_name, blob_name):
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


# config for this page
st.set_page_config(page_title="Chat")
if "optionsInit" not in st.session_state:
    storageClient = BlobServiceClient(
        account_url="https://ingenuitycontextstorage.blob.core.windows.net/",
        credential="RZkbZbqbW3FGkhz/wcwsWBqzZbmncBZaj5dRDSwrMOJo0xsGDobNIIdpXyLk86iQNNyrYsk6xUgF+AStDtSz6w==",
    )
    get_options(storageClient, "stored-options", "options.txt")

# Start error logging
try:

    # simple chat box structure (page body)
    chat_box = ChatBox()
    chat_box.init_session()
    chat_box.output_messages()
    if query := st.chat_input("input your question here", key="chatBox"):
        # -log input-
        chat_box.user_say(query)
        loguruLogger.info("User sent message: " + query)
        # -init client-
        client = AzureOpenAI(
            api_key="2f8c4fc6fba44228b5a9a268cc579fe5",
            api_version="2023-07-01-preview",
            azure_endpoint="https://ingenuityai.openai.azure.com/",
        )
        deployment_name = "ingenuityGPT"
        # Error catching for generating embeddings
        continue_execution = True
        try:
            # -embedding-
            embeddings = client.embeddings.create(
                model="ingenuityEmbedder", input=query, encoding_format="float"
            )
        except Exception as e:
            error_message = f"An error occurred while generating embeddings: {e}"
            logger.error(f"An error occurred while generating embeddings: {e}")
            upload_error_log(logs_container_client, error_message)
            chat_box.ai_say(
                "An unexpected error has occurred while generating the response. You may have exceeded the maximum token length, please try again or shorten your query. For more information, please refer to the error logs."
            )
            continue_execution = False
        ## st.sidebar.write(embeddings.data[0].embedding)
        if continue_execution:
            # -get search results-
            endpoint = "https://ingenuity-ai-search.search.windows.net/"
            index_name = "vector-1709324901732"
            api_version = "2023-11-01"
            api_key = "nmnRajq7Ydh4epVjBkBwyRvfrvWDCfjPf7Amf4bRm6AzSeCqIxtX"
            search_url = (
                f"{endpoint}indexes/{index_name}/docs/search?api-version={api_version}"
            )
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
            else:
                st.sidebar.write("Failed to retrieve search results:", searchResponse.text)

            # store doc title and excerpt for citing
            doc_info = []

            for doc in search_results["value"]:
                title = doc["title"]
                excerpt = doc["chunk"]  # this field SHOULD hold the data given by AiSearch
                doc_info.append({"title": title, "excerpt": excerpt})

            docs_used = []
            for doc in doc_info:
                docs_used.append(doc["title"])

            # set ai chat title empty value
            st.session_state["aiChatTitle"] = ""
            
            # set options-controlled values (temperature / prompt instructions)
            # Tell the model to not just make a hard go/nogo decision, decide the criticality of an error and use the documentation to decide what the craft should do moving forward
            if "loadedOptions" not in st.session_state:
                # tempurature (default)
                callTemperature = 0.20
                # prompt (default)
                promptingInstructions = """You are a subject matter expert for the Ingenuity Mars Helicopter, and you have all the relevant documentation to act as such and make informed decisions. You are providing expert advice to Jet Propulsion Laboratory operators.

Your guidelines are: Explain your reasoning briefly, use first person perspective, use clear and concise language, use conditional language where useful, always use specific numbers and units, cite the names of all documents you used, and emphasize immediate actions and proactive suggestions. If you receive a question with multiple parts, use and cite as many documents as you need. If you are asked to explain a system or topic, always return specific numbers, units, and ranges.

Analyze the following situation and the potential consequences of it. If there is no immediate danger to Ingenuity, then say there is no immediate danger and suggest actions to mitigate future problems. If the situation is dangerous, and likely to cause damage to Ingenuity, then state Ingenuity must land now along with the reason."""
            else:
                # tempurature (custom)
                callTemperature = st.session_state["loadedOptions"][0]
                # prompt (custom)
                promptingInstructions = st.session_state["loadedOptions"][1]

            # prep doc excerpts
            passedDocsString = ""
            for idx, doc in enumerate(doc_info, start=1):
                passedDocsString += f"Title: {doc['title']}\nExcerpt: {doc['excerpt']}\n\n"

            # update chat memory (BUILDING MESSAGE STRUCTURE TO BE SENT)
            if "chatMemory" not in st.session_state:
                st.session_state["chatMemory"] = []
            st.session_state["chatMemory"].append({"role": "system", "content": promptingInstructions})
            st.session_state["chatMemory"].append({"role": "system", "content": "Here is the user’s question:"})
            st.session_state["chatMemory"].append({"role": "user", "content": query})
            st.session_state["chatMemory"].append({"role": "system", "content": "Here are excerpts from documents you should use to aid your response:"})
            st.session_state["chatMemory"].append({"role": "system", "content": passedDocsString})
            st.session_state["chatMemory"].append({"role": "system", "content": "Cite the name of all of the documents you used to aid your response."})

            # Monitor for errors in response generation
            try:
                # -call AI API-
                response = client.chat.completions.create(
                    model=deployment_name,
                    messages=st.session_state["chatMemory"],
                    temperature=callTemperature,
                )
            # Handle the error and log it or display the response
            except RateLimitError as e:
                error_message = f"Rate limit exceeded: {e}"
                logger.error(f"Rate limit exceeded: {e}")
                upload_error_log(logs_container_client, error_message)
                chat_box.ai_say(
                    "An error has occurred while generating the response due to exceeding the rate limit. Please try again in one minute. For more information, please refer to the error logs."
                )
                continue_execution = False

            if continue_execution:
                docs_cited = ", ".join(docs_used)
                final_response = response.choices[0].message.content.format(docs_cited)
                chat_box.ai_say(final_response)

                # update chat memory(post-response)
                del st.session_state["chatMemory"][-6]
                del st.session_state["chatMemory"][-5]
                del st.session_state["chatMemory"][-3]
                del st.session_state["chatMemory"][-2]
                del st.session_state["chatMemory"][-1]
                st.session_state["chatMemory"].append(
                    {"role": "assistant", "content": response.choices[0].message.content}
                )

                # save chat history(after each response)

                # timestamp and title only on first message
                if "timeStamp" not in st.session_state:
                    st.session_state["timeStamp"] = datetime.now(pytz.timezone('US/Pacific')).strftime("%m-%d-%Y_%H'%M'%S")
                    # chat title creation (breif description for viewing conveniece)
                    getTitlePrompt = [
                        {
                            "role": "system",
                            "content": "The following is the first prompt from a user to an LLM in a chat. Provide a title for this chat in 4 words or less, without punctuation, maximum of 15 characters per word.",
                        },
                        st.session_state["chatMemory"][0],
                    ]
                    # Check for errors when generating a title
                    try:
                        titleResponse = client.chat.completions.create(
                            model=deployment_name,
                            messages=getTitlePrompt,
                            temperature=0.20,
                        )
                        st.session_state["aiChatTitle"] = titleResponse.choices[
                            0
                        ].message.content
                    # Handle the error or assign a title
                    except Exception as e:
                        # error_message = f"An error occurred while generating chat title: {e}"
                        # logger.error(f"An error occurred while generating chat title: {e}")
                        # upload_error_log(logs_container_client, error_message)
                        chat_box.ai_say(
                            "An error occured while trying to generate a chat title, please try again"
                        )

                # upload to blob storage
                stringChat = json.dumps(st.session_state["chatMemory"], separators=(",", ":"))
                titledChat = st.session_state["aiChatTitle"] + "\n\n" + stringChat
                storageClient = BlobServiceClient(
                    account_url="https://ingenuitycontextstorage.blob.core.windows.net/",
                    credential="RZkbZbqbW3FGkhz/wcwsWBqzZbmncBZaj5dRDSwrMOJo0xsGDobNIIdpXyLk86iQNNyrYsk6xUgF+AStDtSz6w==",
                )
                upload_blob_stream(
                    storageClient,
                    "chat-logs",
                    (st.session_state["timeStamp"] + ".txt"),
                    titledChat,
                )
                
                del st.session_state["timeStamp"]

    # init page
    css_fix()
    if "chatInit" not in st.session_state:
        if "chatHistoryInit" in st.session_state:
            del st.session_state["chatHistoryInit"]
        if "optionsInit" in st.session_state:
            del st.session_state["optionsInit"]
        st.session_state["chatInit"] = True
        loguruLogger.remove()
        init_logger()

# This should capture errors in the actual UI, all OpenAI calls are monitored seperatly.
except Exception as e:
    error_message = f"An unexpected error has occured: {e}"
    logger.error(f"An error occurred: {e}")
    upload_error_log(logs_container_client, error_message)
    chat_box.ai_say(
        "An unexpected error has occured, please refer to the error logs for more information"
    )
