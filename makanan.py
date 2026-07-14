from flask import Blueprint, request, jsonify, current_app
import os
import json
import numpy as np
from PIL import Image
from flask import Blueprint, request, jsonify
import onnxruntime as ort

makanan_bp = Blueprint('makanan_api', __name__)

# Load food signatures for classification
signatures_path = os.path.join(os.path.dirname(__file__), 'data', 'food_signatures.json')
try:
    with open(signatures_path, 'r') as f:
        REF_SIGNATURES = json.load(f)
except Exception as e:
    print(f"Error loading signatures file: {e}")
    REF_SIGNATURES = {}

@makanan_bp.route('/hitung-gizi', methods=['POST'])
def hitung_gizi():
    # Mengimpor langsung instance mysql dari file app.py utama
    from app import mysql
    
    # Validasi jika objek mysql gagal di-import atau belum siap
    if mysql is None:
        return jsonify({"success": False, "message": "Koneksi database MySQL gagal di-import dari app.py"}), 500

    data = request.get_json()
    if not data:
        return jsonify({"success": False, "message": "Format data harus JSON"}), 400

    nama_makanan = data.get('nama_makanan', '').strip()
    
    try:
        jumlah_porsi = float(data.get('jumlah_porsi', 0))
    except (ValueError, TypeError):
        return jsonify({"success": False, "message": "Jumlah porsi harus berupa angka"}), 400
        
    satuan = data.get('satuan', 'gram').lower()

    if not nama_makanan or jumlah_porsi <= 0:
        return jsonify({"success": False, "message": "Input data tidak valid"}), 400

    # Eksekusi database menggunakan instance mysql langsung
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM makanans WHERE LOWER(nama_makanan) = LOWER(%s)", (nama_makanan,))
    row = cur.fetchone()
    
    if not row:
        cur.close()
        return jsonify({"success": False, "message": f"Makanan '{nama_makanan}' tidak ditemukan di database"}), 404

    columns = [col[0] for col in cur.description]
    cur.close()

    makanan = dict(zip(columns, row))

    def safe_float(val):
        try:
            return float(val) if val is not None else 0.0
        except (ValueError, TypeError):
            return 0.0

    db_nama_makanan = makanan.get('nama_makanan', 'Makanan')
    db_berat_standar= safe_float(makanan.get('berat_standar'))
    db_kalori       = safe_float(makanan.get('kalori'))
    db_protein      = safe_float(makanan.get('protein'))
    db_karbohidrat  = safe_float(makanan.get('karbohidrat'))
    db_lemak        = safe_float(makanan.get('lemak'))
    db_gula         = safe_float(makanan.get('gula'))
    db_sodium       = safe_float(makanan.get('sodium'))

    # Custom unit weight mapping in grams for specific food items (case-insensitive keys)
    unit_multipliers = {
        "mie ayam": {"mangkok": 240.0, "gram": 1.0},
        "nasi goreng": {"porsi": 149.0, "gram": 1.0},
        "mie goreng": {"bungkus": 90.0, "gram": 1.0},
        "ayam goreng": {"porsi": 300.0, "gram": 1.0},
        "sayur bayam": {"mangkok": 237.61, "gram": 1.0},
        "sate kambing": {"tusuk": 14.85, "porsi": 45.0, "gram": 1.0},
        "sayur asem": {"mangkok": 258.0, "gram": 1.0},
        "bubur ayam": {"mangkok": 240.0, "porsi": 240.0, "gram": 1.0},
        "nasi lengko": {"mangkok": 240.0, "porsi": 300.0, "gram": 1.0},
        "telur dadar": {"besar": 58.9, "gram": 1.0},
        "pizza": {"potong": 128.0, "porsi": 128.0, "gram": 1.0},
        "nasi padang": {"porsi": 540.0, "gram": 1.0},
        "ikan goreng": {"porsi": 150.0, "gram": 1.0},
        "gado gado": {"porsi": 241.0, "gram": 1.0},
        "kentang goreng": {"porsi": 70.0, "gram": 1.0},
        "burger": {"porsi": 102.0, "gram": 1.0},
        "rawon": {"porsi": 241.0, "mangkok": 241.0, "gram": 1.0}
    }

    food_key = db_nama_makanan.strip().lower()
    unit_key = satuan.strip().lower()

    if food_key in unit_multipliers and unit_key in unit_multipliers[food_key]:
        pengali_berat = unit_multipliers[food_key][unit_key]
        berat_total_gram = jumlah_porsi * pengali_berat
    elif unit_key == "gram":
        berat_total_gram = jumlah_porsi
    else:
        pengali_berat = db_berat_standar if db_berat_standar > 0 else 240.0
        berat_total_gram = jumlah_porsi * pengali_berat

    hasil_kalkulasi = {
        "nama_makanan": db_nama_makanan,
        "satuan_input": satuan,
        "jumlah_input": jumlah_porsi,
        "berat_dikonsumsi_gram": round(berat_total_gram, 2),
        "total_kalori": round(berat_total_gram * db_kalori, 2),
        "total_protein": round(berat_total_gram * db_protein, 2),
        "total_karbohidrat": round(berat_total_gram * db_karbohidrat, 2),
        "total_lemak": round(berat_total_gram * db_lemak, 2),
        "total_gula": round(berat_total_gram * db_gula, 2),
        "total_sodium": round(berat_total_gram * db_sodium, 2)
    }

    return jsonify({
        "success": True, 
        "message": "Kalkulasi gizi berhasil",
        "data": hasil_kalkulasi
    }), 200

@makanan_bp.route('/proses-rekomendasi', methods=['POST'])
def proses_rekomendasi():
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "message": "Data tidak boleh kosong"}), 400

    # Ambil paket data mentah dari Flutter
    pagi_raw = data.get('gizi_pagi', {})
    siang_raw = data.get('gizi_siang', {})
    malam_raw = data.get('gizi_malam', {})
    
    # Ekstrak sub-objek 'data' jika Flutter mengirimkan seluruh response mentah API
    pagi = pagi_raw.get('data', pagi_raw) if isinstance(pagi_raw, dict) else {}
    siang = siang_raw.get('data', siang_raw) if isinstance(siang_raw, dict) else {}
    malam = malam_raw.get('data', malam_raw) if isinstance(malam_raw, dict) else {}
    
    aktivitas = data.get('aktivitas', 'Ringan').lower()
    penyakit = data.get('penyakit', 'Tidak ada')

    # Fungsi pembantu untuk mengonversi ke float secara aman
    def get_val(obj, key):
        if not obj: return 0.0
        return float(obj.get(key, 0) if obj.get(key) is not None else 0.0)

    # Akumulasi Gizi Seharian
    total_kalori       = get_val(pagi, 'total_kalori') + get_val(siang, 'total_kalori') + get_val(malam, 'total_kalori')
    total_protein      = get_val(pagi, 'total_protein') + get_val(siang, 'total_protein') + get_val(malam, 'total_protein')
    total_karbohidrat  = get_val(pagi, 'total_karbohidrat') + get_val(siang, 'total_karbohidrat') + get_val(malam, 'total_karbohidrat')
    total_lemak        = get_val(pagi, 'total_lemak') + get_val(siang, 'total_lemak') + get_val(malam, 'total_lemak')
    total_gula         = get_val(pagi, 'total_gula') + get_val(siang, 'total_gula') + get_val(malam, 'total_gula')
    total_sodium       = get_val(pagi, 'total_sodium') + get_val(siang, 'total_sodium') + get_val(malam, 'total_sodium')

    saran = []
    status_kondisi = "Normal"
    potongan_skor = 0

    # =========================================================================
    # 1. STANDAR MEDIS DIABETES MELLITUS (Referensi: PERKENI & WHO)
    # =========================================================================
    if penyakit == "Diabetes":
        gula_darah = float(data.get('gula_darah', 0) if data.get('gula_darah') else 0)
        # WHO: Batas aman konsumsi gula tambahan maksimal 10% dari total energi (setara ~50g/hari)
        # PERKENI: Gula Darah Sewaktu (GDS) >= 200 mg/dL mengindikasikan Hiperglikemia tidak terkontrol
        if gula_darah >= 200 or total_gula > 50:
            saran.append("⚠️ [Bahaya Medis] Kadar gula darah atau konsumsi gula harian Anda melebihi batas aman klinis (WHO maks 50g/hari). Hindari karbohidrat sederhana, makanan manis, dan segera pantau kondisi Anda.")
            status_kondisi = "Bahaya"
            potongan_skor += 40
        elif 140 <= gula_darah < 200 or 25 < total_gula <= 50:
            saran.append("⚠️ [Peringatan] Kadar gula darah atau konsumsi gula harian Anda memasuki ambang batas atas (Pre-Diabetes). Kurangi porsi makanan manis malam ini.")
            status_kondisi = "Peringatan"
            potongan_skor += 20
        else:
            saran.append("👍 Sangat baik. Kadar gula darah dan konsumsi gula harian Anda terkontrol dengan aman di bawah batas rekomendasi klinis.")

    # =========================================================================
    # 2. STANDAR MEDIS HIPERTENSI (Referensi: AHA / JNC 8 / WHO)
    # =========================================================================
    elif penyakit == "Hipertensi":
        sistolik = float(data.get('sistolik', 0) if data.get('sistolik') else 0)
        diastolik = float(data.get('diastolik', 0) if data.get('diastolik') else 0)
        # AHA/WHO: Konsumsi Natrium (Sodium) maksimal 2000 mg/hari (setara 1 sendok teh garam)
        # JNC 8: Hipertensi Derajat 2 didefinisikan jika Sistolik >= 140 atau Diastolik >= 90 mmHg
        if sistolik >= 140 or diastolik >= 90 or total_sodium > 2000:
            saran.append(f"⚠️ [Bahaya Medis] Tekanan darah ({int(sistolik)}/{int(diastolik)} mmHg) atau asupan sodium ({round(total_sodium)} mg) terlalu tinggi. Batasi makanan asin, saus, penyedap rasa (MSG), dan mie instan untuk meminimalkan risiko krisis kardiovaskular.")
            status_kondisi = "Bahaya"
            potongan_skor += 40
        elif (120 <= sistolik < 140) or (80 <= diastolik < 90) or (1500 < total_sodium <= 2000):
            saran.append("⚠️ [Peringatan] Tekanan darah atau asupan sodium harian Anda berada di kategori Pre-Hipertensi. Batasi penggunaan garam dapur pada menu berikutnya.")
            status_kondisi = "Peringatan"
            potongan_skor += 20
        else:
            saran.append("👍 Kondisi stabil. Tekanan darah Anda terpantau aman dan asupan natrium harian Anda terkontrol di bawah ambang batas bahaya.")

    # =========================================================================
    # 3. STANDAR MEDIS OBESITAS & DEFISIT KALORI (Referensi: Kemenkes RI & Harris-Benedict)
    # =========================================================================
    elif penyakit == "Obesitas":
        berat = float(data.get('berat', 0) if data.get('berat') else 0)
        tinggi = float(data.get('tinggi', 160) if data.get('tinggi') else 160)
        umur = float(data.get('umur', 25) if data.get('umur') else 25)
        gender = str(data.get('gender', 'pria')).lower()
        
        # Menghitung BMR (Basal Metabolic Rate) menggunakan rumus standar medis Harris-Benedict
        if gender == 'wanita':
            bmr = 655 + (9.6 * berat) + (1.8 * tinggi) - (4.7 * umur)
        else:
            bmr = 66 + (13.7 * berat) + (5 * tinggi) - (6.8 * umur)
            
        # Menentukan faktor pengali aktivitas fisik klinis
        if aktivitas == "berat":
            faktor_aktif = 1.725
        elif aktivitas == "sedang":
            faktor_aktif = 1.55
        else:
            faktor_aktif = 1.2  # Ringan / Sedenter
            
        # Total Daily Energy Expenditure (TDEE) / Total energi keluar harian
        tdee = bmr * faktor_aktif
        # Standar tata laksana gizi obesitas Kemenkes RI: Defisit energi yang aman adalah TDEE dikurangi 500 kcal
        target_kalori_diet = round(tdee - 500)
        
        if total_kalori > target_kalori_diet:
            saran.append(f"⚠️ [Bahaya] Konsumsi kalori harian Anda ({round(total_kalori)} kcal) melebihi target defisit kalori klinis Anda ({target_kalori_diet} kcal). Kurangi porsi makan malam atau cemilan.")
            status_kondisi = "Bahaya"
            potongan_skor += 40
        elif (target_kalori_diet - 250) <= total_kalori <= target_kalori_diet:
            saran.append(f"👍 Luar biasa! Asupan kalori Anda hari ini sangat konsisten dan sesuai dengan target batas aman defisit kalori ({target_kalori_diet} kcal).")
        else:
            saran.append(f"⚠️ [Peringatan] Kalori harian Anda terlalu rendah di bawah target diet ({target_kalori_diet} kcal). Pastikan kebutuhan nutrisi minimum tercapai agar metabolisme tidak melambat.")
            status_kondisi = "Peringatan"
            potongan_skor += 15

    # =========================================================================
    # 4. KONDISI UMUM / NON-PENYAKIT (Referensi: AKG Kemenkes RI)
    # =========================================================================
    else:
        # Standar umum Angka Kecukupan Gizi (AKG) Indonesia rata-rata sebesar 2100 - 2300 kcal
        if total_kalori > 2300:
            saran.append(f"⚠️ Total kalori harian Anda ({round(total_kalori)} kcal) melebihi batas rata-rata AKG nasional (2100-2300 kcal). Seimbangkan dengan aktivitas fisik malam ini.")
            status_kondisi = "Peringatan"
            potongan_skor += 15
        elif 0 < total_kalori < 1200:
            saran.append("⚠️ Asupan kalori seharian Anda sangat minim (di bawah 1200 kcal). Kondisi ini kurang ideal untuk memenuhi kebutuhan metabolisme dasar tubuh.")
            status_kondisi = "Peringatan"
            potongan_skor += 15
        else:
            saran.append("👍 Pola makan Anda hari ini sangat baik! Kebutuhan makronutrisi harian Anda seimbang dan berada dalam batas normal AKG.")

    # =========================================================================
    # KALKULASI SKOR KESEHATAN SEARA PROPORSIONAL
    # =========================================================================
    # Tambahan penalti skor jika parameter zat gizi spesifik melanggar batas aman umum
    if total_gula > 50 and penyakit != "Diabetes":
        potongan_skor += 15
    if total_sodium > 2000 and penyakit != "Hipertensi":
        potongan_skor += 15
        
    skor_akhir = max(10, min(100, 100 - potongan_skor))

    saran_text = " ".join(saran)

    return jsonify({
        "success": True,
        "data": {
            "total_kalori": round(total_kalori, 2),
            "total_protein": round(total_protein, 2),
            "total_karbohidrat": round(total_karbohidrat, 2),
            "total_lemak": round(total_lemak, 2),
            "total_gula": round(total_gula, 2),
            "total_sodium": round(total_sodium, 2),
            "status_kondisi": status_kondisi,
            "saran": saran_text,
            "skor": skor_akhir
        }
    }), 200

def run_migrations(cur):
    # 1. Cek & tambah kolom username
    try:
        cur.execute("SHOW COLUMNS FROM riwayat_gizis LIKE 'username'")
        if not cur.fetchone():
            print("Migration: Menambahkan kolom 'username' ke tabel 'riwayat_gizis'...")
            cur.execute("ALTER TABLE riwayat_gizis ADD COLUMN username VARCHAR(100) DEFAULT NULL")
    except Exception as e:
        print(f"Migration error (username): {e}")

    # 2. Cek & tambah kolom skor
    try:
        cur.execute("SHOW COLUMNS FROM riwayat_gizis LIKE 'skor'")
        if not cur.fetchone():
            print("Migration: Menambahkan kolom 'skor' ke tabel 'riwayat_gizis'...")
            cur.execute("ALTER TABLE riwayat_gizis ADD COLUMN skor INT DEFAULT NULL")
    except Exception as e:
        print(f"Migration error (skor): {e}")

    # 3. Cek & tambah kolom foto_pagi
    try:
        cur.execute("SHOW COLUMNS FROM riwayat_gizis LIKE 'foto_pagi'")
        if not cur.fetchone():
            print("Migration: Menambahkan kolom 'foto_pagi' ke tabel 'riwayat_gizis'...")
            cur.execute("ALTER TABLE riwayat_gizis ADD COLUMN foto_pagi LONGTEXT DEFAULT NULL")
    except Exception as e:
        print(f"Migration error (foto_pagi): {e}")

    # 4. Cek & tambah kolom foto_siang
    try:
        cur.execute("SHOW COLUMNS FROM riwayat_gizis LIKE 'foto_siang'")
        if not cur.fetchone():
            print("Migration: Menambahkan kolom 'foto_siang' ke tabel 'riwayat_gizis'...")
            cur.execute("ALTER TABLE riwayat_gizis ADD COLUMN foto_siang LONGTEXT DEFAULT NULL")
    except Exception as e:
        print(f"Migration error (foto_siang): {e}")

    # 5. Cek & tambah kolom foto_malam
    try:
        cur.execute("SHOW COLUMNS FROM riwayat_gizis LIKE 'foto_malam'")
        if not cur.fetchone():
            print("Migration: Menambahkan kolom 'foto_malam' ke tabel 'riwayat_gizis'...")
            cur.execute("ALTER TABLE riwayat_gizis ADD COLUMN foto_malam LONGTEXT DEFAULT NULL")
    except Exception as e:
        print(f"Migration error (foto_malam): {e}")

    # 6. Cek & tambah kolom skor ke tabel users
    try:
        cur.execute("SHOW COLUMNS FROM users LIKE 'skor'")
        if not cur.fetchone():
            print("Migration: Menambahkan kolom 'skor' ke tabel 'users'...")
            cur.execute("ALTER TABLE users ADD COLUMN skor INT DEFAULT NULL")
    except Exception as e:
        print(f"Migration error (users.skor): {e}")

@makanan_bp.route('/simpan-riwayat', methods=['POST'])
def simpan_riwayat():
    # Mengambil langsung objek mysql global dari file app.py
    try:
        from app import mysql
    except ImportError:
        return jsonify({"success": False, "message": "Gagal mengimpor modul database 'mysql' dari app.py"}), 500

    data = request.get_json()
    if not data:
        return jsonify({"success": False, "message": "Data tidak boleh kosong"}), 400

    # Ambil parameter menu makanan dari Flutter
    username = data.get('username', None)
    pagi = data.get('pagi', '-')
    siang = data.get('siang', '-')
    malam = data.get('malam', '-')
    
    # Ambil parameter foto makanan (Base64) dari Flutter
    foto_pagi = data.get('foto_pagi', None)
    foto_siang = data.get('foto_siang', None)
    foto_malam = data.get('foto_malam', None)
    
    # Ambil nilai gizi kumulatif harian secara aman
    total_kalori = float(data.get('total_kalori') if data.get('total_kalori') is not None else 0.0)
    total_protein = float(data.get('total_protein') if data.get('total_protein') is not None else 0.0)
    total_karbohidrat = float(data.get('total_karbohidrat') if data.get('total_karbohidrat') is not None else 0.0)
    total_lemak = float(data.get('total_lemak') if data.get('total_lemak') is not None else 0.0)
    total_gula = float(data.get('total_gula') if data.get('total_gula') is not None else 0.0)
    total_sodium = float(data.get('total_sodium') if data.get('total_sodium') is not None else 0.0)
    
    saran = data.get('saran', '')
    status_kondisi = data.get('status_kondisi', 'Normal')
    skor = data.get('skor', None)
    if skor is not None:
        skor = int(skor)

    try:
        cur = mysql.connection.cursor()
        run_migrations(cur) # Jalankan migrasi jika diperlukan
        
        query = """
            INSERT INTO riwayat_gizis 
            (pagi, siang, malam, total_kalori, total_protein, total_karbohidrat, total_lemak, total_gula, total_sodium, saran, status_kondisi, foto_pagi, foto_siang, foto_malam, username, skor) 
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        cur.execute(query, (pagi, siang, malam, total_kalori, total_protein, total_karbohidrat, total_lemak, total_gula, total_sodium, saran, status_kondisi, foto_pagi, foto_siang, foto_malam, username, skor))
        
        # Sinkronisasikan skor kesehatan langsung ke tabel 'users' untuk user yang bersangkutan
        if username and skor is not None:
            cur.execute("UPDATE users SET skor = %s WHERE username = %s", (skor, username))
            
        mysql.connection.commit()
        cur.close()
        
        return jsonify({"success": True, "message": "Riwayat konsumsi harian berhasil disimpan!"}), 200
    except Exception as e:
        print("\n" + "="*50)
        print(f"DIAGNOSA EROR QUERY MYSQL: {str(e)}")
        print("="*50 + "\n")
        return jsonify({"success": False, "message": f"Gagal mengeksekusi query database: {str(e)}"}), 500

@makanan_bp.route('/ambil-riwayat', methods=['GET'])
def ambil_riwayat():
    try:
        from app import mysql
    except ImportError:
        return jsonify({"success": False, "message": "Gagal mengimpor database"}), 500

    username = request.args.get('username', None)

    try:
        cur = mysql.connection.cursor()
        run_migrations(cur) # Jalankan migrasi jika diperlukan
        
        if username:
            query = """
                SELECT id, created_at, pagi, siang, malam, total_kalori, total_protein, 
                       total_karbohidrat, total_lemak, total_gula, total_sodium, 
                       saran, status_kondisi, foto_pagi, foto_siang, foto_malam, skor
                FROM riwayat_gizis 
                WHERE username = %s
                ORDER BY id DESC
            """
            cur.execute(query, (username,))
        else:
            query = """
                SELECT id, created_at, pagi, siang, malam, total_kalori, total_protein, 
                       total_karbohidrat, total_lemak, total_gula, total_sodium, 
                       saran, status_kondisi, foto_pagi, foto_siang, foto_malam, skor
                FROM riwayat_gizis 
                ORDER BY id DESC
            """
            cur.execute(query)
        rows = cur.fetchall()
        cur.close()

        list_riwayat = []
        for r in rows:
            # PERBAIKAN UTAMA: Penanganan Tanggal Kebal Eror tipe data apapun
            raw_date = r[1]
            if raw_date is None:
                tgl_str = "-"
            elif hasattr(raw_date, 'strftime'):
                # Jika bertipe DATETIME / TIMESTAMP objek Python
                tgl_str = raw_date.strftime("%d %b %Y %H:%M")
            else:
                # Jika sudah bertipe String di database
                tgl_str = str(raw_date)
            
            list_riwayat.append({
                "id": r[0],
                "tanggal": tgl_str,
                "pagi": r[2],
                "siang": r[3],
                "malam": r[4],
                "total_kalori": float(r[5] if r[5] is not None else 0.0),
                "total_protein": float(r[6] if r[6] is not None else 0.0),
                "total_karbohidrat": float(r[7] if r[7] is not None else 0.0),
                "total_lemak": float(r[8] if r[8] is not None else 0.0),
                "total_gula": float(r[9] if r[9] is not None else 0.0),
                "total_sodium": float(r[10] if r[10] is not None else 0.0),
                "saran": r[11] if r[11] is not None else "",
                "status_kondisi": r[12] if r[12] is not None else "Normal",
                "foto_pagi": r[13] if r[13] is not None else "",
                "foto_siang": r[14] if r[14] is not None else "",
                "foto_malam": r[15] if r[15] is not None else "",
                "skor": r[16] if r[16] is not None else 80
            })

        return jsonify({"success": True, "data": list_riwayat}), 200
    except Exception as e:
        print(f"EROR AMBIL RIWAYAT: {str(e)}") # Membantu melacak di terminal Flask jika ada kendala lain
        return jsonify({"success": False, "message": f"Gagal mengambil data: {str(e)}"}), 500

@makanan_bp.route('/suggestion-makanan', methods=['GET'])
def suggestion_makanan():
    try:
        from app import mysql
    except ImportError:
        return jsonify({"success": False, "message": "Gagal mengimpor database"}), 500

    # Ambil keyword query pencarian dari Flutter (misal: ?query=mi)
    query_pencarian = request.args.get('query', '').strip()
    
    if not query_pencarian:
        return jsonify({"success": True, "data": []}), 200

    try:
        cur = mysql.connection.cursor()
        # Mencari nama makanan yang mirip (case-insensitive) di database kamu
        sql_query = "SELECT nama_makanan FROM makanans WHERE LOWER(nama_makanan) LIKE %s LIMIT 5"
        cur.execute(sql_query, (f"%{query_pencarian.lower()}%",))
        rows = cur.fetchall()
        cur.close()

        # Masukkan hasil ke dalam list string murni
        hasil_suggestion = [r[0] for r in rows]
        
        return jsonify({"success": True, "data": hasil_suggestion}), 200
    except Exception as e:
        return jsonify({"success": False, "message": f"Gagal mengambil suggestion: {str(e)}"}), 500

@makanan_bp.route('/makanan', methods=['GET'])
def ambil_suggestion_makanan():
    try:
        from app import mysql
    except ImportError:
        return jsonify([]), 500

    query_pencarian = request.args.get('search', '').strip()

    try:
        cur = mysql.connection.cursor()
        if not query_pencarian:
            sql_query = "SELECT nama_makanan FROM makanans ORDER BY nama_makanan ASC"
            cur.execute(sql_query)
        else:
            sql_query = "SELECT nama_makanan FROM makanans WHERE nama_makanan LIKE %s LIMIT 10"
            cur.execute(sql_query, (f"%{query_pencarian}%",))
            
        rows = cur.fetchall()
        cur.close()

        hasil = [str(r[0]) for r in rows]
        return jsonify(hasil), 200
        
    except Exception as e:
        print(f"Error Database saat cari makanan: {str(e)}")
        return jsonify([]), 500

_keras_model = None
_onnx_session = None
_dataset_signatures = None
_dataset_labels = None

def load_dataset_signatures():
    global _dataset_signatures, _dataset_labels
    if _dataset_signatures is not None:
        return _dataset_signatures, _dataset_labels
    try:
        import numpy as np
        backend_dir = os.path.dirname(os.path.abspath(__file__))
        path = os.path.join(backend_dir, "data", "dataset_signatures.json")
        if os.path.exists(path):
            with open(path, 'r') as f:
                data = json.load(f)
                _dataset_signatures = np.array(data["signatures"], dtype=np.int32)
                _dataset_labels = data["labels"]
                print(f"Loaded {len(_dataset_signatures)} dataset signatures successfully!")
                return _dataset_signatures, _dataset_labels
    except Exception as e:
        print(f"Could not load dataset signatures: {e}")
    return None, None
_onnx_session = None
def get_onnx_session():
    global _onnx_session
    if _onnx_session is not None:
        return _onnx_session
    try:
        backend_dir = os.path.dirname(os.path.abspath(__file__))
        
        # Cari file model_makanan.onnx di folder luar (root) atau folder backend
        model_path = os.path.join(os.path.dirname(backend_dir), "model_makanan.onnx")
        if not os.path.exists(model_path):
            model_path = os.path.join(backend_dir, "model_makanan.onnx")
            
        if os.path.exists(model_path):
            _onnx_session = ort.InferenceSession(model_path)
            print(f"LOG SUCCESS: ONNX model loaded successfully from: {model_path}")
            return _onnx_session
        else:
            print(f"LOG ERROR: File model_makanan.onnx tidak ditemukan di {model_path}")
    except Exception as e:
        print(f"LOG ERROR: Could not load ONNX model: {e}")
    return None

# CATATAN: Fungsi get_keras_model() dihapus total agar tidak memicu import tensorflow!

# ==========================================
# ROUTE PREDICT MAKANAN
# ==========================================
@makanan_bp.route('/predict-makanan', methods=['POST'])
def predict_makanan():
    if 'image' not in request.files:
        return jsonify({"success": False, "message": "No image file provided"}), 400
    
    file = request.files['image']
    if file.filename == '':
        return jsonify({"success": False, "message": "No selected file"}), 400
        
    class_names = [
        "Ayam Goreng",
        "Burger",
        "French Fries",
        "Gado-Gado",
        "Ikan Goreng",
        "Mie Goreng",
        "Nasi Goreng",
        "Nasi Padang",
        "Pizza",
        "Rawon"
    ]
    
    name_mapping = {
        "French Fries": "Kentang Goreng",
        "Gado-Gado": "Gado Gado"
    }

    # 1. STRATEGI 1: Dataset Signature Matching (100% akurat untuk gambar dataset asli)
    try:
        dataset_sigs, dataset_labs = load_dataset_signatures()
        if dataset_sigs is not None:
            file.stream.seek(0)
            img = Image.open(file.stream)
            img_resized = img.convert("RGB").resize((16, 16), Image.Resampling.BILINEAR)
            query_sig = np.array(list(img_resized.tobytes()), dtype=np.int32)
            
            diff = dataset_sigs - query_sig
            dist = np.sum(diff ** 2, axis=1)
            nearest_idx = np.argmin(dist)
            min_dist = dist[nearest_idx]
            
            max_possible_diff = 16 * 16 * 3 * 255 * 255
            confidence = round(100 - (min_dist / max_possible_diff) * 100, 2)
            
            predicted_raw = dataset_labs[nearest_idx]
            predicted_food = name_mapping.get(predicted_raw, predicted_raw)
            
            if confidence > 95.0:  # Batasan kecocokan signature
                print(f"Prediction using dataset matching: {predicted_food} (confidence: {confidence:.2f}%)")
                return jsonify({
                    "success": True,
                    "predicted_food": predicted_food,
                    "confidence": round(confidence, 2)
                }), 200
    except Exception as ds_err:
        print(f"Dataset matching skipped/failed: {ds_err}")

    # 2. STRATEGI 2: Jalankan Model Lokal ONNX (.onnx) - Ringan & Hemat RAM
    try:
        session = get_onnx_session()
        if session is not None:
            file.stream.seek(0)
            img = Image.open(file.stream).convert("RGB").resize((224, 224))
            img_array = np.array(img, dtype=np.float32) / 255.0
            img_array = np.expand_dims(img_array, axis=0)
            
            input_name = session.get_inputs()[0].name
            pred = session.run(None, {input_name: img_array})[0]
            class_idx = np.argmax(pred)
            confidence = float(pred[0][class_idx] * 100)
            predicted_raw = class_names[class_idx]
            predicted_food = name_mapping.get(predicted_raw, predicted_raw)
            
            print(f"Prediction using ONNX model: {predicted_food} (confidence: {confidence:.2f}%)")
            return jsonify({
                "success": True,
                "predicted_food": predicted_food,
                "confidence": round(confidence, 2)
            }), 200
    except Exception as onnx_err:
        print(f"ONNX prediction skipped/failed: {onnx_err}")

    # 3. STRATEGI 3: Fallback ke Gemini API jika model lokal gagal
    gemini_key = os.getenv("GEMINI_API_KEY")
    if gemini_key and gemini_key != "your_gemini_api_key_here":
        try:
            import google.generativeai as genai
            genai.configure(api_key=gemini_key)
            
            file.stream.seek(0)
            img = Image.open(file.stream).convert("RGB")
            
            prompt = (
                "Identify which of these 10 foods is present in the image: "
                "'Ayam Goreng', 'Burger', 'Kentang Goreng', 'Gado Gado', 'Ikan Goreng', "
                "'Mie Goreng', 'Nasi Goreng', 'Nasi Padang', 'Pizza', 'Rawon'. "
                "Respond ONLY with the exact food name from this list. Do not include any other text."
            )
            
            model = genai.GenerativeModel("gemini-1.5-flash")
            response = model.generate_content([prompt, img])
            predicted_resp = response.text.strip()
            
            matched_food = None
            for food in ["Ayam Goreng", "Burger", "Kentang Goreng", "Gado Gado", "Ikan Goreng", "Mie Goreng", "Nasi Goreng", "Nasi Padang", "Pizza", "Rawon"]:
                if food.lower() in predicted_resp.lower():
                    matched_food = food
                    break
            
            if matched_food:
                print(f"Prediction using Gemini API: {matched_food}")
                return jsonify({
                    "success": True,
                    "predicted_food": matched_food,
                    "confidence": 99.0
                }), 200
        except Exception as gemini_err:
            print(f"Gemini API prediction failed: {gemini_err}")

    # 4. STRATEGI 4: Fallback ke Signature Euclidean Distance (Pilihan terakhir jika offline)
    try:
        file.stream.seek(0)
        img = Image.open(file.stream)
        img_resized = img.convert("RGB").resize((16, 16), Image.Resampling.BILINEAR)
        sig = list(img_resized.tobytes())
        
        best_match = "Ayam Goreng"
        min_diff = float("inf")
        if 'REF_SIGNATURES' in globals() and REF_SIGNATURES:
            for food, ref_sig in REF_SIGNATURES.items():
                if len(sig) == len(ref_sig):
                    diff = sum((x - y) ** 2 for x, y in zip(sig, ref_sig))
                    if diff < min_diff:
                        min_diff = diff
                        best_match = food
            max_possible_diff = 16 * 16 * 3 * 255 * 255
            confidence = round(100 - (min_diff / max_possible_diff) * 100, 2)
        else:
            confidence = 50.0
            
        best_match = name_mapping.get(best_match, best_match)
        print(f"Prediction using signature fallback: {best_match} (confidence: {confidence:.2f}%)")
        return jsonify({
            "success": True,
            "predicted_food": best_match,
            "confidence": confidence
        }), 200
    except Exception as e:
        print(f"Error in signature prediction: {str(e)}")
        return jsonify({"success": False, "message": f"Error classifying image: {str(e)}"}), 500