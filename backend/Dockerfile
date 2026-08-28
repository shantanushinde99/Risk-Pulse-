FROM python:3.12-slim

# Install system dependencies required by Moss SDK and ONNX runtime
RUN apt-get update && apt-get install -y \
    build-essential \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Run the FastAPI server. Render uses the $PORT environment variable.
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
