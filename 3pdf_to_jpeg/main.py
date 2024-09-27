import os
import logging
from pdf2image import convert_from_path
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
SCOPES = ['https://www.googleapis.com/auth/cloud-platform']  # Adjust scopes if needed

logging.debug(f"Service Account File: {SERVICE_ACCOUNT_FILE}")
logging.debug(f"Scopes: {SCOPES}")

try:
    credentials = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    logging.debug("Service account credentials loaded successfully")
except Exception as e:
    logging.error(f"Error loading service account credentials: {e}")
    raise

# Cloud Storage settings
BUCKET_NAME = os.getenv('CLOUD_STORAGE_BUCKET')
ATTACHMENT_FOLDER = "attachments"  # Make sure this matches the first and second scripts

logging.debug(f"Cloud Storage Bucket: {BUCKET_NAME}")

def pdf_to_jpeg(pdf_path, output_folder, dpi=200):
    """
    Converts a PDF to JPEG, puts them in subfolders within the output_folder.
    """
    images = convert_from_path(pdf_path, dpi=dpi)
    pdf_name = os.path.splitext(os.path.basename(pdf_path))[0] 

    subfolder_count = 0
    image_count = 0
    for i, image in enumerate(images):
        if image_count % 10 == 0: 
            subfolder_count += 1
            current_output_folder = os.path.join(output_folder, f"subfolder_{subfolder_count:02d}")
            os.makedirs(current_output_folder, exist_ok=True)

        image_filename = f"image_{i+1:02d}.jpeg"
        image_path = os.path.join(current_output_folder, image_filename)
        image.save(image_path, "JPEG")
        image_count += 1

def process_pdfs_in_cloud_storage(event, context):
    """Triggered by a change to a Cloud Storage bucket.
    Args:
         event (dict): Event payload.
         context (google.cloud.functions.Context): Metadata for the event.
    """
    logging.debug(f"Event: {event}")
    logging.debug(f"Context: {context}")

    file_name = event['name']
    logging.debug(f"Processing file: {file_name}")

    # Check if the file is a PDF in the attachments folder
    if not file_name.startswith(ATTACHMENT_FOLDER + "/") or not file_name.lower().endswith('.pdf'):
        logging.info(f"Skipping file: {file_name} (not a PDF in attachments folder)")
        return

    # Initialize Cloud Storage client
    storage_client = storage.Client(credentials=credentials)

    # Get the PDF file from the bucket
    bucket = storage_client.bucket(BUCKET_NAME)
    blob = bucket.blob(file_name)

    # Download the PDF to a temporary location
    temp_file_path = f"/tmp/{file_name.split('/')[-1]}"
    blob.download_to_filename(temp_file_path)

    # Create the output folder in the same directory as the PDF, but within the 'images' subfolder
    output_dir = os.path.join(os.path.dirname(temp_file_path), "images", os.path.splitext(os.path.basename(temp_file_path))[0])
    os.makedirs(output_dir, exist_ok=True)

    # Convert the PDF to JPEGs
    pdf_to_jpeg(temp_file_path, output_dir)

    # Upload the JPEGs to Cloud Storage, maintaining the original folder structure
    for root, _, files in os.walk(output_dir):
        for file in files:
            if file.lower().endswith('.jpeg'):
                local_file_path = os.path.join(root, file)
                # Construct the Cloud Storage path, keeping the relative path from the 'images' folder
                cloud_storage_path = os.path.join(ATTACHMENT_FOLDER, "images", os.path.relpath(local_file_path, output_dir))
                image_blob = bucket.blob(cloud_storage_path)
                image_blob.upload_from_filename(local_file_path)
                logging.info(f"Uploaded JPEG: {cloud_storage_path}")

    # Optionally, delete the temporary PDF file and the local 'images' folder
    os.remove(temp_file_path)
    # shutil.rmtree(output_dir)  

    logging.info(f"Processed PDF: {file_name}")