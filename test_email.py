import os
from dotenv import load_dotenv

load_dotenv()

from flask import Flask
from flask_mail import Mail, Message

app = Flask(__name__)
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USE_SSL'] = True

username = os.getenv('MAIL_USERNAME')
password = os.getenv('MAIL_PASSWORD')
print(f'USERNAME: {username}')
print(f'PASSWORD ada: {bool(password)}')

mail = Mail(app)
with app.app_context():
    try:
        msg = Message(
            'TEST OTP - Sehat App',
            sender=username,
            recipients=[username]
        )
        msg.html = '<h2 style="color:#2196F3;">Kode OTP: <b>123456</b></h2><p>Ini adalah email test dari Sehat App.</p>'
        mail.send(msg)
        print('SUCCESS: Email berhasil terkirim!')
    except Exception as e:
        print(f'ERROR: {e}')
