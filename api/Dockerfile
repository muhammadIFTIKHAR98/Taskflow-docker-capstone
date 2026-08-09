FROM python:3.12-slim

WORKDIR /app

# Dependencies first - this layer only invalidates when requirements.txt changes
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt


# Source code copied last - changes here don't bust the pip install cache
COPY . .


# Non-root user
RUN useradd --create-home appuser
USER appuser

EXPOSE 5000
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]

