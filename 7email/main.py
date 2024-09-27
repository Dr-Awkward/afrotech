import os
import logging
from google.cloud import storage
from google.oauth2 import service_account
from googleapiclient.discovery import build
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s [%(levelname)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

# Load environment variables from .env file
logging.debug("Loading environment variables from .env file")
load_dotenv()

# Load credentials from the JSON key file
SERVICE_ACCOUNT_FILE = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
SCOPES = ['https://www.googleapis.com/auth/cloud-platform', 
          'https://www.googleapis.com/auth/gmail.send']  # Add Gmail send scope

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

def send_email_with_html_attachment(sender_email, html_file_path):
    """Sends an email with the generated HTML file attached to the original sender."""

    # Build the Gmail service
    service = build('gmail', 'v1', credentials=credentials)

    # Create the email message
    message = MIMEMultipart()
    message['to'] = sender_email
    message['from'] = 'coop@farehard.com'
    message['subject'] = 'Your processed attachment'

    # Attach the HTML file
    with open(html_file_path, 'r', encoding="utf-8") as f:
        html_content = f.read()

    msg_html = MIMEText(html_content, 'html')
    message.attach(msg_html)

    # Encode the message
    raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')

    # Send the email
    try:
        message = (service.users().messages().send(userId='me', body={'raw': raw_message}).execute())
        logging.info(f"Email sent successfully to {sender_email} with message ID: {message['id']}")
    except Exception as e:
        logging.error(f"Error sending email: {e}")

def email_generated_html(event, context):
    """Triggered by a change to a Cloud Storage bucket.
    Args:
        event (dict): Event payload.
        context (google.cloud.functions.Context): Metadata for the event.
    """
    logging.debug(f"Event: {event}")
    logging.debug(f"Context: {context}")

    file_name = event['name']
    logging.debug(f"Processing file: {file_name}")

    # Check if the file is an HTML file in the claude_output folder
    if not file_name.startswith("claude_output/") or not file_name.lower().endswith('.html'):
        logging.info(f"Skipping file: {file_name} (not an HTML file in claude_output folder)")
        return

    # Extract sender's email from file path (adjust this logic as needed based on your file naming)
    sender_email = file_name.split('_')[2]  # Assuming format: claude_output/<zip_filename>/Youre_A_Wizard_Harry_<sender_email>_<rest_of_filename>.html

    # Initialize Cloud Storage client
    storage_client = storage.Client(credentials=credentials)
    bucket = storage_client.bucket(BUCKET_NAME)
    blob = bucket.blob(file_name)

    # Download the HTML file to a temporary location
    temp_file_path = f"/tmp/{file_name.split('/')[-1]}"
    blob.download_to_filename(temp_file_path)

    # Send the email
    send_email_with_html_attachment(sender_email, temp_file_path)

    # Clean up the temporary file
    os.remove(temp_file_path)