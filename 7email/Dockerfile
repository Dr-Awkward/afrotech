FROM python:3.10-slim-buster

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire script into the container
COPY main.py .

# Copy the .env file into the container
COPY .env .

# Set the entry point to run the script
CMD ["python", "main.py"]