# OAUTHC FAI validation data-entry app
FROM python:3.12-slim

WORKDIR /app

COPY oatuhc_protocol/webapp/ /app/webapp/

RUN pip install --no-cache-dir fastapi uvicorn python-multipart

WORKDIR /app/webapp
EXPOSE 8000

# Persist data outside the container via volume at /data
ENV FAI_DB_PATH=/data/oatuhc_fai.db

CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
