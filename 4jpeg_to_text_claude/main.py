import os
import logging
import anthropic
import glob
import base64
from PIL import Image
import io
import time
import traceback
from google.cloud import storage
from google.oauth2 import service_account
from dotenv import load_dotenv
from google.cloud import secretmanager

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s [%(levelname)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

# Load environment variables from .env file
logging.debug("Loading environment variables from .env file")
load_dotenv()

# Load credentials from the JSON key file
SERVICE_ACCOUNT_FILE = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
SCOPES = ['https://www.googleapis.com/auth/cloud-platform'] 

logging.debug(f"Service Account File: {SERVICE_ACCOUNT_FILE}")
logging.debug(f"Scopes: {SCOPES}")

try:
    credentials = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    logging.debug("Service account credentials loaded successfully")
except Exception as e:
    logging.error(f"Error loading service account credentials: {e}")
    raise

# Cloud Storage and Secret Manager settings
BUCKET_NAME = "bonesjustice" 
ATTACHMENT_FOLDER = "attachments" 
PROJECT_ID = os.getenv('PROJECT_ID') # Get your project ID from environment variables

logging.debug(f"Cloud Storage Bucket: {BUCKET_NAME}")

def read_and_resize_image(file_path, max_size=(1568, 1568)):
    # ... (same as before)

def process_images_in_folder(folder_path, client, system_prompt, user_prompt):
    # ... (same as before)

def access_secret_version(secret_id, version_id="latest"):
    """
    Access the payload for the given secret version if one exists. The version
    can be a version number as a string (e.g. "5") or an alias (e.g. "latest").
    """
    client = secretmanager.SecretManagerServiceClient(credentials=credentials)
    name = f"projects/{PROJECT_ID}/secrets/{secret_id}/versions/{version_id}"
    try:
        response = client.access_secret_version(request={"name": name})
        payload = response.payload.data.decode("UTF-8")
        return payload
    except Exception as e:
        logging.error(f"Error accessing secret version: {e}")
        raise

def process_jpegs_in_cloud_storage(event, context):
    """Triggered by a change to a Cloud Storage bucket.
    Args:
         event (dict): Event payload.
         context (google.cloud.functions.Context): Metadata for the event.
    """
    logging.debug(f"Event: {event}")
    logging.debug(f"Context: {context}")

    file_name = event['name']
    logging.debug(f"Processing file: {file_name}")

    # Check if the file is a JPEG in the attachments/images folder
    if not file_name.startswith(os.path.join(ATTACHMENT_FOLDER, "images") + "/") or not file_name.lower().endswith('.jpeg'):
        logging.info(f"Skipping file: {file_name} (not a JPEG in attachments/images folder)")
        return

    # Get secrets from Secret Manager
    api_key = access_secret_version("claude_api_key")
    system_prompt = access_secret_version("decode_system_prompt")
    user_prompt = access_secret_version("decode_user_prompt")

    client = anthropic.Anthropic(api_key=api_key)

    # Process all folders within 'attachments/images'
    storage_client = storage.Client(credentials=credentials)
    bucket = storage_client.bucket(BUCKET_NAME)
    for folder in bucket.list_blobs(prefix=os.path.join(ATTACHMENT_FOLDER, "images")):
        if folder.name.endswith('/'): 
            folder_path = "/tmp/" + folder.name 
            os.makedirs(folder_path, exist_ok=True)
            logging.info(f"Downloading folder: {folder.name} to {folder_path}")

            for blob in bucket.list_blobs(prefix=folder.name):
                if not blob.name.endswith('/'):  # it's a file, not a folder
                    file_path = os.path.join(folder_path, os.path.basename(blob.name))
                    blob.download_to_filename(file_path)

            process_images_in_folder(folder_path, client, system_prompt, user_prompt)

            # Clean up the temporary folder
            for file in os.listdir(folder_path):
                os.remove(os.path.join(folder_path, file))
            os.rmdir(folder_path)