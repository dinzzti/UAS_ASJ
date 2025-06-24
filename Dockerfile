# Menggunakan image dasar Python 3.9
FROM python:3.9-slim-buster

# Mengatur direktori kerja di dalam kontainer
WORKDIR /app

# Menyalin file requirements.txt ke dalam kontainer
COPY app/requirements.txt .

# Menginstal semua dependensi Python yang terdaftar di requirements.txt
# --no-cache-dir: Memastikan pip tidak menyimpan cache, mengurangi ukuran image
RUN pip install --no-cache-dir -r requirements.txt

# Menyalin seluruh isi folder 'app' ke direktori kerja '/app' di dalam kontainer
# Ini akan mencakup src/, templates/, dan static/
COPY app/ .

# Mengekspos port 5000 di mana aplikasi Flask akan berjalan
EXPOSE 5000

# Menentukan perintah yang akan dijalankan saat kontainer dimulai
CMD ["python", "src/app.py"]
