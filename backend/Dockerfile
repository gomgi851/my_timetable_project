FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# System deps for pillow/scikit-learn
RUN apt-get update && apt-get install -y --no-install-recommends \
    libjpeg62-turbo \
    zlib1g \
    libpng16-16 \
    libfreetype6 \
    libgomp1 \
 && rm -rf /var/lib/apt/lists/*

# Install Python deps (pin via pyproject versions)
RUN pip install --no-cache-dir \
    fastapi>=0.135.1 \
    numpy>=2.4.3 \
    pandas>=3.0.1 \
    pillow>=12.1.1 \
    python-multipart>=0.0.22 \
    scikit-learn>=1.8.0 \
    uvicorn>=0.42.0

COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
