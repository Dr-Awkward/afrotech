FROM python:3.10-slim-buster

# Install system dependencies
RUN apt-get update && apt-get install -y \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py .

# Set environment variables (or use .env file)
ENV GOOGLE_APPLICATION_CREDENTIALS="./gator.json"
ENV CLOUD_STORAGE_BUCKET="bonesjustice"

CMD ["functions-framework", "--target", "process_pdfs_in_cloud_storage"]
