import os
import sys
import tensorflow as tf
import subprocess

keras_model_path = "model_makanan.keras"
temp_saved_model_dir = "temp_saved_model"
onnx_model_path = "model_makanan.onnx"

if not os.path.exists(keras_model_path):
    print(f"Error: File {keras_model_path} tidak ditemukan!")
else:
    try:
        print("1. Memuat model Keras...")
        model = tf.keras.models.load_model(keras_model_path, compile=False)
        
        print("2. Menyimpan sementara ke format SavedModel...")
        model.export(temp_saved_model_dir) 
        print("   SavedModel berhasil dibuat di folder:", temp_saved_model_dir)

        print("3. Mengonversi SavedModel ke ONNX via CLI...")
        # Menggunakan sys.executable agar tetap berada di dalam Virtual Environment (venv)
        cmd = [
            sys.executable, "-m", "tf2onnx.convert",
            "--saved-model", temp_saved_model_dir,
            "--output", onnx_model_path,
            "--opset", "15"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"\n🎉 SUKSES! File model baru kamu telah berhasil dibuat: {onnx_model_path}")
            
            # Hapus folder sementara agar foldermu tetap bersih
            import shutil
            if os.path.exists(temp_saved_model_dir):
                shutil.rmtree(temp_saved_model_dir)
                print("   Folder sementara dibersihkan.")
        else:
            print("\n❌ Gagal saat konversi ONNX:")
            print(result.stderr)

    except Exception as e:
        print(f"\n❌ Terjadi kesalahan saat proses: {e}")