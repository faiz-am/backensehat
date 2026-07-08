import os
import MySQLdb
from dotenv import load_dotenv

def main():
    # Load .env variables
    backend_dir = os.path.dirname(os.path.abspath(__file__))
    dotenv_path = os.path.join(backend_dir, ".env")
    load_dotenv(dotenv_path)

    host = os.getenv("MYSQL_HOST", "localhost")
    user = os.getenv("MYSQL_USER", "root")
    password = os.getenv("MYSQL_PASSWORD", "")
    default_db = os.getenv("MYSQL_DB", "sehat_app")

    print(f"Menghubungkan ke MySQL host={host}, user={user}...")

    try:
        # Hubungkan ke MySQL Server
        conn = MySQLdb.connect(
            host=host,
            user=user,
            password=password
        )
        cur = conn.cursor()

        # Daftar database yang akan dimigrasi (default db, sehat_app, dan kitasehat_app)
        dbs_to_migrate = list(set([default_db, "sehat_app", "kitasehat_app"]))

        for db_name in dbs_to_migrate:
            try:
                # Periksa apakah database ada
                cur.execute(f"SHOW DATABASES LIKE '{db_name}'")
                if not cur.fetchone():
                    print(f"Database '{db_name}' tidak ditemukan, melewati...")
                    continue

                cur.execute(f"USE `{db_name}`")
                print(f"\nMemproses database: {db_name}")

                # 1. Cek & Tambah Kolom 'username'
                cur.execute("SHOW COLUMNS FROM riwayat_gizis LIKE 'username'")
                if not cur.fetchone():
                    print(f" -> Menambahkan kolom 'username' ke tabel 'riwayat_gizis'...")
                    cur.execute("ALTER TABLE riwayat_gizis ADD COLUMN username VARCHAR(100) DEFAULT NULL")
                else:
                    print(" -> Kolom 'username' sudah ada.")

                # 2. Cek & Tambah Kolom 'skor'
                cur.execute("SHOW COLUMNS FROM riwayat_gizis LIKE 'skor'")
                if not cur.fetchone():
                    print(f" -> Menambahkan kolom 'skor' ke tabel 'riwayat_gizis'...")
                    cur.execute("ALTER TABLE riwayat_gizis ADD COLUMN skor INT DEFAULT NULL")
                else:
                    print(" -> Kolom 'skor' sudah ada.")

                # 3. Cek & Tambah Kolom 'foto_pagi'
                cur.execute("SHOW COLUMNS FROM riwayat_gizis LIKE 'foto_pagi'")
                if not cur.fetchone():
                    print(f" -> Menambahkan kolom 'foto_pagi' ke tabel 'riwayat_gizis'...")
                    cur.execute("ALTER TABLE riwayat_gizis ADD COLUMN foto_pagi LONGTEXT DEFAULT NULL")
                else:
                    print(" -> Kolom 'foto_pagi' sudah ada.")

                # 4. Cek & Tambah Kolom 'foto_siang'
                cur.execute("SHOW COLUMNS FROM riwayat_gizis LIKE 'foto_siang'")
                if not cur.fetchone():
                    print(f" -> Menambahkan kolom 'foto_siang' ke tabel 'riwayat_gizis'...")
                    cur.execute("ALTER TABLE riwayat_gizis ADD COLUMN foto_siang LONGTEXT DEFAULT NULL")
                else:
                    print(" -> Kolom 'foto_siang' sudah ada.")

                # 5. Cek & Tambah Kolom 'foto_malam'
                cur.execute("SHOW COLUMNS FROM riwayat_gizis LIKE 'foto_malam'")
                if not cur.fetchone():
                    print(f" -> Menambahkan kolom 'foto_malam' ke tabel 'riwayat_gizis'...")
                    cur.execute("ALTER TABLE riwayat_gizis ADD COLUMN foto_malam LONGTEXT DEFAULT NULL")
                else:
                    print(" -> Kolom 'foto_malam' sudah ada.")

                # 6. Cek & Tambah Kolom 'skor' ke tabel 'users'
                cur.execute("SHOW COLUMNS FROM users LIKE 'skor'")
                if not cur.fetchone():
                    print(f" -> Menambahkan kolom 'skor' ke tabel 'users'...")
                    cur.execute("ALTER TABLE users ADD COLUMN skor INT DEFAULT NULL")
                else:
                    print(" -> Kolom 'skor' sudah ada di tabel 'users'.")

                conn.commit()
                print(f"Sukses memigrasi database '{db_name}'!")
            except Exception as db_err:
                print(f"Gagal memproses database '{db_name}': {db_err}")

        cur.close()
        conn.close()
        print("\nMigrasi selesai!")
    except Exception as e:
        print(f"Koneksi MySQL gagal: {e}")

if __name__ == "__main__":
    main()
