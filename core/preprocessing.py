"""Preprocessing dataset — identik dengan train/training.py (langkah 2–5)."""
import numpy as np
import pandas as pd

from .config import DATA_PATH, FITUR, FITUR_POLUTAN, HORIZONS

KOLOM_LEAKAGE = ["max", "parameter_kritis", "kategori"]
KOLOM_LAG = ["pm25_lag1", "pm25_lag2", "pm25_lag3", "pm25_roll3"]
KOLOM_TARGET = [f"target_h{h}" for h in HORIZONS]


def muat_dataset(path=DATA_PATH) -> pd.DataFrame:
    """Baca dataset mentah dari Excel."""
    df = pd.read_excel(path)
    df["tanggal"] = pd.to_datetime(df["tanggal"])
    return df


def preprocess(df_mentah: pd.DataFrame) -> pd.DataFrame:
    """Buang kolom leakage, ffill polutan, lalu buat fitur lag/rolling/waktu & target t+1..t+7.

    Belum ada dropna: baris tanpa target (2–8 Nov 2025) tetap dipertahankan
    supaya kondisi terakhir bisa dipakai untuk prediksi aktual.
    """
    df = df_mentah.drop(columns=[c for c in KOLOM_LEAKAGE if c in df_mentah.columns])
    df = df.sort_values(["stasiun", "tanggal"]).reset_index(drop=True)

    # tandai PM2.5 asli (bukan hasil pengisian) -> metrik hanya di nilai asli
    df["pm25_asli"] = df["pm25"].notna()
    df[FITUR_POLUTAN] = df.groupby("stasiun")[FITUR_POLUTAN].transform(lambda s: s.ffill(limit=7))

    g = df.groupby("stasiun")
    for lg in [1, 2, 3]:
        df[f"pm25_lag{lg}"] = g["pm25"].shift(lg)
    df["pm25_roll3"] = g["pm25"].transform(lambda s: s.shift(1).rolling(3).mean())
    df["bulan"] = df["tanggal"].dt.month
    df["hari"] = df["tanggal"].dt.dayofweek

    for h in HORIZONS:
        df[f"target_h{h}"] = g["pm25"].shift(-h)
        df[f"target_h{h}_asli"] = g["pm25_asli"].shift(-h).eq(True)  # NaN -> False
    return df


def kondisi_terakhir(df: pd.DataFrame, stasiun: str) -> pd.Series:
    """Baris fitur hari terakhir dataset untuk satu stasiun (dasar Mode Prediksi Aktual)."""
    baris = df[df["stasiun"] == stasiun].dropna(subset=KOLOM_LAG)
    if baris.empty:
        raise ValueError(f"Stasiun tidak ditemukan atau fitur lag kosong: {stasiun}")
    return baris.loc[baris["tanggal"].idxmax()]


def data_evaluasi(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Timestamp]:
    """Replikasi split training: dropna lag + target, lalu data uji = tanggal >= tu[int(n*0.85)].

    Mengembalikan (data uji, tanggal batas uji).
    """
    siap = df.dropna(subset=KOLOM_LAG + KOLOM_TARGET).reset_index(drop=True)
    tu = np.sort(siap["tanggal"].unique())
    batas_uji = pd.Timestamp(tu[int(len(tu) * 0.85)])
    uji = siap[siap["tanggal"] >= batas_uji].reset_index(drop=True)
    return uji, batas_uji


def matriks_fitur(baris: pd.DataFrame | pd.Series) -> pd.DataFrame:
    """Ambil kolom fitur dengan urutan yang sama seperti saat training."""
    if isinstance(baris, pd.Series):
        baris = baris.to_frame().T
    return baris[FITUR].astype(float)
