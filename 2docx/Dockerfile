FROM python:3.10-slim-buster

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py .

# Set environment variables (or use .env file)
ENV GOOGLE_APPLICATION_CREDENTIALS="gator.json"
ENV CLOUD_STORAGE_BUCKET="bonesjustice"
ENV PROJECT_ID="alligatorsnapper"

CMD ["functions-framework", "--target", "process_attachments"]