"""Aturan fitur turunan pada Mode Simulasi (logika murni, tanpa Streamlit).

Model, scaler, dan preprocessing tidak berubah: fungsi ini hanya menyusun nilai masukan skenario.
"""
import pandas as pd

LAG_PM25 = ["pm25_lag1", "pm25_lag2", "pm25_lag3"]


def samakan_riwayat_pm25(fitur: pd.Series, pm25: float) -> pd.Series:
    """Opsi simulasi: anggap PM2.5 tiga hari sebelumnya sama dengan PM2.5 hari ini.

    pm25_lag1..lag3 = pm25, lalu pm25_roll3 = rata-rata ketiganya, sesuai definisi training
    (shift(1).rolling(3).mean() = rata-rata lag1, lag2, lag3). Bulan & hari tetap dari kondisi acuan.
    """
    hasil = fitur.copy()
    for f in LAG_PM25:
        hasil[f] = float(pm25)
    hasil["pm25_roll3"] = float(hasil[LAG_PM25].astype(float).mean())
    return hasil
