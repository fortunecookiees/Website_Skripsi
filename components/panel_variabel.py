"""Panel 21 variabel masukan: spasial (penanda khusus), meteorologi, polutan, turunan."""
import math

import pandas as pd
import streamlit as st

from .format import BULAN, HARI, angka

# fitur: (nama singkat, satuan, jumlah desimal tampilan, langkah slider)
TAMPILAN = {
    "luas_rth_km2": ("Luas RTH", "km²", 3, 0.001),
    "kepadatan_penduduk_jiwa_km2": ("Kepadatan", "j/km²", 0, 1.0),
    "suhu_c": ("Suhu", "°C", 1, 0.01),
    "kelembapan_pct": ("Kelembapan", "%", 0, 0.01),
    "curah_hujan_mm": ("Curah hujan", "mm", 1, 0.1),
    "tutupan_awan_pct": ("Tutupan awan", "%", 0, 0.01),
    "kecepatan_angin_kmh": ("Kec. angin", "km/j", 1, 0.01),
    "tekanan_hpa": ("Tekanan", "hPa", 0, 0.01),
    "arah_angin_deg": ("Arah angin", "°", 0, 0.01),
    "pm25": ("PM2.5", "ISPU", 0, 1.0),
    "pm10": ("PM10", "ISPU", 0, 1.0),
    "so2": ("SO₂", "ISPU", 0, 1.0),
    "co": ("CO", "ISPU", 0, 1.0),
    "o3": ("O₃", "ISPU", 0, 1.0),
    "no2": ("NO₂", "ISPU", 0, 1.0),
}

# urutan tampilan mengikuti desain (urutan input model tetap FITUR di core/config.py)
KELOMPOK = [
    ("spasial", "Variabel Spasial", ["luas_rth_km2", "kepadatan_penduduk_jiwa_km2"], "#1c1c1c", "novelty penelitian"),
    ("meteorologi", "Meteorologi", ["suhu_c", "kelembapan_pct", "curah_hujan_mm", "tutupan_awan_pct",
                                     "kecepatan_angin_kmh", "tekanan_hpa", "arah_angin_deg"], "#b0b0b0", ""),
    ("polutan", "Polutan Udara", ["pm25", "pm10", "so2", "co", "o3", "no2"], "#b0b0b0", ""),
]


def nilai_tampil(fitur: str, nilai: float) -> str:
    _, satuan, desimal, _ = TAMPILAN[fitur]
    pemisah = "" if satuan == "°" else " "
    return f"{angka(nilai, desimal)}{pemisah}{satuan}"


def _baris_slider(fitur: str, nilai: float, rentang: pd.Series, terkunci: bool, kunci: str) -> float:
    nama, _, _, langkah = TAMPILAN[fitur]
    c_nama, c_slider, c_nilai = st.columns([1.05, 2.6, 1.05], vertical_alignment="center")
    c_nama.html(f'<div class="sName">{nama}</div>')
    if nilai is None or math.isnan(nilai):
        c_slider.html('<div class="sNa">data tidak tersedia</div>')
        c_nilai.html('<div class="sVal">–</div>')
        return float("nan")
    lo, hi = float(rentang["min"]), float(rentang["max"])
    nilai = min(max(float(nilai), lo), hi)
    with c_slider:
        v = st.slider(nama, min_value=lo, max_value=hi, value=nilai, step=langkah,
                      disabled=terkunci, label_visibility="collapsed", key=kunci)
    c_nilai.html(f'<div class="sVal">{nilai_tampil(fitur, v)}</div>')
    return v


def panel_variabel(baris: pd.Series, rentang: pd.DataFrame, terkunci: bool, prefix: str) -> dict:
    """Render slider per kelompok. Mengembalikan {fitur: nilai} dari slider."""
    hasil = {}
    for kode, nama, fitur_list, warna, catatan in KELOMPOK:
        with st.container(key=f"grp_{kode}"):
            note = f'<span class="grpNote">{catatan}</span>' if catatan else ""
            st.html(f'<div class="grpHead"><span class="grpDot" style="background:{warna}"></span>'
                    f'<span class="grpName">{nama}</span><span class="grpCount">{len(fitur_list)} fitur</span>{note}</div>')
            for f in fitur_list:
                hasil[f] = _baris_slider(f, baris[f], rentang.loc[f], terkunci, f"{prefix}_{f}")
    _kotak_turunan(baris)
    return hasil


def _kotak_turunan(baris: pd.Series) -> None:
    rincian = (f"PM2.5 hari ke-1: <b>{angka(baris['pm25_lag1'])}</b> · ke-2: <b>{angka(baris['pm25_lag2'])}</b> · "
               f"ke-3 sebelumnya: <b>{angka(baris['pm25_lag3'])}</b> · rata-rata bergerak 3 hari: "
               f"<b>{angka(baris['pm25_roll3'], 1)}</b> · bulan: <b>{BULAN[int(baris['bulan']) - 1]}</b> · "
               f"hari: <b>{HARI[int(baris['hari'])]}</b>")
    st.html(f'<div class="derived"><b>Dihitung otomatis dari data historis — 6 fitur</b><br>{rincian}</div>'
            '<div class="note" style="text-align:right">Total <b>21 fitur masukan</b></div>')
