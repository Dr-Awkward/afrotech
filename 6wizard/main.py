import os
import logging
import openai
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
PROJECT_ID = os.getenv('PROJECT_ID')

logging.debug(f"Cloud Storage Bucket: {BUCKET_NAME}")

def read_and_resize_image(file_path, max_size=(1568, 1568)):
    # Implement image reading and resizing logic here
    pass

def process_images_in_folder(folder_path, client, system_prompt, user_prompt):
    # Implement image processing logic with ChatGPT
    pass

def access_secret_version(secret_id, version_id="latest"):
    client = secretmanager.SecretManagerServiceClient(credentials=credentials)
    name = f"projects/{PROJECT_ID}/secrets/{secret_id}/versions/{version_id}"
    try:
        response = client.access_secret_version(request={"name": name})
        payload = response.payload.data.decode("UTF-8")
        return payload
    except Exception as e:
        logging.error(f"Error accessing secret version: {e}")
        raise

def get_chatgpt_response(messages, system_prompt):
    """Get a response from ChatGPT."""
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",  
            messages=messages,
            max_tokens=1500,
            temperature=0.0
        )
        return response.choices[0].message.content
    except Exception as e:
        logging.error(f"Error getting response from ChatGPT: {e}")
        raise

def process_text_file(file_name, system_prompt):
    logging.info(f"Processing file: {file_name}")

    storage_client = storage.Client(credentials=credentials)
    bucket = storage_client.bucket(BUCKET_NAME)
    blob = bucket.blob(file_name)

    # Download the text file to a temporary location
    temp_file_path = f"/tmp/{file_name.split('/')[-1]}"
    blob.download_to_filename(temp_file_path)

    try:
        with open(temp_file_path, 'r', encoding="utf-8-sig") as f:
            user_prompt = f.read().strip()

        output_file = os.path.join("/tmp", 'Mindset.html') 

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        assistant_response = get_chatgpt_response(messages, system_prompt)
        
        with open(output_file, 'w', encoding="utf-8") as f:
            f.write(assistant_response)

        logging.info(f"The complete response has been saved to {output_file}")

        # Upload the output HTML file to a new folder in Cloud Storage
        original_zip_filename = file_name.split("/")[2]
        output_file_name = f'Youre_A_Wizard_Harry_{original_zip_filename}.html'
        output_folder_name = f"chatgpt_output/{original_zip_filename}"
        output_blob = bucket.blob(os.path.join(output_folder_name, output_file_name))
        output_blob.upload_from_filename(output_file)
        logging.info(f"Uploaded HTML file to Cloud Storage: {output_blob.name}")

    except Exception as e:
        logging.error(f"An error occurred while processing file {file_name}:")
        logging.error(str(e))
        logging.error("Traceback:")
        traceback.print_exc()

    finally:
        # Clean up temporary files
        os.remove(temp_file_path)
        if os.path.exists(output_file):
            os.remove(output_file)

def process_text_files_in_cloud_storage(event, context):
    logging.debug(f"Event: {event}")
    logging.debug(f"Context: {context}")

    file_name = event['name']
    logging.debug(f"Processing file: {file_name}")

    if not file_name.startswith(os.path.join(ATTACHMENT_FOLDER, "images")) or not file_name.lower().endswith('.txt'):
        logging.info(f"Skipping file: {file_name} (not a text file in attachments/images folder)")
        return

    # Get secrets from Secret Manager
    api_key = access_secret_version("chatgpt_api_key")
    system_prompt = access_secret_version("chatgpt_system_prompt")

    openai.api_key = api_key

    process_text_file(file_name, system_prompt)
