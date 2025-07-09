import gspread
from gspread_dataframe import get_as_dataframe
from oauth2client.service_account import ServiceAccountCredentials

# Inisialisasi kredensial
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
client = gspread.authorize(creds)

# Ganti sesuai nama spreadsheet kamu
spreadsheet = client.open("Binary Finance Data")
sheet = spreadsheet.sheet1

# Coba ambil isi spreadsheet ke DataFrame
df = get_as_dataframe(sheet)
print("✅ Berhasil terhubung!\n")
print(df)
