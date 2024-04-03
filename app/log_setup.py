import logging
import os
from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient
from datetime import datetime
import random
import string

# Set up credentials from the $logs container
#Connection String from the Ingenuitycontextstorage -> access keys
blob_service_client = BlobServiceClient.from_connection_string("DefaultEndpointsProtocol=https;AccountName=ingenuitycontextstorage;AccountKey=RZkbZbqbW3FGkhz/wcwsWBqzZbmncBZaj5dRDSwrMOJo0xsGDobNIIdpXyLk86iQNNyrYsk6xUgF+AStDtSz6w==;EndpointSuffix=core.windows.net")
# connecting to the error-log container
container_name = "error-logs"
logs_container_client = blob_service_client.get_container_client(container_name)

# Set up logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.ERROR)

# Create a file handler
file_handler = logging.FileHandler('error.log')
file_handler.setLevel(logging.ERROR)

# Create a formatter
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)

# Add the file handler to the logger
logger.addHandler(file_handler)

def upload_error_log(logs_container_client, error_message):
    # Generate a unique file name using the timestamp and a random string
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    random_string = ''.join(random.choices(string.ascii_letters + string.digits, k=3))
    file_name = f"error_log_{timestamp}_{random_string}.txt"

    # Create the log file
    with open(file_name, "w") as log_file:
        log_file.write(error_message)

    # Upload the log file to the container
    with open(file_name, "rb") as data:
        logs_container_client.upload_blob(name=file_name, data=data)

    # Remove the local log file
    os.remove(file_name)
