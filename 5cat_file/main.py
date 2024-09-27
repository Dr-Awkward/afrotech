import os
import logging
from google.cloud import storage
from google.oauth2 import service_account
from dotenv import load_dotenv

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

# Cloud Storage settings
BUCKET_NAME = "bonesjustice"
ATTACHMENT_FOLDER = "attachments"

logging.debug(f"Cloud Storage Bucket: {BUCKET_NAME}")

def concatenate_text_files(event, context):
    """Triggered by a change to a Cloud Storage bucket.
    Args:
         event (dict): Event payload.
         context (google.cloud.functions.Context): Metadata for the event.
    """
    logging.debug(f"Event: {event}")
    logging.debug(f"Context: {context}")

    file_name = event['name']
    logging.debug(f"Processing file: {file_name}")

    # Check if the file is a text file in the attachments/images folder
    if not file_name.startswith(os.path.join(ATTACHMENT_FOLDER, "images")) or not file_name.lower().endswith('.txt'):
        logging.info(f"Skipping file: {file_name} (not a text file in attachments/images folder)")
        return

    # Initialize Cloud Storage client
    storage_client = storage.Client(credentials=credentials)
    bucket = storage_client.bucket(BUCKET_NAME)

    # Extract the original ZIP filename from the text file's path
    original_zip_filename = file_name.split("/")[2]  

    # Create a unique folder for the concatenated output
    output_folder_name = f"concatenated_text/{original_zip_filename}"

    # List all text files associated with the same original ZIP upload
    text_files = list(bucket.list_blobs(prefix=os.path.join(ATTACHMENT_FOLDER, "images", original_zip_filename)))

    # Concatenate the content of all text files
    concatenated_content = ""
    for text_file in text_files:
        if text_file.name.lower().endswith('.txt'):
            logging.info(f"Concatenating: {text_file.name}")
            concatenated_content += text_file.download_as_string().decode("utf-8") + "\n\n"  # Add separator between files

    # Upload the concatenated content to the new folder
    output_blob = bucket.blob(os.path.join(output_folder_name, f"{original_zip_filename}_concatenated.txt"))
    output_blob.upload_from_string(concatenated_content)

    logging.info(f"Concatenated text files for {original_zip_filename} into {output_blob.name}")