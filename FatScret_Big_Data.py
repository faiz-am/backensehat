# === Cell 1 ===
# pip install requests requests_oauthlib pymongo pandas matplotlib

# === Cell 3 ===

# Define display fallback for CLI environment
try:
    from IPython.display import display
except ImportError:
    display = print

from requests_oauthlib import OAuth1
import requests
from pymongo import MongoClient
import pandas as pd
import re
HAS_MATPLOTLIB = True
try:
    import matplotlib.pyplot as plt
except ImportError:
    HAS_MATPLOTLIB = False

# === Cell 5 ===
import requests
import base64

CLIENT_ID = "f7d2cf713f57464c99fe3a1fbcc6f2a8"
CLIENT_SECRET = "d792c7c85a2040ad88cbad425a485fa4"

auth = base64.b64encode(f"{CLIENT_ID}:{CLIENT_SECRET}".encode()).decode()

url = "https://oauth.fatsecret.com/connect/token"

headers = {
    "Authorization": f"Basic {auth}",
    "Content-Type": "application/x-www-form-urlencoded"
}

data = {
    "grant_type": "client_credentials"
}

res = requests.post(url, headers=headers, data=data)

print(res.status_code)
print(res.text)

# === Cell 7 ===
from requests_oauthlib import OAuth1
import requests

CONSUMER_KEY = "f7d2cf713f57464c99fe3a1fbcc6f2a8"
CONSUMER_SECRET = "d792c7c85a2040ad88cbad425a485fa4"

url = "https://platform.fatsecret.com/rest/server.api"

auth = OAuth1(CONSUMER_KEY, CONSUMER_SECRET)

queries = ["rice", "chicken", "apple"]
data_mongo = []

for q in queries:
    params = {
        "method": "foods.search",
        "search_expression": q,
        "format": "json"
    }

    res = requests.get(url, params=params, auth=auth)

    print(f"\n🔎 {q} | Status:", res.status_code)

    try:
        data = res.json()
    except:
        print("❌ Response bukan JSON:", res.text)
        continue

    if "foods" in data:
        foods = data["foods"]["food"]

        if isinstance(foods, dict):
            foods = [foods]

        for item in foods[:5]:
            data_mongo.append({
                "input": q,
                "name": item.get("food_name"),
                "desc": item.get("food_description")
            })
    else:
        print("❌ Error API:", data)

print("Total data:", len(data_mongo))

# === Cell 9 ===
client = MongoClient("mongodb+srv://riyannurhidayat297:RIYAN123@cluster0.3j2umo0.mongodb.net/?appName=Cluster0")

db = client["mulai_sehat"]        # sesuai gambar
collection = db["nutrition"]      # pakai collection nutrition

collection.delete_many({})

collection.insert_many(data_mongo)

print("✅ Data masuk MongoDB")

# === Cell 11 ===
data = list(collection.find())
df = pd.DataFrame(data)

print("📦 Data awal:")
display(df.head())

# === Cell 12 ===
print("\n📦 Data di MongoDB:")
for item in collection.find().limit(5):
    print(item)

# === Cell 14 ===
def extract_nutrition(desc):
    data = {
        "calories": None,
        "protein_g": None,
        "fat_total_g": None,
        "carbs_g": None
    }

    if not desc:
        return data

    patterns = {
        "calories": r"Calories:\s*(\d+)",
        "protein_g": r"Protein:\s*([\d\.]+)g",
        "fat_total_g": r"Fat:\s*([\d\.]+)g",
        "carbs_g": r"Carbs:\s*([\d\.]+)g"
    }

    for key, pattern in patterns.items():
        match = re.search(pattern, desc)
        if match:
            data[key] = match.group(1)

    return data

nutrition_df = df["desc"].apply(lambda x: extract_nutrition(x)).apply(pd.Series)
df = pd.concat([df, nutrition_df], axis=1)

# === Cell 15 ===
if "_id" in df.columns:
    df = df.drop("_id", axis=1)

cols = ["calories", "protein_g", "fat_total_g", "carbs_g"]

for col in cols:
    df[col] = pd.to_numeric(df[col], errors="coerce")

df[cols] = df[cols].fillna(0)

df = df.drop_duplicates()

print("\n🧹 Data setelah cleaning:")
display(df)

# === Cell 17 ===
print("\n📈 Statistik:")
print(df.describe())

print("\n📊 Rata-rata Nutrisi:")
print(df[cols].mean())

print("\n🔥 Top Kalori:")
print(df.sort_values(by="calories", ascending=False)[["name","calories"]].head(5))

print("\n💪 Top Protein:")
print(df.sort_values(by="protein_g", ascending=False)[["name","protein_g"]].head(5))

print("\n🔗 Korelasi:")
print(df[cols].corr())

# === Cell 19 ===
if HAS_MATPLOTLIB:
    try:
        plt.figure()
        df.sort_values("calories", ascending=False).head(5).plot(
            x="name", y="calories", kind="bar"
        )
        plt.title("Top 5 Makanan Berdasarkan Kalori")
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.show()
    except Exception as e:
        print(f"Bypass plotting error: {e}")

# === Cell 20 ===
if HAS_MATPLOTLIB:
    try:
        plt.figure()
        df.sort_values("protein_g", ascending=False).head(5).plot(
            x="name", y="protein_g", kind="bar"
        )
        plt.title("Top 5 Makanan Berdasarkan Protein")
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.show()
    except Exception as e:
        print(f"Bypass plotting error: {e}")

# === Cell 21 ===
if HAS_MATPLOTLIB:
    try:
        plt.figure()
        corr = df[cols].corr()
        plt.imshow(corr)
        plt.colorbar()
        plt.xticks(range(len(cols)), cols, rotation=45)
        plt.yticks(range(len(cols)), cols)
        plt.title("Korelasi Nutrisi")
        plt.show()
    except Exception as e:
        print(f"Bypass plotting error: {e}")

# === Cell 22 ===
df.to_csv("hasil_nutrisi.csv", index=False)
print("✅ Disimpan ke CSV")

# === Cell 24 ===
def health_score(calories, fat):
    if calories < 300 and fat < 15:
        return "Healthy"
    else:
        return "Less Healthy"

df["health_status"] = df.apply(
    lambda x: health_score(
        x["calories"],
        x["fat_total_g"]
    ),
    axis=1
)

print("\n💪 Hasil Analisis:")
display(df)

# === Cell 26 ===
if HAS_MATPLOTLIB:
    try:
        df["health_status"].value_counts().plot(kind="bar")
        plt.title("Distribusi Healthy vs Less Healthy")
        plt.show()
        
        # ==========================================
        # TAMBAHAN PIE CHART
        # ==========================================
        plt.figure()
        
        kategori_counts = df["health_status"].value_counts()
        
        plt.pie(
            kategori_counts,
            labels=kategori_counts.index,
            autopct='%1.1f%%'
        )
        
        plt.title("Distribusi Kategori Makanan")
        plt.show()
    except Exception as e:
        print(f"Bypass plotting error: {e}")

# === Cell 27 ===
print("\n📊 INSIGHT")

print("Rata-rata Kalori :", df["calories"].mean())
print("Rata-rata Lemak  :", df["fat_total_g"].mean())

# === Cell 28 ===
analysis_collection = db["analysis"]

analysis_collection.delete_many({})
analysis_collection.insert_many(df.to_dict("records"))

print("✅ Hasil analisis disimpan ke MongoDB")

# === Cell 29 ===
healthy = (df["health_status"] == "Healthy").sum()
unhealthy = (df["health_status"] == "Less Healthy").sum()

print("\n📌 KESIMPULAN")
print("Healthy :", healthy)
print("Less Healthy :", unhealthy)
