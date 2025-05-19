# Use official Python image
FROM python:alpine

# Set work directory
WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy bot code
COPY bot.py .
COPY .env.example .

# Entrypoint
CMD ["python", "bot.py"]