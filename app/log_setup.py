import logging
from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient
from datetime import datetime

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

# Upload the error log to Azure Blob Storage
def upload_error_log(container_client):
    with open('error.log', 'rb') as file:
        blob_client = container_client.get_blob_client(f'error_{datetime.now().strftime("%Y%m%d%H%M%S")}.log')
        blob_client.upload_blob(file)

