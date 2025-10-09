# Use Python 3.10 base image
FROM python:3.10-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    python3-dev \
    musl-dev \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Verify all imports work before copying code
RUN python -c "import django_filters, rest_framework, corsheaders, environ, drf_yasg; print('All dependencies imported successfully')"

# Copy project code
COPY . .

# Expose port 8000 with 'docker run -p 8000:8000'
EXPOSE 8000

# Command to run the application
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "messaging_app.wsgi:application"]