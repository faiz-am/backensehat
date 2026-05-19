from flask import Flask, jsonify, request
from flask_mysqldb import MySQL
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
import os
from dotenv import load_dotenv
from flask_jwt_extended import (
    JWTManager,
    create_access_token,
    jwt_required,
    get_jwt_identity
)

app = Flask(__name__)
CORS(app)

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

# =====================================================
# REGISTER API (TETAP)
# =====================================================

@app.route('/api/register', methods=['POST'])
def register():

    data = request.get_json()

    username = data['username']
    password = generate_password_hash(data['password'])

    cur = mysql.connection.cursor()

    cur.execute(
        "SELECT * FROM users WHERE username=%s",
        (username,)
    )

    user = cur.fetchone()

    if user:

        cur.close()

        return jsonify({
            "success": False,
            "message": "Username sudah digunakan"
        }), 400

    cur.execute(
        "INSERT INTO users(username, password) VALUES(%s, %s)",
        (username, password)
    )

    mysql.connection.commit()
    cur.close()

    return jsonify({
        "success": True,
        "message": "Register berhasil"
    })


# =====================================================
# LOGIN API (PAKAI JWT)
# =====================================================

@app.route('/api/login', methods=['POST'])
def login():

    data = request.get_json()

    username = data['username']
    password = data['password']

    cur = mysql.connection.cursor()

    cur.execute(
        "SELECT * FROM users WHERE username=%s",
        (username,)
    )

    user = cur.fetchone()
    cur.close()

    if user and check_password_hash(user[2], password):

        token = create_access_token(identity=username)

        return jsonify({
            "success": True,
            "token": token
        })

    return jsonify({
        "success": False,
        "message": "Login gagal"
    }), 401


# =====================================================
# PROTECTED API (CONTOH KEAMANAN JWT)
# =====================================================

@app.route('/api/users', methods=['GET'])
@jwt_required()
def get_users():

    current_user = get_jwt_identity()

    cur = mysql.connection.cursor()

    cur.execute("SELECT id, username FROM users")

    rows = cur.fetchall()
    cur.close()

    users = []

    for row in rows:

        users.append({
            "id": row[0],
            "username": row[1]
        })

    return jsonify({
        "logged_in_as": current_user,
        "users": users
    })

# =====================================================
# PUBLIC TIPS (TANPA JWT)
# =====================================================
@app.route('/api/tips', methods=['GET'])
def get_tips():

    cur = mysql.connection.cursor()

    cur.execute("SELECT id, title, description, icon FROM tips")

    rows = cur.fetchall()
    cur.close()

    tips = []

    for row in rows:
        tips.append({
            "id": row[0],
            "title": row[1],
            "description": row[2],
            "icon": row[3]
        })

    return jsonify(tips)

# =====================================================
# RUN
# =====================================================

if __name__ == '__main__':

    app.run(
        host='0.0.0.0',
        port=5000,
        debug=True
    )