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

COPY process_jpegs_in_cloud_storage.py .

# Set environment variables (or use .env file)
ENV GOOGLE_APPLICATION_CREDENTIALS="gator.json"
ENV CLOUD_STORAGE_BUCKET="bonesjustice"
ENV PROJECT_ID="alligator-snapper"

CMD ["functions-framework", "--target", "process_jpegs_in_cloud_storage"]