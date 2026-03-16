# Use official Python image
FROM python:3.10

# Set working directory inside container
WORKDIR /app

# Copy all files into container
COPY . .

# Install dependencies
RUN pip install --no-cache-dir flask firebase-admin

# Expose Flask port
EXPOSE 5000

# Run the Flask app
CMD ["python", "app.py"]