from flask import Flask, jsonify, render_template, request, redirect, session
from flask_mysqldb import MySQL
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
import os
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

# Load .env
load_dotenv()

app = Flask(__name__)
CORS(app)

# =========================
# MAIL CONFIG
# =========================
app.config['MAIL_SERVER'] = os.getenv("MAIL_SERVER", 'smtp.gmail.com')
app.config['MAIL_PORT'] = int(os.getenv("MAIL_PORT", 465))
app.config['MAIL_USERNAME'] = os.getenv("MAIL_USERNAME")
app.config['MAIL_PASSWORD'] = os.getenv("MAIL_PASSWORD")
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USE_SSL'] = True
mail = Mail(app)

# =========================
# MYSQL CONFIG
# =========================
app.config['MYSQL_HOST'] = os.getenv("MYSQL_HOST")
app.config['MYSQL_USER'] = os.getenv("MYSQL_USER")
app.config['MYSQL_PASSWORD'] = os.getenv("MYSQL_PASSWORD")
app.config['MYSQL_DB'] = os.getenv("MYSQL_DB")

# =========================
# JWT CONFIG
# =========================
app.config['JWT_SECRET_KEY'] = os.getenv("JWT_SECRET_KEY")
jwt = JWTManager(app)

mysql = MySQL(app)

# =========================
# FIREBASE CONFIG
# =========================
try:
    cred = credentials.Certificate("firebase.json")
    firebase_admin.initialize_app(cred)
except Exception as e:
    print(f"Firebase error: {e}")

# =========================
# ROOT API
# =========================
@app.route('/', methods=['GET'])
def root():
    return jsonify({"message": "api aktif", "status": "running"}), 200

# =========================
# REGISTER API
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

    cur.execute("SELECT * FROM users WHERE username=%s", (username,))
    user = cur.fetchone()

    if user:
        cur.close()
        return jsonify({"success": False, "message": "Username sudah digunakan"}), 400

    otp = str(random.randint(100000, 999999))

    try:
        cur.execute(
            "INSERT INTO users(username, password, is_verified, otp) VALUES(%s,%s,%s,%s)",
            (username, password, 0, otp)
        )
        msg = Message(
            'Kode Verifikasi OTP - Sehat App',
            sender=app.config['MAIL_USERNAME'],
            recipients=[username]
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
        mail.send(msg)
        mysql.connection.commit()
    except Exception as e:
        mysql.connection.rollback()
        print(f"Error mengirim email OTP atau menyimpan user: {e}")
        return jsonify({"success": False, "message": f"Gagal mengirim email OTP: {str(e)}"}), 500
    finally:
        cur.close()

    return jsonify({"success": True, "message": "Register berhasil, silakan cek email Anda untuk kode OTP."})

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
# RUN
# =========================
if __name__ == '__main__':
    app.run(debug=True)