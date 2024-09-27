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
    try:
        with Image.open(file_path) as img:
            img.thumbnail(max_size)
            buffered = io.BytesIO()
            img.save(buffered, format="JPEG")
            encoded = base64.b64encode(buffered.getvalue()).decode('utf-8')
            logging.debug(f"Encoded image from {file_path}. First 20 characters: {encoded[:20]}")
            return encoded
    except IOError:
        logging.error(f"Error: Unable to open or process image: {file_path}")
        raise

def process_images_in_folder(folder_path, client, system_prompt, user_prompt):
    try:
        jpeg_files = glob.glob(os.path.join(folder_path, "*.jpg")) + glob.glob(os.path.join(folder_path, "*.jpeg"))
        if not jpeg_files:
            logging.info(f"No JPEG files found in {folder_path}. Skipping.")
            return

        content = []
        for i, file in enumerate(jpeg_files, 1):
            encoded_image = read_and_resize_image(file)
            content.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/jpeg",
                    "data": encoded_image
                }
            })
            content.append({
                "type": "text",
                "text": f"Image {i}:"
            })

        content.append({
            "type": "text",
            "text": user_prompt
        })

        logging.debug("Number of items in content list: {}".format(len(content)))
        for i, item in enumerate(content):
            if item['type'] == 'image':
                logging.debug(f"Item {i} is an image. First 50 characters of base64 data: {item['source']['data'][:50]}")
            elif item['type'] == 'text':
                logging.debug(f"Item {i} is text. Content: {item['text']}")

        try:
            response = client.messages.create(
                model="claude-3-5-sonnet-20240620",
                max_tokens=8192,
                extra_headers={"anthropic-beta": "max-tokens-3-5-sonnet-2024-07-15"},
                system=system_prompt,
                messages=[
                    {
                        "role": "user", 
                        "content": content
                    }
                ]
            )
            assistant_response = response.content[0].text

            # Save the response to a file
            output_file_name = os.path.join(folder_path, f'response_{int(time.time())}.txt')
            with open(output_file_name, 'w') as output_file:
                output_file.write(assistant_response)
            logging.info(f"Response has been written to {output_file_name}")
        except anthropic.APIError as e:
            logging.error(f"Anthropic API error: {str(e)}")

    except Exception as e:
        logging.error(f"An error occurred while processing folder {folder_path}: {str(e)}")
        traceback.print_exc()

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

def process_jpegs_in_cloud_storage(event, context):
    logging.debug(f"Event: {event}")
    logging.debug(f"Context: {context}")

    file_name = event['name']
    logging.debug(f"Processing file: {file_name}")

    if not file_name.startswith(os.path.join(ATTACHMENT_FOLDER, "images") + "/") or not file_name.lower().endswith('.jpeg'):
        logging.info(f"Skipping file: {file_name} (not a JPEG in attachments/images folder)")
        return

    api_key = access_secret_version("claude_api_key")
    system_prompt = access_secret_version("decode_system_prompt")
    user_prompt = access_secret_version("decode_user_prompt")

    client = anthropic.Anthropic(api_key=api_key)

    storage_client = storage.Client(credentials=credentials)
    bucket = storage_client.bucket(BUCKET_NAME)
    for folder in bucket.list_blobs(prefix=os.path.join(ATTACHMENT_FOLDER, "images")):
        if folder.name.endswith('/'):
            folder_path = "/tmp/" + folder.name 
            os.makedirs(folder_path, exist_ok=True)
            logging.info(f"Downloading folder: {folder.name} to {folder_path}")

            for blob in bucket.list_blobs(prefix=folder.name):
                if not blob.name.endswith('/'):
                    file_path = os.path.join(folder_path, os.path.basename(blob.name))
                    blob.download_to_filename(file_path)

            process_images_in_folder(folder_path, client, system_prompt, user_prompt)

            for file in os.listdir(folder_path):
                os.remove(os.path.join(folder_path, file))
            os.rmdir(folder_path)
