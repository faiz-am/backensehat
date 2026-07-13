from flask import Flask, jsonify, render_template, request, redirect, session
from flask_mysqldb import MySQL
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
import os
import json
from threading import Thread
import random
from dotenv import load_dotenv
from flask_jwt_extended import (
    JWTManager,
    create_access_token,
    jwt_required,
    get_jwt_identity
)
from flask_mail import Mail, Message
import firebase_admin
from firebase_admin import credentials, auth
import google.generativeai as genai


# Load .env
load_dotenv()

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*", "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"], "allow_headers": ["Content-Type", "Authorization"]}})

# =========================
# GEMINI CHATBOT CONFIG
# =========================
gemini_key = os.getenv("GEMINI_API_KEY")
chatbot_model = None
if gemini_key and gemini_key != "your_gemini_api_key_here":
    try:
        genai.configure(api_key=gemini_key)
        chatbot_model = genai.GenerativeModel(
            "gemini-1.5-flash",
            system_instruction=(
                "Anda adalah Asisten Kesehatan Sehat Kita, asisten kesehatan interaktif di aplikasi 'Sehat Kita'. "
                "Tugas Anda adalah membantu menjawab pertanyaan pengguna seputar kesehatan, diet, nutrisi, olahraga, hidrasi, "
                "dan penggunaan aplikasi Sehat Kita secara ramah, informatif, dan ringkas dalam bahasa Indonesia. "
                "Gunakan format teks polos (plain text) atau gunakan simbol emoticon/emoji menarik, batasi penggunaan format markdown tebal/list jika tidak diperlukan. "
                "Berikan jawaban yang praktis dan dukung pengguna untuk hidup lebih sehat."
            )
        )
        print("Gemini AI Chatbot berhasil dikonfigurasi!")
    except Exception as e:
        print(f"Gagal mengonfigurasi Gemini: {e}")
else:
    print("Warning: GEMINI_API_KEY tidak disetel atau masih bernilai default. Chatbot akan menggunakan fallback rule-based.")



# =========================
# MAIL CONFIG
# =========================
app.config['MAIL_SERVER'] = os.getenv("MAIL_SERVER", 'smtp.gmail.com')
app.config['MAIL_PORT'] = int(os.getenv("MAIL_PORT", 465))
app.config['MAIL_USERNAME'] = os.getenv("MAIL_USERNAME")
app.config['MAIL_PASSWORD'] = os.getenv("MAIL_PASSWORD")
app.config['MAIL_USE_TLS'] = False  # Langsung diisi False tanpa os.getenv
app.config['MAIL_USE_SSL'] = True   # Langsung diisi True tanpa os.getenv
mail = Mail(app)
print("MAIL_SERVER =", app.config["MAIL_SERVER"])
print("MAIL_PORT =", app.config["MAIL_PORT"])
print("MAIL_USERNAME =", app.config["MAIL_USERNAME"])

# =========================
# MYSQL CONFIG
# =========================
app.config['MYSQL_HOST'] = os.getenv("MYSQLHOST")
app.config['MYSQL_PORT'] = int(os.getenv("MYSQLPORT", 3306))
app.config['MYSQL_USER'] = os.getenv("MYSQLUSER")
app.config['MYSQL_PASSWORD'] = os.getenv("MYSQLPASSWORD")
app.config['MYSQL_DB'] = os.getenv("MYSQLDATABASE")
# =========================
# JWT CONFIG
# =========================
app.config['JWT_SECRET_KEY'] = os.getenv("JWT_SECRET_KEY")
jwt = JWTManager(app)

mysql = MySQL()
from makanan import makanan_bp
app.register_blueprint(makanan_bp, url_prefix='/api')
mysql.init_app(app)
# =========================
# FIREBASE CONFIG
# =========================
# =========================
# FIREBASE CONFIG
# =========================
try:
    if not firebase_admin._apps:
        firebase_credentials = os.getenv("FIREBASE_CREDENTIALS")

        if firebase_credentials:
            cred_dict = json.loads(firebase_credentials)
            cred = credentials.Certificate(cred_dict)
            firebase_admin.initialize_app(cred)
            print("Firebase berhasil diinisialisasi!")
        else:
            print("FIREBASE_CREDENTIALS tidak ditemukan.")
except Exception as e:
    print(f"Firebase error: {e}")
# =========================
# ROOT API
# =========================
@app.route('/', methods=['GET'])
def root():
    return jsonify({"message": "api aktif", "status": "running"}), 200

# =========================
# PROFILE API (TANPA JWT - Sesuai dengan Flutter kamu saat ini)
# =========================
@app.route('/api/ambil-profil', methods=['GET'])
def ambil_profil():
    username = request.args.get('username', '').strip()
    
    if not username:
        return jsonify({"success": False, "message": "Username diperlukan"}), 400

    try:
        cur = mysql.connection.cursor()
        cur.execute("SELECT id, username, nama, telepon, umur, tinggi, berat FROM users WHERE username = %s", (username,))
        user = cur.fetchone()
        cur.close()

        if not user:
            return jsonify({"success": False, "message": "User tidak ditemukan"}), 404

        return jsonify({
            "success": True,
            "data": {
                "id": user[0],
                "username": user[1],
                "nama": user[2] if user[2] else "",
                "telepon": user[3] if user[3] else "",
                "umur": user[4] if user[4] else "",
                "tinggi": user[5] if user[5] else "",
                "berat": user[6] if user[6] else ""
            }
        }), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/update-profil', methods=['POST'])
def update_profil():
    data = request.get_json()
    
    username = data.get('username', '').strip()
    nama = data.get('nama', '').strip()
    telepon = data.get('telepon', '').strip()
    umur = data.get('umur', 0)
    tinggi = data.get('tinggi', 0.0)
    berat = data.get('berat', 0.0)

    if not username:
        return jsonify({"success": False, "message": "Username tidak boleh kosong"}), 400

    try:
        cur = mysql.connection.cursor()
        cur.execute("""
            UPDATE users 
            SET nama = %s, telepon = %s, umur = %s, tinggi = %s, berat = %s 
            WHERE username = %s
        """, (nama, telepon, umur, tinggi, berat, username))
        
        mysql.connection.commit()
        cur.close()
        
        return jsonify({"success": True, "message": "Profil berhasil diperbarui di database!"}), 200
    except Exception as e:
        mysql.connection.rollback()
        return jsonify({"success": False, "message": str(e)}), 500

# Tambahkan di bagian bawah app.py
@app.route('/api/status-kesehatan', methods=['GET'])
def get_status_kesehatan():
    username = request.args.get('username')
    cur = mysql.connection.cursor()
    cur.execute("SELECT tinggi, berat FROM users WHERE username = %s", (username,))
    user = cur.fetchone()
    cur.close()

    if not user or not user[0]: return jsonify({"status": "Normal", "target_kalori": 2000}), 200
        
    tinggi_m = user[0] / 100
    berat = user[1]
    
    # Perhitungan BMI (Sumber: World Health Organization - BMI Classification)
    bmi = berat / (tinggi_m * tinggi_m)
    
    # Logika Medis: Obesitas jika BMI >= 27
    if bmi >= 27:
        return jsonify({"status": "Obesitas", "target_kalori": 1600}), 200
    elif bmi < 18.5:
        return jsonify({"status": "Kurang Gizi", "target_kalori": 2200}), 200
    else:
        return jsonify({"status": "Normal", "target_kalori": 2000}), 200


# Fungsi helper untuk mengirim email secara async di background
def send_async_email(flask_app, msg):
    with flask_app.app_context():
        try:
            mail.send(msg)
            print("LOG: Email OTP berhasil dikirim di background!")
        except Exception as e:
            print(f"LOG ERROR: Gagal mengirim email OTP di background: {e}")
# =========================
# REGISTER API (SINKRONUS UNTUK TESTING ERROR EMAIL)
# =========================
@app.route('/api/register', methods=['POST'])
def register():
    data = request.get_json()

    username = data.get('username', '').strip()
    password_raw = data.get('password', '')

    if not username or not password_raw:
        return jsonify({"success": False, "message": "Isi semua field"}), 400

    password = generate_password_hash(password_raw)
    cur = mysql.connection.cursor()

    try:
        # 1. Cek apakah username sudah ada
        cur.execute("SELECT * FROM users WHERE username=%s", (username,))
        user = cur.fetchone()

        if user:
            return jsonify({"success": False, "message": "Username sudah digunakan"}), 400

        # 2. Generate OTP & Insert ke database
        otp = str(random.randint(100000, 999999))
        cur.execute(
            "INSERT INTO users(username, password, is_verified, otp) VALUES(%s,%s,%s,%s)",
            (username, password, 0, otp)
        )
        
        # 3. Commit data ke database TERLEBIH DAHULU agar data aman tersimpan
        mysql.connection.commit()
        print("LOG: Data user berhasil di-insert dan di-commit.")

        # 4. Siapkan format Email
        msg = Message(
            'Kode Verifikasi OTP - Sehat App',
            sender=app.config['MAIL_USERNAME'],
            recipients=[username]  # Pastikan input 'username' saat daftar adalah email aktif (contoh: riyannewskull@gmail.com)
        )
        msg.html = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #e0e0e0; border-radius: 12px; background-color: #ffffff;">
            <div style="text-align: center; margin-bottom: 20px;">
                <h1 style="color: #2196F3; margin: 0;">Sehat App</h1>
                <p style="color: #666; margin: 5px 0 0 0;">Verifikasi Akun Anda</p>
            </div>
            <hr style="border: 0; border-top: 1px solid #eee; margin: 20px 0;">
            <p>Halo,</p>
            <p>Terima kasih telah mendaftar di Sehat App. Silakan gunakan kode OTP di bawah ini untuk menyelesaikan pendaftaran Anda:</p>
            <div style="text-align: center; margin: 30px 0; padding: 15px; background-color: #f0f6ff; border-radius: 8px;">
                <span style="font-size: 32px; font-weight: bold; letter-spacing: 5px; color: #1a237e;">{otp}</span>
            </div>
            <p style="color: #555; font-size: 14px;">Kode OTP ini bersifat rahasia. Jangan bagikan kode ini kepada siapa pun.</p>
            <hr style="border: 0; border-top: 1px solid #eee; margin: 20px 0;">
            <p style="color: #999; font-size: 12px; text-align: center; margin: 0;">Ini adalah email otomatis, mohon tidak membalas email ini.</p>
        </div>
        """
        
        # 5. Kirim langsung secara sinkronus agar kita bisa menangkap detail error jika gagal
        print(f"LOG: Mencoba mengirim email ke {username}...")
        mail.send(msg)
        print("LOG: Email OTP berhasil terkirim secara synchronous!")

        return jsonify({"success": True, "message": "Register berhasil, silakan cek email Anda untuk kode OTP."}), 201

    except Exception as e:
        mysql.connection.rollback()
        print(f"LOG ERROR: Terjadi kegagalan registrasi atau pengiriman email: {e}")
        # Kembalikan detail error agar kamu bisa melihat langsung pesan error aslinya dari Postman/aplikasi
        return jsonify({
            "success": False, 
            "message": f"Terjadi kesalahan saat mengirim email: {str(e)}"
        }), 500
        
    finally:
        cur.close()

# =========================
# VERIFY OTP API
# =========================
@app.route('/api/verify-otp', methods=['POST'])
def verify_otp():
    data = request.get_json()

    username = data.get('username', '').strip()
    otp_input = data.get('otp', '').strip()

    if not username or not otp_input:
        return jsonify({"success": False, "message": "Email dan OTP tidak boleh kosong"}), 400

    cur = mysql.connection.cursor()
    cur.execute("SELECT id, otp, is_verified FROM users WHERE username=%s", (username,))
    user = cur.fetchone()

    if not user:
        cur.close()
        return jsonify({"success": False, "message": "User tidak ditemukan"}), 404

    db_otp = user[1]
    is_verified = user[2]

    if is_verified:
        cur.close()
        return jsonify({"success": False, "message": "Akun sudah terverifikasi"}), 400

    if db_otp == otp_input:
        cur.execute("UPDATE users SET is_verified = 1 WHERE username=%s", (username,))
        mysql.connection.commit()
        cur.close()
        return jsonify({"success": True, "message": "Email berhasil diverifikasi! Silakan login."})
    else:
        cur.close()
        return jsonify({"success": False, "message": "Kode OTP salah atau tidak valid"}), 400


# =========================
# FIREBASE LOGIN API
# =========================
@app.route('/api/firebase-login', methods=['POST'])
def firebase_login():
    data = request.get_json()
    id_token = data.get('id_token')

    if not id_token:
        return jsonify({"success": False, "message": "ID Token required"}), 400

    try:
        # Verifikasi token ID dengan Firebase Admin SDK
        decoded_token = auth.verify_id_token(id_token)
        uid = decoded_token['uid']
        email = decoded_token.get('email')

        if not email:
            return jsonify({"success": False, "message": "Email not found in token"}), 400

        cur = mysql.connection.cursor()

        # Cari apakah user sudah ada di database kita
        cur.execute("SELECT id, username FROM users WHERE username = %s", (email,))
        user = cur.fetchone()

        if not user:
            # Jika user belum ada, buat akun baru secara otomatis dengan status terverifikasi (is_verified = 1)
            # Dan password kosong karena login dengan Google
            cur.execute(
                "INSERT INTO users(username, password, is_verified, otp) VALUES(%s, %s, %s, %s)",
                (email, '', 1, '')
            )
            mysql.connection.commit()

        cur.close()

        # Buat JWT token untuk login ke backend
        token = create_access_token(identity=email)
        return jsonify({"success": True, "token": token})

    except Exception as e:
        print(f"Firebase verification error: {e}")
        return jsonify({"success": False, "message": "Token tidak valid atau kedaluwarsa"}), 401


# =========================
# LOGIN API
# =========================
@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()

    username = data['username']
    password = data['password']

    cur = mysql.connection.cursor()
    cur.execute("SELECT id, username, password, is_verified FROM users WHERE username=%s", (username,))
    user = cur.fetchone()
    cur.close()

    if user and check_password_hash(user[2], password):
        if not user[3]:
            return jsonify({"success": False, "message": "Belum verifikasi"}), 403

        token = create_access_token(identity=username)
        return jsonify({"success": True, "token": token})

    return jsonify({"success": False, "message": "Login gagal"}), 401

# =========================
# GET USERS (JWT)
# =========================
@app.route('/api/users')
@jwt_required()
def get_users():
    cur = mysql.connection.cursor()
    cur.execute("SELECT id, username FROM users")
    rows = cur.fetchall()
    cur.close()

    users = [{"id": r[0], "username": r[1]} for r in rows]

    return jsonify({"users": users, "success": True})

# =========================
# ADMIN LOGIN API
# =========================
@app.route('/api/admin/login', methods=['POST'])
def admin_login():
    data = request.get_json()
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()

    if not username or not password:
        return jsonify({"success": False, "message": "Username dan password tidak boleh kosong"}), 400

    cur = mysql.connection.cursor()
    cur.execute("SELECT id, username, password FROM admins WHERE username = %s", (username,))
    admin = cur.fetchone()
    cur.close()

    if admin:
        stored_password = admin[2]
        # Mendukung pencocokan plain text (admin123) atau check_password_hash
        if stored_password == password or check_password_hash(stored_password, password):
            token = create_access_token(identity=username)
            return jsonify({
                "success": True,
                "token": token,
                "username": username
            })

    return jsonify({"success": False, "message": "Username atau password admin salah"}), 401

# =========================
# GET TIPS API (PUBLIC)
# =========================
@app.route('/api/tips', methods=['GET'])
def get_tips():
    cur = mysql.connection.cursor()
    cur.execute("SELECT id, title, description, icon FROM tips")
    rows = cur.fetchall()
    cur.close()

    tips = [{"id": r[0], "title": r[1], "description": r[2], "icon": r[3]} for r in rows]
    return jsonify(tips)

# =========================
# GET CHART STATS API (JWT PROTECTED)
# =========================
@app.route('/api/admin/chart-stats', methods=['GET'])
@jwt_required()
def get_chart_stats():
    try:
        cur = mysql.connection.cursor()
        
        # 1. User stats (Verified vs Unverified)
        cur.execute("SELECT is_verified, COUNT(*) FROM users GROUP BY is_verified")
        user_rows = cur.fetchall()
        user_stats = {"verified": 0, "unverified": 0}
        for row in user_rows:
            if row[0] == 1:
                user_stats["verified"] = int(row[1])
            else:
                user_stats["unverified"] = int(row[1])
                
        # 2. Tips stats (Grouped by Icon)
        cur.execute("SELECT icon, COUNT(*) FROM tips GROUP BY icon")
        tip_rows = cur.fetchall()
        tips_stats = {r[0] if r[0] else "default": int(r[1]) for r in tip_rows}
        
        # 3. Riwayat stats (Grouped by Condition/Status)
        cur.execute("SELECT status_kondisi, COUNT(*) FROM riwayat_gizis GROUP BY status_kondisi")
        riwayat_condition_rows = cur.fetchall()
        riwayat_conditions = {r[0] if r[0] else "Normal": int(r[1]) for r in riwayat_condition_rows}
        
        # 4. Riwayat activity (Grouped by Date for last 7 days)
        cur.execute("""
            SELECT DATE_FORMAT(created_at, '%Y-%m-%d') as date, COUNT(*) 
            FROM riwayat_gizis 
            GROUP BY DATE(created_at) 
            ORDER BY date ASC 
            LIMIT 7
        """)
        riwayat_activity_rows = cur.fetchall()
        riwayat_activity = [{"date": r[0], "count": int(r[1])} for r in riwayat_activity_rows]
        
        cur.close()
        
        return jsonify({
            "success": True,
            "users": user_stats,
            "tips": tips_stats,
            "riwayat_conditions": riwayat_conditions,
            "riwayat_activity": riwayat_activity
        }), 200
    except Exception as e:
        print(f"Error getting chart stats: {e}")
        return jsonify({"success": False, "message": str(e)}), 500

# =========================
# ADMIN TIPS CRUD API (JWT PROTECTED)
# =========================
@app.route('/api/admin/tips', methods=['POST'])
@jwt_required()
def add_tip():
    data = request.get_json()
    title = data.get('title', '').strip()
    description = data.get('description', '').strip()
    icon = data.get('icon', 'heartbeat').strip()

    if not title or not description:
        return jsonify({"success": False, "message": "Judul dan deskripsi tip tidak boleh kosong"}), 400

    cur = mysql.connection.cursor()
    cur.execute(
        "INSERT INTO tips(title, description, icon) VALUES(%s, %s, %s)",
        (title, description, icon)
    )
    mysql.connection.commit()
    cur.close()

    return jsonify({"success": True, "message": "Tip kesehatan berhasil ditambahkan!"})

@app.route('/api/admin/tips/<int:tip_id>', methods=['PUT'])
@jwt_required()
def update_tip(tip_id):
    data = request.get_json()
    title = data.get('title', '').strip()
    description = data.get('description', '').strip()
    icon = data.get('icon', 'heartbeat').strip()

    if not title or not description:
        return jsonify({"success": False, "message": "Judul dan deskripsi tip tidak boleh kosong"}), 400

    cur = mysql.connection.cursor()
    cur.execute("SELECT id FROM tips WHERE id = %s", (tip_id,))
    tip = cur.fetchone()

    if not tip:
        cur.close()
        return jsonify({"success": False, "message": "Tip tidak ditemukan"}), 404

    cur.execute(
        "UPDATE tips SET title = %s, description = %s, icon = %s WHERE id = %s",
        (title, description, icon, tip_id)
    )
    mysql.connection.commit()
    cur.close()

    return jsonify({"success": True, "message": "Tip kesehatan berhasil diperbarui!"})

@app.route('/api/admin/tips/<int:tip_id>', methods=['DELETE'])
@jwt_required()
def delete_tip(tip_id):
    cur = mysql.connection.cursor()
    cur.execute("SELECT id FROM tips WHERE id = %s", (tip_id,))
    tip = cur.fetchone()

    if not tip:
        cur.close()
        return jsonify({"success": False, "message": "Tip tidak ditemukan"}), 404

    cur.execute("DELETE FROM tips WHERE id = %s", (tip_id,))
    mysql.connection.commit()
    cur.close()

    return jsonify({"success": True, "message": "Tip kesehatan berhasil dihapus!"})
# =========================
# CHATBOT API
# =========================
def get_rule_based_response(message):
    clean_text = message.lower().strip()
    if "makanan" in clean_text and ("sehat" in clean_text or "terbaik" in clean_text or "paling" in clean_text):
        return (
            "Makanan paling sehat meliputi:\n"
            "1. 🥬 Sayuran Hijau (bayam, brokoli, kangkung) - kaya serat & zat besi.\n"
            "2. 🥑 Buah-buahan (alpukat, apel, beri) - kaya vitamin & antioksidan.\n"
            "3. 🍗 Protein Tanpa Lemak (dada ayam, ikan, tempe, tahu) - membangun jaringan otot.\n"
            "4. 🫘 Kacang-kacangan & Biji-bijian - sumber lemak sehat omega-3.\n"
            "5. 🌾 Karbohidrat Kompleks (nasi merah, oatmeal, ubi) - energi tahan lama."
        )
    elif "diet" in clean_text or "berat" in clean_text or "turun" in clean_text:
        return (
            "Tips menurunkan berat badan secara sehat:\n"
            "1. 🥗 Lakukan defisit kalori ringan (kurangi 300-500 kalori harian).\n"
            "2. 🏃‍♂️ Tingkatkan aktivitas fisik / olahraga minimal 150 menit per minggu.\n"
            "3. 🥩 Penuhi kebutuhan protein agar kenyang lebih lama dan otot terjaga.\n"
            "4. 💧 Minum air putih sebelum makan.\n"
            "5. 😴 Tidur cukup 7-8 jam per hari, karena kurang tidur meningkatkan hormon lapar."
        )
    elif "gula" in clean_text or "diabetes" in clean_text or "manis" in clean_text:
        return (
            "Cara mengontrol kadar gula darah:\n"
            "1. 🍚 Batasi karbohidrat sederhana (nasi putih berlebih, roti putih).\n"
            "2. 🍩 Hindari minuman manis, sirup, dan soda.\n"
            "3. 🥦 Perbanyak makanan tinggi serat (sayuran, kacang-kacangan).\n"
            "4. 🚶‍♂️ Lakukan jalan kaki 10-15 menit setelah makan.\n"
            "5. 📊 Pantau asupan gula harian Anda (maksimal 4 sendok makan atau 50 gram sehari)."
        )
    elif "garam" in clean_text or "sodium" in clean_text or "natrium" in clean_text or "hipertensi" in clean_text or "tensi" in clean_text:
        return (
            "Cara membatasi konsumsi garam (natrium):\n"
            "1. 🍟 Kurangi makanan cepat saji, camilan asin, dan makanan kalengan.\n"
            "2. 🌿 Gunakan rempah alami (bawang, ketumbar, lemon) sebagai penyedap rasa pengganti garam.\n"
            "3. 🥫 Selalu baca label informasi nilai gizi (pilih produk rendah natrium).\n"
            "4. 🥤 Perbanyak minum air putih untuk membantu tubuh mengeluarkan kelebihan natrium.\n"
            "5. 🧂 Batasi garam meja maksimal 1 sendok teh (2000mg natrium) per hari."
        )
    elif "air" in clean_text or "minum" in clean_text or "gelas" in clean_text or "hidrasi" in clean_text:
        return (
            "Pentingnya hidrasi tubuh harian:\n"
            "1. 💧 Kebutuhan rata-rata orang dewasa adalah 8 gelas atau 2 liter sehari.\n"
            "2. 🏃‍♂️ Jika Anda berolahraga atau cuaca panas, tambahkan asupan air Anda.\n"
            "3. 🍋 Manfaat air putih: membuang racun, melancarkan pencernaan, menjaga elastisitas kulit, dan mencegah dehidrasi."
        )
    elif "riwayat" in clean_text or "grafik" in clean_text or "perkembangan" in clean_text:
        return (
            "Untuk melihat riwayat perkembangan gizi Anda:\n"
            "1. 📊 Masuk ke menu 'Riwayat' (tab kedua dari bawah).\n"
            "2. Anda akan melihat daftar riwayat makan pagi, siang, malam beserta status kondisi kesehatan Anda (Normal, Kurang Gizi, atau Obesitas)."
        )
    elif "input" in clean_text or "tambah" in clean_text or "catat" in clean_text or "makanan baru" in clean_text:
        return (
            "Cara mencatat/menginput makanan baru:\n"
            "1. ➕ Tekan tab 'Input' (ikon plus di bagian tengah navigasi bawah).\n"
            "2. Masukkan nama makanan (misal: 'Nasi Goreng').\n"
            "3. Tentukan waktu makan (Pagi, Siang, atau Malam).\n"
            "4. Isi jumlah kalori, protein, sodium (garam), dan gula yang Anda konsumsi.\n"
            "5. Tekan tombol 'Simpan' untuk mencatat ke database."
        )
    elif "fitur" in clean_text or "aplikasi" in clean_text or "apa saja" in clean_text:
        return (
            "Fitur unggulan di aplikasi Sehat Kita:\n"
            "1. 🩺 Dashboard Pemantauan - memantau skor kesehatan, kalori harian, gula, dan garam.\n"
            "2. 📝 Pencatatan Gizi - fitur input makanan harian untuk pagi, siang, dan malam.\n"
            "3. 📊 Riwayat Gizi - grafik visualisasi riwayat kesehatan Anda.\n"
            "4. 💡 Tips Kesehatan - tips harian yang diperbarui langsung oleh admin.\n"
            "5. 💬 Chatbot AI - asisten kesehatan interaktif Anda."
        )
    elif any(word in clean_text for word in ["halo", "hai", "pagi", "siang", "sore", "malam", "assalamualaikum"]):
        return "Halo! 👋 Saya adalah Asisten Kesehatan Sehat Kita. Ada yang bisa saya bantu hari ini tentang tips kesehatan atau pola makan sehat?"
    elif any(word in clean_text for word in ["terima kasih", "makasih", "thank you"]):
        return "Sama-sama! 😊 Senang bisa membantu Anda. Selalu jaga kesehatan dan pola makan seimbang ya!"
    else:
        return (
            "Maaf, saya kurang memahami pertanyaan Anda. 😅\n\n"
            "Coba tanyakan hal-macam berikut:\n"
            "• 'makanan sehat paling bagus apa saja?'\n"
            "• 'bagaimana tips diet?'\n"
            "• 'cara mengontrol gula darah'\n"
            "• 'berapa kebutuhan air harian?'\n"
            "• 'bagaimana cara input makanan?'"
        )

@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.get_json()
    if not data or 'message' not in data:
        return jsonify({"success": False, "message": "Pesan tidak boleh kosong"}), 400
    
    user_message = data['message']
    
    if chatbot_model:
        try:
            response = chatbot_model.generate_content(user_message)
            reply = response.text
            return jsonify({"success": True, "reply": reply.strip()})
        except Exception as e:
            print(f"Error calling Gemini API: {e}")
            reply = get_rule_based_response(user_message)
            return jsonify({"success": True, "reply": reply})
    else:
        reply = get_rule_based_response(user_message)
        return jsonify({"success": True, "reply": reply})

# =========================
# BIG DATA ANALYTICS API
# =========================
@app.route('/api/bigdata/analytics', methods=['GET'])
def get_bigdata_analytics():
    try:
        cur = mysql.connection.cursor()
        
        # 1. Total foods & Health category counts
        cur.execute("SELECT health_status, COUNT(*) FROM big_data_analysis GROUP BY health_status")
        rows = cur.fetchall()
        summary = {
            "total_foods": 0,
            "healthy_count": 0,
            "less_healthy_count": 0,
            "avg_calories": 0.0,
            "avg_protein": 0.0,
            "avg_fat": 0.0,
            "avg_carbs": 0.0
        }
        for r in rows:
            status = r[0]
            count = int(r[1])
            summary["total_foods"] += count
            if status == "Healthy":
                summary["healthy_count"] = count
            elif status == "Less Healthy":
                summary["less_healthy_count"] = count

        # 2. Averages of nutrients
        cur.execute("SELECT AVG(calories), AVG(protein_g), AVG(fat_total_g), AVG(carbs_g) FROM big_data_analysis")
        avg_row = cur.fetchone()
        if avg_row and summary["total_foods"] > 0:
            summary["avg_calories"] = round(float(avg_row[0]) if avg_row[0] is not None else 0.0, 2)
            summary["avg_protein"] = round(float(avg_row[1]) if avg_row[1] is not None else 0.0, 2)
            summary["avg_fat"] = round(float(avg_row[2]) if avg_row[2] is not None else 0.0, 2)
            summary["avg_carbs"] = round(float(avg_row[3]) if avg_row[3] is not None else 0.0, 2)

        # 3. Top 5 foods by calories
        cur.execute("SELECT name, calories FROM big_data_analysis ORDER BY calories DESC LIMIT 5")
        cal_rows = cur.fetchall()
        top_calories = [{"name": r[0], "calories": float(r[1])} for r in cal_rows]

        # 4. Top 5 foods by protein
        cur.execute("SELECT name, protein_g FROM big_data_analysis ORDER BY protein_g DESC LIMIT 5")
        prot_rows = cur.fetchall()
        top_protein = [{"name": r[0], "protein": float(r[1])} for r in prot_rows]

        cur.close()
        return jsonify({
            "success": True,
            "summary": summary,
            "top_calories": top_calories,
            "top_protein": top_protein
        }), 200
    except Exception as e:
        print(f"Error getting big data analytics: {e}")
        return jsonify({"success": False, "message": str(e)}), 500

# =========================
# RUN
# =========================
import os

if __name__ == '__main__':
    # Membaca port default dari server hosting, jika tidak ada baru gunakan 5000
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False)