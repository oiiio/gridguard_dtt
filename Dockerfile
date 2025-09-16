FROM python:3.11-slim

# Set working directory
WORKDIR /usr/src/app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY web_dashboard.py .
COPY templates/ templates/
COPY static/ static/

# Create shared data directory
RUN mkdir -p /shared_data

# Expose port 5001
EXPOSE 5001

# Run the dashboard
CMD ["python", "web_dashboard.py"]
