# Use an official lightweight Python image
FROM python:3.10-slim

# Set the working directory inside the container to root context
WORKDIR /app

# Install system utilities needed for potential network/dicom operations
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker's caching system
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of your application files into the container
COPY . .

# Expose the standard Streamlit port so we can view it outside the container
EXPOSE 8501

# We will let docker-compose override the starting commands for the watcher vs. dashboard
CMD ["python"]