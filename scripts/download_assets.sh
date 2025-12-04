#!/bin/sh
set -e

# Klasörleri oluştur
mkdir -p models
mkdir -p videos

echo "===> YOLO dosyaları indiriliyor (yoksa)..."

# --- YOLOv3-tiny weights ---
if [ ! -f models/yolov3-tiny.weights ]; then
  echo "Downloading yolov3-tiny.weights..."
  wget -O models/yolov3-tiny.weights \
    https://pjreddie.com/media/files/yolov3-tiny.weights
else
  echo "yolov3-tiny.weights zaten mevcut, atlanıyor."
fi

# --- YOLOv3-tiny cfg ---
if [ ! -f models/yolov3-tiny.cfg ]; then
  echo "Downloading yolov3-tiny.cfg..."
  wget -O models/yolov3-tiny.cfg \
    https://raw.githubusercontent.com/pjreddie/darknet/master/cfg/yolov3-tiny.cfg
else
  echo "yolov3-tiny.cfg zaten mevcut, atlanıyor."
fi

# --- coco.names ---
if [ ! -f models/coco.names ]; then
  echo "Downloading coco.names..."
  wget -O models/coco.names \
    https://raw.githubusercontent.com/pjreddie/darknet/master/data/coco.names
else
  echo "coco.names zaten mevcut, atlanıyor."
fi

echo "===> Örnek videolar indiriliyor (yoksa)..."

# GOOGLE DRIVE LINKLERİN (direct download)
PEOPLE_URL="https://drive.google.com/uc?export=download&id=1FTPIufInAryf7gOXmNA8-dUeC_9edXHW"
TRAFFIC_URL="https://drive.google.com/uc?export=download&id=1bUOxnOyQWXBM6qpYWVCFWQzUfJDbjVIS"

if [ ! -f videos/people.mp4 ]; then
  echo "Downloading people.mp4 from: $PEOPLE_URL"
  wget -O videos/people.mp4 "$PEOPLE_URL"
else
  echo "videos/people.mp4 zaten mevcut, atlanıyor."
fi

if [ ! -f videos/traffic.mp4 ]; then
  echo "Downloading traffic.mp4 from: $TRAFFIC_URL"
  wget -O videos/traffic.mp4 "$TRAFFIC_URL"
else
  echo "videos/traffic.mp4 zaten mevcut, atlanıyor."
fi

echo "===> Tüm modeller ve videolar hazır."
