# Use the official Python 3.10 image from Google Cloud's container registry
FROM python:3.10-slim-buster

# Install Poppler
RUN apt-get update && apt-get install -y poppler-utils 

# Copy your function code
COPY main.py /main.py
COPY requirements.txt /requirements.txt

# Expose the dynamic port
EXPOSE $PORT 

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Set the entry point for your function
CMD ["functions-framework", "--target", "process_archive"]