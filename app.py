import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
from openai import OpenAI
import json
import os
from dotenv import load_dotenv

# Load API key dari .env
load_dotenv()
client_ai = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Setup kredensial dan akses Google Sheets via st.secrets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds_dict = json.loads(st.secrets["GOOGLE_CREDS"])  # Ambil dari secrets TOML
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)

# Buka spreadsheet dan worksheet
sheet = client.open("Binary Finance Data").sheet1

# Fungsi ambil data dari Google Sheets
def get_data():
    values = sheet.get_all_values()
    if not values or len(values) < 2:
        return pd.DataFrame()
    headers = values[0]
    rows = values[1:]
    df = pd.DataFrame(rows, columns=headers)
    df.columns = df.columns.str.strip()
    return df

# Fungsi simpan data ke Google Sheets
def simpan_data(tanggal, kategori, tipe, jumlah, keterangan):
    sheet.append_row([tanggal.strftime("%Y/%m/%d"), kategori, tipe, jumlah, keterangan])

# Fungsi generate insight dari AI
def generate_insight(data_summary):
    prompt = f"""
    Kamu adalah asisten keuangan pribadi. Berdasarkan data berikut ini, berikan insight/saran keuangan singkat:

    {data_summary}

    Jawab dalam bahasa Indonesia, singkat, dan jelas.
    """
    response = client_ai.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=150,
        temperature=0.7,
    )
    
    return response.choices[0].message.content

# ========================== Streamlit UI ==========================
st.title("🧾 Binary Personal Finance Tracker v1")

st.header("💰 Tambah Catatan Keuangan")
tanggal = st.date_input("Tanggal", datetime.now())
kategori = st.selectbox("Kategori", ["Makan", "Transport", "Proyek", "Hiburan", "Lainnya"])
tipe = st.radio("Tipe", ["Pemasukan", "Pengeluaran"])
jumlah = st.number_input("Jumlah (Rp)", min_value=0)
keterangan = st.text_input("Keterangan (opsional)")

if st.button("Simpan"):
    simpan_data(tanggal, kategori, tipe, jumlah, keterangan)
    st.success("✅ Data berhasil disimpan!")

# ========================== Ringkasan Data ==========================
st.markdown("---")
st.header("📊 Ringkasan Data")
df = get_data()

if not df.empty:
    df.columns = df.columns.str.strip()
    df["Tanggal"] = pd.to_datetime(df["Tanggal"], errors='coerce')
    df["Jumlah"] = pd.to_numeric(df["Jumlah"], errors='coerce').fillna(0)
    df["Tipe"] = df["Tipe"].str.strip().str.capitalize()  # 🔧 Normalisasi kolom Tipe

    st.subheader("📄 10 Catatan Terakhir")
    st.dataframe(df.tail(10))

    df["Minggu"] = df["Tanggal"].dt.isocalendar().week
    df["Bulan"] = df["Tanggal"].dt.month

    mingguan = df.groupby(["Minggu", "Tipe"])["Jumlah"].sum().unstack().fillna(0)
    bulanan = df.groupby(["Bulan", "Tipe"])["Jumlah"].sum().unstack().fillna(0)

    st.subheader("📆 Grafik Mingguan")
    st.bar_chart(mingguan)

    st.subheader("📅 Grafik Bulanan")
    st.bar_chart(bulanan)

    st.subheader("🤖 Insight Keuangan dari AI")

    try:
        # Default Series kosong kalau belum ada datanya
        pemasukan = bulanan.get("Pemasukan", pd.Series(dtype=float))
        pengeluaran = bulanan.get("Pengeluaran", pd.Series(dtype=float))

        pengeluaran_df = df[df["Tipe"] == "Pengeluaran"]
        kategori_terbesar = (
            pengeluaran_df.groupby("Kategori")["Jumlah"]
            .sum()
            .sort_values(ascending=False)
            .head(1)
        )

        summary_text = f"""
        Total pemasukan bulan ini: Rp {int(pemasukan.sum()):,}
        Total pengeluaran bulan ini: Rp {int(pengeluaran.sum()):,}

        Kategori pengeluaran terbesar minggu ini:
        {kategori_terbesar.to_string()}
        """

        if st.button("🔍 Dapatkan Insight AI"):
            with st.spinner("Sedang menganalisis..."):
                ai_result = generate_insight(summary_text)
                st.success("Insight berhasil dihasilkan!")
                st.markdown(f"💬 **AI Insight:** {ai_result}")
    except Exception as e:
        st.warning("Belum cukup data untuk menghasilkan insight.")
        st.text(f"(Debug: {e})")
else:
    st.info("Belum ada data keuangan tercatat.")
