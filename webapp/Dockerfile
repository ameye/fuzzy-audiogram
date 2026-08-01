FROM python:3.12-slim

WORKDIR /app

# System deps for OpenCV + fontconfig
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 libglib2.0-0 fonts-dejavu && \
    rm -rf /var/lib/apt/lists/*

# Core fuzzy package + webapp
COPY fuzzy_audiogram/ /app/fuzzy_audiogram/
COPY webapp/ /app/webapp/
COPY pyproject.toml /app/

RUN pip install --no-cache-dir -e /app \
    && pip install --no-cache-dir \
       fastapi uvicorn python-multipart \
       numpy pandas matplotlib scikit-fuzzy scikit-learn networkx \
       opencv-python-headless pillow

WORKDIR /app/webapp
EXPOSE 8000

CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
