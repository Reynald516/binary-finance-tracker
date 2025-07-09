import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import openai
import os
from dotenv import load_dotenv

# Load API key dari .env
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

# Setup kredensial dan akses Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
client = gspread.authorize(creds)

# Buka spreadsheet dan worksheet
sheet = client.open("Binary Finance Data").sheet1

# Fungsi ambil data dari Google Sheets
def get_data():
    values = sheet.get_all_values()
    if not values or len(values) < 2:
        return pd.DataFrame()  # Kalau kosong, return dataframe kosong
    headers = values[0]
    rows = values[1:]
    df = pd.DataFrame(rows, columns=headers)
    df.columns = df.columns.str.strip()  # hilangkan spasi tak sengaja
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

    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=150,
        temperature=0.7,
    )

    return response.choices[0].message["content"]

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
    df.columns = df.columns.str.strip()  # pastikan kolom bersih dari spasi
    df["Tanggal"] = pd.to_datetime(df["Tanggal"], errors='coerce')
    df["Jumlah"] = pd.to_numeric(df["Jumlah"], errors='coerce').fillna(0)

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
        pengeluaran = df[df["Tipe"] == "Pengeluaran"]
        summary_text = f"""
        Total pemasukan bulan ini: Rp {int(bulanan.get("Pemasukan", pd.Series()).sum()):,}
        Total pengeluaran bulan ini: Rp {int(bulanan.get("Pengeluaran", pd.Series()).sum()):,}

        Kategori pengeluaran terbesar minggu ini:
        {pengeluaran.groupby("Kategori")["Jumlah"].sum().sort_values(ascending=False).head(1).to_string()}
        """
        if st.button("🔍 Dapatkan Insight AI"):
            with st.spinner("Sedang menganalisis..."):
                ai_result = generate_insight(summary_text)
                st.success("Insight berhasil dihasilkan!")
                st.markdown(f"💬 **AI Insight:** {ai_result}")
    except:
        st.warning("Belum cukup data untuk menghasilkan insight.")
else:
    st.info("Belum ada data keuangan tercatat.")
