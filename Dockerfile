FROM python:3.11-slim

WORKDIR /app

# Sistem bağımlılıkları
RUN apt-get update && apt-get install -y \
    wget \
    libgl1 \
    libglib2.0-0 \
 && rm -rf /var/lib/apt/lists/*

# Python bağımlılıkları
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Uygulama kodunu kopyala
COPY . .

EXPOSE 5000

# Container çalışırken:
# 1) download_assets.sh ile modeller + videolar indir
# 2) Flask app'i başlat
CMD ["sh", "-c", "./scripts/download_assets.sh && python app.py"]
