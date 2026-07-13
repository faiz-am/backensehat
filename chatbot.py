import re
import math
import collections

# Predefined Knowledge Base (Q&A Dataset) in Indonesian
KNOWLEDGE_BASE = [
    {
        "category": "makanan_sehat",
        "answer": (
            "Makanan paling sehat meliputi:\n"
            "1. 🥬 Sayuran Hijau (bayam, broccoli, kangkung) - kaya serat & zat besi.\n"
            "2. 🥑 Buah-buahan (alpukat, apel, beri) - kaya vitamin & antioksidan.\n"
            "3. 🍗 Protein Tanpa Lemak (dada ayam, ikan, tempe, tahu) - membangun jaringan otot.\n"
            "4. 🫘 Kacang-kacangan & Biji-bijian - sumber lemak sehat omega-3.\n"
            "5. 🌾 Karbohidrat Kompleks (nasi merah, oatmeal, ubi) - energi tahan lama."
        ),
        "questions": [
            "makanan sehat paling bagus apa saja",
            "apa saja makanan sehat",
            "rekomendasi makanan sehat",
            "makanan sehat untuk tubuh",
            "menu sehat gizi seimbang",
            "sayuran dan buah sehat",
            "bagaimana cara makan sehat",
            "daftar makanan bergizi",
            "makanan tinggi serat dan protein",
            "pilihan makanan sehat harian",
            "makanan sehat",
            "makanan bergizi",
            "menu sehat"
        ]
    },
    {
        "category": "tips_diet",
        "answer": (
            "Tips menurunkan berat badan secara sehat:\n"
            "1. 🥗 Lakukan defisit kalori ringan (kurangi 300-500 kalori harian).\n"
            "2. 🏃‍♂️ Tingkatkan aktivitas fisik / olahraga minimal 150 menit per minggu.\n"
            "3. 🥩 Penuhi kebutuhan protein agar kenyang lebih lama dan otot terjaga.\n"
            "4. 💧 Minum air putih sebelum makan.\n"
            "5. 😴 Tidur cukup 7-8 jam per hari, karena kurang tidur meningkatkan hormon lapar."
        ),
        "questions": [
            "bagaimana tips diet",
            "cara menurunkan berat badan",
            "tips mengecilkan perut buncit",
            "cara diet sehat dan cepat",
            "bagaimana cara diet aman",
            "rekomendasi diet menurunkan berat badan",
            "tips menurunkan berat badan alami",
            "cara kurus sehat",
            "cara kurangi berat badan",
            "program diet yang baik",
            "tips diet",
            "diet sehat",
            "turun berat badan"
        ]
    },
    {
        "category": "kontrol_gula",
        "answer": (
            "Cara mengontrol kadar gula darah:\n"
            "1. 🍚 Batasi karbohidrat sederhana (nasi putih berlebih, roti putih).\n"
            "2. 🍩 Hindari minuman manis, sirup, dan soda.\n"
            "3. 🥦 Perbanyak makanan tinggi serat (sayuran, kacang-kacangan).\n"
            "4. 🚶‍♂️ Lakukan jalan kaki 10-15 menit setelah makan.\n"
            "5. 📊 Pantau asupan gula harian Anda (maksimal 4 sendok makan atau 50 gram sehari)."
        ),
        "questions": [
            "cara mengontrol gula darah",
            "tips diet penderita diabetes",
            "bagaimana cara menurunkan kadar gula",
            "mencegah gula darah tinggi",
            "cara menghindari diabetes",
            "batasi makanan manis",
            "tips kontrol gula harian",
            "gula darah normal",
            "pantau asupan gula",
            "cara kurangi konsumsi manis",
            "kontrol gula",
            "kadar gula darah",
            "diabetes"
        ]
    },
    {
        "category": "batasi_garam",
        "answer": (
            "Cara membatasi konsumsi garam (natrium):\n"
            "1. 🍟 Kurangi makanan cepat saji, camilan asin, dan makanan kalengan.\n"
            "2. 🌿 Gunakan rempah alami (bawang, ketumbar, lemon) sebagai penyedap rasa pengganti garam.\n"
            "3. 🥫 Selalu baca label informasi nilai gizi (pilih produk rendah natrium).\n"
            "4. 🥤 Perbanyak minum air putih untuk membantu tubuh mengeluarkan kelebihan natrium.\n"
            "5. 🧂 Batasi garam meja maksimal 1 sendok teh (2000mg natrium) per hari."
        ),
        "questions": [
            "cara membatasi konsumsi garam",
            "tips menurunkan darah tinggi hipertensi",
            "mengurangi asupan natrium sodium",
            "garam maksimal harian berapa",
            "bahaya garam berlebih",
            "cara membatasi asin",
            "makanan tinggi garam natrium",
            "tensi darah tinggi apa solusinya",
            "cara mengontrol hipertensi",
            "batasi garam",
            "hipertensi",
            "darah tinggi",
            "kurangi garam"
        ]
    },
    {
        "category": "fitur_app",
        "answer": (
            "Fitur unggulan di aplikasi Sehat Kita:\n"
            "1. 🩺 Dashboard Pemantauan - memantau skor kesehatan, kalori harian, gula, dan garam.\n"
            "2. 📝 Pencatatan Gizi - fitur input makanan harian untuk pagi, siang, dan malam.\n"
            "3. 📊 Riwayat Gizi - grafik visualisasi riwayat kesehatan Anda.\n"
            "4. 💡 Tips Kesehatan - tips harian yang diperbarui langsung oleh admin.\n"
            "5. 💬 Chatbot AI - asisten kesehatan interaktif Anda."
        ),
        "questions": [
            "fitur apa saja di aplikasi ini",
            "apa kegunaan aplikasi sehat kita",
            "fitur unggulan sehat kita",
            "bagaimana cara menggunakan fitur aplikasi",
            "menu utama aplikasi sehat kita",
            "fitur pemantauan gizi",
            "apa saja yang ada di aplikasi ini",
            "fitur app",
            "fitur aplikasi",
            "menu aplikasi"
        ]
    },
    {
        "category": "hidrasi",
        "answer": (
            "Pentingnya hidrasi tubuh harian:\n"
            "1. 💧 Kebutuhan rata-rata orang dewasa adalah 8 gelas atau 2 liter sehari.\n"
            "2. 🏃‍♂️ Jika Anda berolahraga atau cuaca panas, tambahkan asupan air Anda.\n"
            "3. 🍋 Manfaat air putih: membuang racun, melancarkan pencernaan, menjaga elastisitas kulit, dan mencegah dehidrasi."
        ),
        "questions": [
            "berapa kebutuhan air harian",
            "tips minum air putih cukup",
            "pentingnya hidrasi tubuh",
            "berapa gelas air sehari",
            "cara mengatasi dehidrasi",
            "kebutuhan cairan tubuh harian",
            "minum air putih berapa liter",
            "kebutuhan air",
            "air putih harian",
            "dehidrasi"
        ]
    },
    {
        "category": "input_makanan",
        "answer": (
            "Cara mencatat/menginput makanan baru:\n"
            "1. ➕ Tekan tab 'Input' (ikon plus di bagian tengah navigasi bawah).\n"
            "2. Masukkan nama makanan (misal: 'Nasi Goreng').\n"
            "3. Tentukan waktu makan (Pagi, Siang, atau Malam).\n"
            "4. Isi jumlah kalori, protein, sodium (garam), dan gula yang Anda konsumsi.\n"
            "5. Tekan tombol 'Simpan' untuk mencatat ke database."
        ),
        "questions": [
            "cara input makanan baru",
            "cara mencatat makanan harian",
            "cara tambah menu makanan",
            "bagaimana cara mencatat kalori",
            "cara input gizi makanan",
            "pencatatan makanan di aplikasi",
            "input makanan",
            "tambah makanan",
            "catat kalori"
        ]
    },
    {
        "category": "riwayat_gizi",
        "answer": (
            "Untuk melihat riwayat perkembangan gizi Anda:\n"
            "1. 📊 Masuk ke menu 'Riwayat' (tab kedua dari bawah).\n"
            "2. Anda akan melihat daftar riwayat makan pagi, siang, malam beserta status kondisi kesehatan Anda (Normal, Kurang Gizi, atau Obesitas)."
        ),
        "questions": [
            "cara melihat riwayat gizi",
            "dimana melihat grafik perkembangan kesehatan",
            "riwayat kesehatan saya",
            "perkembangan gizi harian",
            "grafik kondisi kesehatan",
            "riwayat gizi",
            "grafik perkembangan"
        ]
    }
]

# Greetings and Gratitude Keywords
GREETING_KEYWORDS = ["halo", "hai", "pagi", "siang", "sore", "malam", "assalamualaikum", "permisi", "hi", "helo", "hello"]
GRATITUDE_KEYWORDS = ["terima kasih", "makasih", "thank you", "nuhun", "suwun", "syukur", "tengkyu", "thanks"]

# Indonesian Stop Words to filter out for higher precision Cosine Similarity
STOP_WORDS = {
    "yang", "dan", "di", "dari", "untuk", "dengan", "saya", "kamu", "anda", "ini", "itu", 
    "ada", "adalah", "bisa", "cara", "bagaimana", "apa", "saja", "ke", "buat", "ingin", 
    "mau", "atau", "sebagai", "apakah", "bagaimanakah", "kita", "kami", "sih", "lah", 
    "kah", "deh", "pun", "saya", "gua", "gw"
}

# Preprocessing: remove symbols, emojis, and lowercase
def clean_query(text):
    text = text.lower()
    # Remove emojis and non-alphanumeric chars (keep spaces and normal word characters)
    text = re.sub(r'[^\w\s]', ' ', text)
    # Remove extra spaces
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def tokenize(text):
    tokens = clean_query(text).split()
    # Filter out stop words
    return [t for t in tokens if t not in STOP_WORDS]

# Simple TF-IDF Vectorizer
class SimpleTFIDF:
    def __init__(self, corpus_documents):
        self.num_docs = len(corpus_documents)
        
        # Calculate Document Frequency (DF) for each term
        self.df = collections.defaultdict(int)
        for doc in corpus_documents:
            unique_terms = set(doc)
            for term in unique_terms:
                self.df[term] += 1
                
        # Calculate Inverse Document Frequency (IDF): log(1 + N / (1 + df))
        self.idf = {}
        for term, df_val in self.df.items():
            self.idf[term] = math.log(1.0 + (self.num_docs / (1.0 + df_val)))
            
    def get_tfidf_vector(self, tokens):
        tf = collections.defaultdict(int)
        for token in tokens:
            tf[token] += 1
            
        vector = {}
        for term, tf_val in tf.items():
            if term in self.idf:
                vector[term] = tf_val * self.idf[term]
        return vector

def cosine_similarity(vec1, vec2):
    dot_product = 0.0
    for term, val1 in vec1.items():
        if term in vec2:
            dot_product += val1 * vec2[term]
            
    mag1 = math.sqrt(sum(val ** 2 for val in vec1.values()))
    mag2 = math.sqrt(sum(val ** 2 for val in vec2.values()))
    
    if mag1 == 0.0 or mag2 == 0.0:
        return 0.0
        
    return dot_product / (mag1 * mag2)

# Build and train vectorizer on the predefined KNOWLEDGE_BASE
corpus = []
question_to_kb_map = [] # maps corpus index back to KNOWLEDGE_BASE category & answer

for kb_entry in KNOWLEDGE_BASE:
    for question in kb_entry["questions"]:
        tokens = tokenize(question)
        corpus.append(tokens)
        question_to_kb_map.append({
            "category": kb_entry["category"],
            "answer": kb_entry["answer"]
        })

# Instantiate vectorizer and pre-calculate vectors for all dataset questions
vectorizer = SimpleTFIDF(corpus)
database_vectors = [vectorizer.get_tfidf_vector(doc) for doc in corpus]

def get_chatbot_response(message):
    cleaned = clean_query(message)
    
    # ----------------------------------------------------
    # RULE-BASED MATCHING (HIGHEST PRIORITY)
    # ----------------------------------------------------
    
    # 1. Direct Suggestion Chips / Keywords Match
    if cleaned in ["makanan sehat", "makanan sehat 🥬"]:
        return KNOWLEDGE_BASE[0]["answer"]
    elif cleaned in ["tips diet", "tips diet 🏃‍♂️", "cara diet"]:
        return KNOWLEDGE_BASE[1]["answer"]
    elif cleaned in ["kontrol gula", "kontrol gula 🍚", "kadar gula"]:
        return KNOWLEDGE_BASE[2]["answer"]
    elif cleaned in ["batasi garam", "batasi garam 🧂", "kurangi garam"]:
        return KNOWLEDGE_BASE[3]["answer"]
    elif cleaned in ["fitur app", "fitur aplikasi", "fitur app 🩺"]:
        return KNOWLEDGE_BASE[4]["answer"]
    elif cleaned in ["air putih", "minum air", "hidrasi", "dehidrasi"]:
        return KNOWLEDGE_BASE[5]["answer"]
    elif cleaned in ["input makanan", "tambah makanan", "catat makanan"]:
        return KNOWLEDGE_BASE[6]["answer"]
    elif cleaned in ["riwayat gizi", "grafik gizi", "grafik kesehatan"]:
        return KNOWLEDGE_BASE[7]["answer"]
        
    # 2. Greetings Match
    words = cleaned.split()
    if any(greet in words for greet in GREETING_KEYWORDS):
        return "Halo! 👋 Saya adalah Asisten Kesehatan Sehat Kita. Ada yang bisa saya bantu hari ini tentang tips kesehatan atau pola makan sehat?"
        
    # 3. Gratitude Match
    if any(thanks in cleaned for thanks in GRATITUDE_KEYWORDS):
        return "Sama-sama! 😊 Senang bisa membantu Anda. Selalu jaga kesehatan dan pola makan seimbang ya!"

    # ----------------------------------------------------
    # COSINE SIMILARITY MATCHING
    # ----------------------------------------------------
    query_tokens = tokenize(message)
    query_vector = vectorizer.get_tfidf_vector(query_tokens)
    
    best_score = 0.0
    best_index = -1
    
    for idx, doc_vector in enumerate(database_vectors):
        score = cosine_similarity(query_vector, doc_vector)
        if score > best_score:
            best_score = score
            best_index = idx
            
    # Set matching threshold (0.25 is standard for TF-IDF on short queries)
    if best_score >= 0.25 and best_index != -1:
        return question_to_kb_map[best_index]["answer"]
        
    # ----------------------------------------------------
    # FALLBACK RESPONSE
    # ----------------------------------------------------
    return (
        "Maaf, saya kurang memahami pertanyaan Anda. 😅\n\n"
        "Coba tanyakan hal-hal berikut:\n"
        "• 'makanan sehat paling bagus apa saja?'\n"
        "• 'bagaimana tips diet?'\n"
        "• 'bagaimana cara mengontrol gula darah?'\n"
        "• 'berapa kebutuhan air harian?'\n"
        "• 'bagaimana cara input makanan baru?'\n"
        "• 'di mana melihat riwayat gizi saya?'"
    )
