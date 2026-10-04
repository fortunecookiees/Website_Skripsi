"""Konstanta aplikasi: path file, stasiun, kelompok fitur, dan kategori ISPU."""
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = ROOT / "data" / "datasetskripsi.xlsx"
MODEL_DIR = ROOT / "models"
EVAL_PATH = MODEL_DIR / "hasil_evaluasi.json"

HORIZONS = [1, 2, 3, 4, 5, 6, 7]

# ---------------------------------------------------------------------
# Stasiun SPKU (nama sama persis dengan kolom `stasiun` di dataset)
# ---------------------------------------------------------------------
STASIUN = {
    "DKI1 Bundaran HI":   {"kecamatan": "Menteng",       "lat": -6.1946, "lon": 106.8229},
    "DKI2 Kelapa Gading": {"kecamatan": "Kelapa Gading", "lat": -6.1553, "lon": 106.9070},
    "DKI3 Jagakarsa":     {"kecamatan": "Jagakarsa",     "lat": -6.3395, "lon": 106.8261},
    "DKI4 Lubang Buaya":  {"kecamatan": "Cipayung",      "lat": -6.2919, "lon": 106.9086},
    "DKI5 Kebon Jeruk":   {"kecamatan": "Kebon Jeruk",   "lat": -6.1919, "lon": 106.7683},
}

# ---------------------------------------------------------------------
# Fitur (urutan FITUR harus sama dengan `fitur` di .pkl)
# ---------------------------------------------------------------------
FITUR_SPASIAL = ["kepadatan_penduduk_jiwa_km2", "luas_rth_km2"]
FITUR_METEOROLOGI = ["suhu_c", "kelembapan_pct", "curah_hujan_mm", "tutupan_awan_pct",
                     "kecepatan_angin_kmh", "tekanan_hpa", "arah_angin_deg"]
FITUR_POLUTAN = ["pm10", "pm25", "so2", "co", "o3", "no2"]
FITUR_TURUNAN = ["pm25_lag1", "pm25_lag2", "pm25_lag3", "pm25_roll3", "bulan", "hari"]
FITUR = FITUR_SPASIAL + FITUR_METEOROLOGI + FITUR_POLUTAN + FITUR_TURUNAN

LABEL_FITUR = {
    "kepadatan_penduduk_jiwa_km2": ("Kepadatan penduduk", "jiwa/km²"),
    "luas_rth_km2": ("Luas RTH", "km²"),
    "suhu_c": ("Suhu", "°C"),
    "kelembapan_pct": ("Kelembapan", "%"),
    "curah_hujan_mm": ("Curah hujan", "mm"),
    "tutupan_awan_pct": ("Tutupan awan", "%"),
    "kecepatan_angin_kmh": ("Kecepatan angin", "km/jam"),
    "tekanan_hpa": ("Tekanan udara", "hPa"),
    "arah_angin_deg": ("Arah angin", "°"),
    "pm10": ("PM10", "ISPU"),
    "pm25": ("PM2.5", "ISPU"),
    "so2": ("SO₂", "ISPU"),
    "co": ("CO", "ISPU"),
    "o3": ("O₃", "ISPU"),
    "no2": ("NO₂", "ISPU"),
    "pm25_lag1": ("PM2.5 1 hari sebelumnya", "ISPU"),
    "pm25_lag2": ("PM2.5 2 hari sebelumnya", "ISPU"),
    "pm25_lag3": ("PM2.5 3 hari sebelumnya", "ISPU"),
    "pm25_roll3": ("Rata-rata PM2.5 3 hari sebelumnya", "ISPU"),
    "bulan": ("Bulan", "1–12"),
    "hari": ("Hari dalam minggu", "0=Senin … 6=Minggu"),
}

# ---------------------------------------------------------------------
# Kategori ISPU (PermenLHK No. 14/2020)
# ---------------------------------------------------------------------
KATEGORI_ISPU = [
    # (batas atas, nama, rentang, warna utama, warna latar lembut, warna teks di atas latar lembut)
    (50,  "Baik",               "1–50",    "#2E7D4F", "#E7F0EA", "#2E7D4F"),
    (100, "Sedang",             "51–100",  "#2A5F9E", "#E6ECF3", "#2A5F9E"),
    (200, "Tidak Sehat",        "101–200", "#B08300", "#F6EFDC", "#8A6A00"),
    (300, "Sangat Tidak Sehat", "201–300", "#B23A32", "#F4E6E5", "#B23A32"),
    (float("inf"), "Berbahaya", "≥301",    "#232323", "#E4E4E4", "#232323"),
]


def bulatkan_ispu(nilai: float) -> int:
    """Bulatkan ke integer, setengah ke atas (50,5 -> 51). ISPU selalu bilangan bulat."""
    return int(np.floor(float(nilai) + 0.5))


def kategori_ispu(nilai: float) -> dict:
    """Kategori ISPU dari nilai yang sudah dibulatkan, jadi tidak ada celah 50–51."""
    v = bulatkan_ispu(nilai)
    for batas, nama, rentang, warna, bg, teks in KATEGORI_ISPU:
        if v <= batas:
            return {"nilai": v, "kategori": nama, "rentang": rentang,
                    "warna": warna, "bg": bg, "warna_teks": teks}
