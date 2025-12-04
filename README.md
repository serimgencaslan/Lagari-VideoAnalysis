Bu proje, bir web arayüzü üzerinden:

Video dosyası veya canlı kamera kaynağından görüntü alır,

İnsan ve araç tespiti yapar (HOG + YOLOv3-tiny),

Canlı kişi/araç sayısını gösterir,

Son tespitleri tarih/saat bilgisiyle kaydeder,

Kullanıcı rolleri (admin/user) ile giriş sistemi sunar,

Admin’in kullanıcı ekleme/silme/güncelleme yapabildiği küçük bir yönetim paneli içerir.


1) git clone https://github.com/serimgencaslan/Lagari-VideoAnalysis.git
2) cd Lagari-VideoAnalysis
3) python -m venv venv
4) source venv/bin/activate
5) pip install -r requirements.txt
6) docker build -t video-analytics .
7) docker run -p 5000:5000 video-analytics


User giriş bilgileri: (username: demo password: Demo123)
Admin giriş bilgileri: (username: admin password: Admin123)
