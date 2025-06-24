import os
import time
import psycopg2
from psycopg2.extras import RealDictCursor
from flask import Flask, render_template, request, redirect, url_for, abort
from dotenv import load_dotenv

# --- Load environment variables from .env file ---
# Memuat variabel dari file .env di root proyek (uas-project/)
# ke dalam os.environ, sehingga aplikasi Flask bisa membacanya.
load_dotenv(os.path.join(os.path.dirname(__file__), '../../.env'))

# --- Konfigurasi Aplikasi Flask ---
app = Flask(__name__,
            template_folder='../templates', # Mengarahkan Flask ke folder templates relatif dari app.py
            static_folder='../static')    # Mengarahkan Flask ke folder static relatif dari app.py

# --- Konfigurasi Database dari Environment Variables ---
# Mengambil kredensial database dari variabel lingkungan yang sudah dimuat.
DB_NAME = os.environ.get('POSTGRES_DB')
DB_USER = os.environ.get('POSTGRES_USER')
DB_PASSWORD = os.environ.get('POSTGRES_PASSWORD')
DB_HOST = os.environ.get('DATABASE_HOST')
DB_PORT = os.environ.get('DATABASE_PORT', '5432')

print(f"Flask Template Directory: {app.template_folder}")
print(f"Flask Static Directory: {app.static_folder}")
print(f"Mencoba terhubung ke database di {DB_HOST}:{DB_PORT}...")

def get_db_connection():
    """
    Membuat dan mengembalikan objek koneksi ke database PostgreSQL.
    Mencetak pesan kesalahan jika koneksi gagal.
    """
    conn = None
    try:
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT,
            connect_timeout=5 # Timeout koneksi database dalam detik
        )
        print("Koneksi database berhasil!")
        return conn
    except Exception as e:
        print(f"Kesalahan koneksi database: {e}")
        return None

def ensure_table_exists():
    """
    Memastikan tabel 'kpop_items' ada di database. Membuatnya jika belum ada.
    Fungsi ini juga akan menambahkan kolom 'image_url' jika belum ada.
    """
    conn = get_db_connection()
    if conn:
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS kpop_items (
                        id SERIAL PRIMARY KEY,
                        name VARCHAR(100) NOT NULL,
                        description TEXT,
                        image_url TEXT 
                    );
                """)
                conn.commit()
                print("Tabel 'kpop_items' berhasil diperiksa/dibuat.")
        except Exception as e:
            print(f"Kesalahan saat memastikan tabel ada: {e}")
            if conn:
                conn.rollback()
        finally:
            conn.close()
    else:
        print("Tidak dapat membuat koneksi database untuk memastikan tabel.")

print(f"Mencoba koneksi database awal dengan host: {DB_HOST}, port: {DB_PORT}...")
max_retries = 15 
retry_delay = 3 
for i in range(max_retries):
    try:
        conn_test = get_db_connection()
        if conn_test:
            conn_test.close() 
            ensure_table_exists() # Pastikan tabel ada setelah koneksi berhasil
            print("Koneksi database awal berhasil dan tabel diperiksa.")
            break # Keluar dari loop jika koneksi berhasil
    except Exception as e:
        print(f"Mencoba kembali koneksi database ({i+1}/{max_retries}): {e}")
    time.sleep(retry_delay)
else:
    print("Gagal terhubung ke database setelah beberapa kali percobaan. Pastikan service 'db' berjalan dan dapat diakses.")
    exit(1)


# --- Rute Flask (Definisi Endpoint Aplikasi) ---

@app.route('/')
def welcome():
    """
    Rute utama ('/') sekarang akan menampilkan halaman selamat datang.
    """
    return render_template('welcome.html')

@app.route('/collection') # Rute baru untuk halaman koleksi (sebelumnya '/')
def index():
    """
    Rute '/collection' untuk menampilkan daftar semua item koleksi Kpop.
    Mengambil data dari database dan merendernya menggunakan template 'index.html'.
    """
    conn = get_db_connection()
    kpop_items = []
    if conn:
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM kpop_items ORDER BY id DESC;") # Mengambil semua item, diurutkan dari yang terbaru
                kpop_items = cur.fetchall() # Mengambil semua baris hasil query
        except Exception as e:
            print(f"Kesalahan saat mengambil item: {e}")
        finally:
            conn.close() # Pastikan koneksi database ditutup
    # Merender template 'index.html' dan meneruskan daftar item ke template
    return render_template('index.html', kpop_items=kpop_items)

@app.route('/create', methods=['GET', 'POST'])
def create():
    """
    Rute '/create' untuk menambahkan item koleksi Kpop baru.
    - Metode GET: Menampilkan formulir penambahan item.
    - Metode POST: Memproses data formulir dan menyimpan item baru ke database.
    """
    if request.method == 'POST':
        name = request.form['name'].strip()
        description = request.form['description'].strip()
        image_url = request.form['image_url'].strip()

        if name:
            conn = get_db_connection()
            if conn:
                try:
                    with conn.cursor() as cur:
                        cur.execute(
                            "INSERT INTO kpop_items (name, description, image_url) VALUES (%s, %s, %s);",
                            (name, description, image_url)
                        )
                    conn.commit()
                except Exception as e:
                    print(f"Kesalahan saat menyisipkan item: {e}")
                    conn.rollback()
                finally:
                    conn.close()
        return redirect(url_for('index')) # Redirect ke /collection (nama fungsi index sekarang)
    return render_template('create.html')

@app.route('/edit/<int:item_id>', methods=['GET', 'POST'])
def edit(item_id):
    """
    Rute '/edit/<int:item_id>' untuk mengedit item koleksi Kpop yang sudah ada.
    - Metode GET: Mengambil data item berdasarkan ID dan menampilkan formulir edit yang terisi.
    - Metode POST: Memproses data formulir dan memperbarui item di database.
    """
    conn = get_db_connection()
    item = None
    if conn:
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM kpop_items WHERE id = %s;", (item_id,))
                item = cur.fetchone()
        except Exception as e:
            print(f"Kesalahan saat mengambil item untuk diedit: {e}")
        finally:
            conn.close()

    if not item:
        abort(404)

    if request.method == 'POST':
        name = request.form['name'].strip()
        description = request.form['description'].strip()
        image_url = request.form['image_url'].strip()

        if name:
            conn = get_db_connection()
            if conn:
                try:
                    with conn.cursor() as cur:
                        cur.execute(
                            "UPDATE kpop_items SET name = %s, description = %s, image_url = %s WHERE id = %s;",
                            (name, description, image_url, item_id)
                        )
                    conn.commit()
                except Exception as e:
                    print(f"Kesalahan saat memperbarui item: {e}")
                    conn.rollback()
                finally:
                    conn.close()
        return redirect(url_for('index')) # Redirect ke /collection (nama fungsi index sekarang)
    return render_template('edit.html', item=item)

@app.route('/delete/<int:item_id>', methods=['POST'])
def delete(item_id):
    """Menghapus item koleksi Kpop."""
    conn = get_db_connection()
    if conn:
        try:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM kpop_items WHERE id = %s;", (item_id,))
            conn.commit()
        except Exception as e:
            print(f"Kesalahan saat menghapus item: {e}")
            conn.rollback()
        finally:
            conn.close()
    return redirect(url_for('index')) # Redirect ke /collection (nama fungsi index sekarang)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
