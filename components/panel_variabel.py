"""Panel 21 variabel masukan: spasial (penanda khusus), meteorologi, polutan, turunan."""
import math

import pandas as pd
import streamlit as st

from core.simulasi import samakan_riwayat_pm25

from .bahasa import inggris, t
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

# versi Inggris nama singkat & satuan (yang tidak ada di sini sama di kedua bahasa)
NAMA_EN = {"luas_rth_km2": "GOS area", "kepadatan_penduduk_jiwa_km2": "Density", "suhu_c": "Temperature",
           "kelembapan_pct": "Humidity", "curah_hujan_mm": "Rainfall", "tutupan_awan_pct": "Cloud cover",
           "kecepatan_angin_kmh": "Wind speed", "tekanan_hpa": "Pressure", "arah_angin_deg": "Wind dir."}
SATUAN_EN = {"j/km²": "p/km²", "km/j": "km/h"}
PANJANG_EN = {
    "luas_rth_km2": "green open space area", "kepadatan_penduduk_jiwa_km2": "population density",
    "suhu_c": "temperature", "kelembapan_pct": "humidity", "curah_hujan_mm": "rainfall",
    "tutupan_awan_pct": "cloud cover", "kecepatan_angin_kmh": "wind speed", "tekanan_hpa": "air pressure",
    "arah_angin_deg": "wind direction",
}

# nama dalam kalimat (huruf kecil kecuali singkatan)
PANJANG = {
    "luas_rth_km2": "luas RTH", "kepadatan_penduduk_jiwa_km2": "kepadatan penduduk", "suhu_c": "suhu",
    "kelembapan_pct": "kelembapan", "curah_hujan_mm": "curah hujan", "tutupan_awan_pct": "tutupan awan",
    "kecepatan_angin_kmh": "kecepatan angin", "tekanan_hpa": "tekanan udara", "arah_angin_deg": "arah angin",
}

# urutan tampilan mengikuti desain (urutan input model tetap FITUR di core/config.py)
KELOMPOK = [
    ("spasial", ("Variabel Spasial", "Spatial Variables"), ["luas_rth_km2", "kepadatan_penduduk_jiwa_km2"],
     "#347653", ""),
    ("meteorologi", ("Meteorologi", "Meteorology"), ["suhu_c", "kelembapan_pct", "curah_hujan_mm",
                                                     "tutupan_awan_pct", "kecepatan_angin_kmh", "tekanan_hpa",
                                                     "arah_angin_deg"], "#c9dbe7", ""),
    ("polutan", ("Polutan Udara", "Air Pollutants"), ["pm25", "pm10", "so2", "co", "o3", "no2"], "#c9dbe7", ""),
]


def nama_singkat(fitur: str) -> str:
    return NAMA_EN.get(fitur, TAMPILAN[fitur][0]) if inggris() else TAMPILAN[fitur][0]


def nilai_tampil(fitur: str, nilai: float) -> str:
    _, satuan, desimal, _ = TAMPILAN[fitur]
    satuan = SATUAN_EN.get(satuan, satuan) if inggris() else satuan
    pemisah = "" if satuan == "°" else " "
    return f"{angka(nilai, desimal)}{pemisah}{satuan}"


def _baris_slider(fitur: str, nilai: float, rentang: pd.Series, terkunci: bool, kunci: str) -> float:
    _, _, _, langkah = TAMPILAN[fitur]
    nama = nama_singkat(fitur)
    c_nama, c_slider, c_nilai = st.columns([1.05, 2.6, 1.05], vertical_alignment="center")
    c_nama.html(f'<div class="sName">{nama}</div>')
    if nilai is None or math.isnan(nilai):
        c_slider.html(f'<div class="sNa">{t("data tidak tersedia", "data not available")}</div>')
        c_nilai.html('<div class="sVal">–</div>')
        return float("nan")
    lo, hi = float(rentang["min"]), float(rentang["max"])
    if kunci not in st.session_state:
        # panel terkunci (Mode Aktual) menampilkan kondisi aktual; slider simulasi mulai dari ujung kiri (minimum dataset)
        st.session_state[kunci] = min(max(float(nilai), lo), hi) if terkunci else lo
    with c_slider:
        v = st.slider(nama, min_value=lo, max_value=hi, step=langkah,
                      disabled=terkunci, label_visibility="collapsed", key=kunci)
    c_nilai.html(f'<div class="sVal">{nilai_tampil(fitur, v)}</div>')
    return v


def _kunci(prefix: str, fitur: str) -> str:
    return f"{prefix}_{fitur}"


def kunci_samakan(prefix: str) -> str:
    return f"{prefix}_samakan_riwayat"


def samakan_aktif(prefix: str, pm25: float) -> bool:
    """Toggle 'samakan riwayat PM2.5' menyala dan PM2.5 hari ini tersedia."""
    return bool(st.session_state.get(kunci_samakan(prefix))) and not math.isnan(pm25)


def panel_variabel(baris: pd.Series, rentang: pd.DataFrame, terkunci: bool, prefix: str) -> dict:
    """Render slider per kelompok. Mengembalikan {fitur: nilai} dari slider.

    Panel simulasi (tidak terkunci) menampilkan toggle riwayat PM2.5 di bawah slider PM2.5.
    """
    hasil = {}
    for kode, nama, fitur_list, warna, catatan in KELOMPOK:
        with st.container(key=f"grp_{kode}"):
            note = f'<span class="grpNote">{catatan}</span>' if catatan else ""
            st.html(f'<div class="grpHead"><span class="grpDot" style="background:{warna}"></span>'
                    f'<span class="grpName">{t(*nama)}</span><span class="grpCount">{len(fitur_list)} '
                    f'{t("fitur", "features")}</span>{note}</div>')
            for f in fitur_list:
                hasil[f] = _baris_slider(f, baris[f], rentang.loc[f], terkunci, _kunci(prefix, f))
                if f == "pm25" and not terkunci:
                    with st.container(key="samakan_riwayat"):
                        st.toggle(t("Samakan PM2.5 3 hari sebelumnya dengan nilai hari ini",
                                    "Set PM2.5 of the previous 3 days to today's value"),
                                  key=kunci_samakan(prefix), disabled=math.isnan(hasil[f]))
                        st.html('<div class="note">' + t(
                            "Jika mati, riwayat PM2.5 memakai data asli sehingga lonjakan satu hari cenderung "
                            "diprediksi turun kembali.",
                            "When off, the PM2.5 history uses the real data, so a one-day spike tends to be "
                            "predicted to drop back.") + '</div>')
    disamakan = not terkunci and samakan_aktif(prefix, hasil["pm25"])
    _kotak_turunan(samakan_riwayat_pm25(baris, hasil["pm25"]) if disamakan else baris, disamakan)
    return hasil


def reset_slider(baris: pd.Series, rentang: pd.DataFrame, prefix: str) -> None:
    """Callback tombol reset: kembalikan semua slider ke nilai kondisi aktual dan matikan toggle riwayat."""
    for f in TAMPILAN:
        if not math.isnan(baris[f]):
            lo, hi = rentang.loc[f, "min"], rentang.loc[f, "max"]
            st.session_state[_kunci(prefix, f)] = min(max(float(baris[f]), lo), hi)
    st.session_state[kunci_samakan(prefix)] = False


def daftar_perubahan(aktual: pd.Series, simulasi: dict) -> list[str]:
    """Frasa 'luas RTH dinaikkan menjadi 1,640 km²' untuk tiap variabel yang digeser."""
    hasil = []
    for _, _, fitur_list, _, _ in KELOMPOK:
        for f in fitur_list:
            lama, baru = aktual[f], simulasi[f]
            if math.isnan(lama) or abs(baru - lama) < TAMPILAN[f][3] / 2:
                continue
            nilai = nilai_tampil(f, baru).replace("j/km²", "jiwa/km²").replace("p/km²", "people/km²")
            if inggris():
                arah = "raised" if baru > lama else "lowered"
                hasil.append(f"{PANJANG_EN.get(f, TAMPILAN[f][0])} {arah} to {nilai}")
            else:
                arah = "dinaikkan" if baru > lama else "diturunkan"
                hasil.append(f"{PANJANG.get(f, TAMPILAN[f][0])} {arah} menjadi {nilai}")
    return hasil


def _kotak_turunan(baris: pd.Series, disamakan: bool = False) -> None:
    l1, l2, l3 = (angka(baris[f"pm25_lag{i}"]) for i in (1, 2, 3))
    roll, bulan, hari = angka(baris["pm25_roll3"], 1), BULAN[int(baris["bulan"]) - 1], HARI[int(baris["hari"])]
    rincian = t(f"PM2.5 hari ke-1: <b>{l1}</b> · ke-2: <b>{l2}</b> · ke-3 sebelumnya: <b>{l3}</b> · rata-rata "
                f"bergerak 3 hari: <b>{roll}</b> · bulan: <b>{bulan}</b> · hari: <b>{hari}</b>",
                f"PM2.5 1 day before: <b>{l1}</b> · 2 days: <b>{l2}</b> · 3 days: <b>{l3}</b> · 3-day moving "
                f"average: <b>{roll}</b> · month: <b>{bulan}</b> · day: <b>{hari}</b>")
    if disamakan:
        judul = t("Dihitung otomatis — riwayat PM2.5 disamakan dengan nilai hari ini",
                  "Computed automatically — PM2.5 history set to today's value")
    else:
        judul = t("Dihitung otomatis dari data historis — 6 fitur",
                  "Computed automatically from historical data — 6 features")
    st.html(f'<div class="derived"><b>{judul}</b><br>{rincian}</div>'
            '<div class="note" style="text-align:right">' + t("Total <b>21 fitur masukan</b>",
                                                              "Total <b>21 input features</b>") + '</div>')
