# Use the Python 3.10 slim-buster image
FROM python:3.10-slim-buster

WORKDIR /app

# Install system dependencies for Pillow
RUN apt-get update && apt-get install -y \
    libjpeg-dev \
    zlib1g-dev \
    libpng-dev \
    libfreetype6-dev \
    liblcms2-dev \
    libtiff-dev \
    tk-dev \
    tcl-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py .

# Set environment variables (or use .env file)
ENV GOOGLE_APPLICATION_CREDENTIALS="/path/to/your/credentials.json"
ENV CLOUD_STORAGE_BUCKET="bonesjustice"
ENV PROJECT_ID="your-project-id"

CMD ["functions-framework", "--target", "process_text_files_in_cloud_storage"]