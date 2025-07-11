import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import google.generativeai as genai
import json
import os
from dotenv import load_dotenv

# Load API key dari .env
load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# Setup kredensial dan akses Google Sheets via st.secrets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds_dict = json.loads(st.secrets["GOOGLE_CREDS"])
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)

# Buka spreadsheet dan worksheet
sheet = client.open("Binary Finance Data").sheet1

# ==================== Fungsi Google Sheets ====================
def get_data():
    values = sheet.get_all_values()
    if not values or len(values) < 2:
        return pd.DataFrame()
    headers = values[0]
    rows = values[1:]
    df = pd.DataFrame(rows, columns=headers)
    df.columns = df.columns.str.strip()
    return df

def simpan_data(tanggal, kategori, tipe, jumlah, keterangan):
    sheet.append_row([tanggal.strftime("%Y/%m/%d"), kategori, tipe, jumlah, keterangan])

def hapus_baris(index):
    sheet.delete_rows(index)

def hapus_semua_data():
    header = sheet.row_values(1)
    sheet.clear()
    sheet.append_row(header)

# ==================== Fungsi AI Insight ====================
def generate_insight(data_summary):
    prompt = f"""
    Kamu adalah asisten keuangan pribadi. Berdasarkan data berikut ini, berikan insight/saran keuangan singkat:

    {data_summary}

    Jawab dalam bahasa Indonesia, singkat, dan jelas.
    """
    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        return f"(Gagal menghasilkan insight: {e})"

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
    df["Tipe"] = df["Tipe"].str.strip().str.capitalize()

    st.subheader("📄 10 Catatan Terakhir")
    st.dataframe(df.tail(10))

    df["Minggu"] = df["Tanggal"].dt.isocalendar().week
    df["Bulan"] = df["Tanggal"].dt.month

    mingguan = df.groupby(["Minggu", "Tipe"])["Jumlah"].sum().unstack().fillna(0)
    bulanan = df.groupby(["Bulan", "Tipe"])["Jumlah"].sum().unstack().fillna(0)

        # Ringkasan total uang
    total_pemasukan = df[df["Tipe"] == "Pemasukan"]["Jumlah"].sum()
    total_pengeluaran = df[df["Tipe"] == "Pengeluaran"]["Jumlah"].sum()
    total_saldo = total_pemasukan - total_pengeluaran

    st.subheader("💵 Ringkasan Keuangan Saat Ini")
    st.markdown(f"""
    - **Total Pemasukan:** Rp {int(total_pemasukan):,}
    - **Total Pengeluaran:** Rp {int(total_pengeluaran):,}
    - **Total Uang Sekarang:** Rp {int(total_saldo):,}
    """)

    st.subheader("📆 Grafik Mingguan")
    st.bar_chart(mingguan)

    st.subheader("📅 Grafik Bulanan")
    st.bar_chart(bulanan)

    st.subheader("🤖 Insight Keuangan dari AI")
    try:
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

    # ========================== Fitur Hapus Data ==========================
    st.markdown("---")
    st.subheader("🧹 Kelola Data")

    with st.expander("❌ Hapus Catatan Tertentu"):
        df_display = df.copy()
        df_display["Index Sheet"] = df_display.index + 2  # index + 2 karena header di baris 1
        st.dataframe(df_display)

        selected_index = st.number_input("Masukkan Index Sheet yang ingin dihapus", min_value=2, step=1)
        if st.button("🗑️ Hapus Catatan Ini"):
            try:
                hapus_baris(int(selected_index))
                st.success(f"✅ Baris ke-{int(selected_index)} berhasil dihapus.")
            except Exception as e:
                st.error(f"Gagal menghapus baris: {e}")

    with st.expander("⚠️ Hapus Semua Data"):
        if st.button("🧨 Hapus Semua Data (Reset Sheet)"):
            confirm = st.radio("Yakin ingin hapus semua data?", ["Tidak", "Ya"])
            if confirm == "Ya":
                hapus_semua_data()
                st.success("✅ Semua data berhasil dihapus (kecuali header).")

else:
    st.info("Belum ada data keuangan tercatat.")
