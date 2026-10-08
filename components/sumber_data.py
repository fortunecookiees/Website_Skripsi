"""Pemuatan model & data dengan cache Streamlit (lapisan tipis di atas core/)."""
import json

import pandas as pd
import streamlit as st

from core.config import EVAL_PATH, FITUR, RTH_KOORDINAT_PATH, SKENARIO_PATH
from core.inference import muat_model, prediksi_7_hari, prediksi_batch
from core.preprocessing import data_evaluasi, kondisi_terakhir, muat_dataset, preprocess
from core.unggah import buat_template


@st.cache_resource(show_spinner="Memuat model…")
def model() -> dict:
    return muat_model()


@st.cache_data(show_spinner="Memuat dataset…")
def dataset_mentah() -> pd.DataFrame:
    return muat_dataset()


@st.cache_data(show_spinner="Memuat dataset…")
def dataset() -> pd.DataFrame:
    return preprocess(dataset_mentah())


@st.cache_data
def tanggal_terakhir() -> pd.Timestamp:
    return dataset()["tanggal"].max()


@st.cache_data
def kondisi(stasiun: str) -> pd.Series:
    return kondisi_terakhir(dataset(), stasiun)


@st.cache_data
def prediksi_aktual(stasiun: str) -> pd.DataFrame:
    """Prediksi t+1..t+7 dari kondisi terakhir dataset (Mode Prediksi Aktual)."""
    return prediksi_7_hari(model(), kondisi(stasiun))


@st.cache_data
def rentang_fitur() -> pd.DataFrame:
    """Nilai min & maks tiap fitur di seluruh dataset (batas slider)."""
    return dataset()[FITUR].agg(["min", "max"]).T


@st.cache_data
def periode_uji() -> tuple[pd.Timestamp, pd.Timestamp, int]:
    uji, batas = data_evaluasi(dataset())
    return batas, uji["tanggal"].max(), len(uji)


@st.cache_data(show_spinner="Menghitung prediksi data uji…")
def prediksi_uji() -> pd.DataFrame:
    """Data uji (replikasi split training) + kolom pred_h1..pred_h7."""
    uji, _ = data_evaluasi(dataset())
    return pd.concat([uji, prediksi_batch(model(), uji)], axis=1)


@st.cache_data
def hasil_evaluasi() -> dict:
    with open(EVAL_PATH, encoding="utf-8") as f:
        return json.load(f)


@st.cache_data
def feature_importance(horizon: int = 1) -> pd.Series:
    """Importance (gain, bawaan xgboost) model horizon tertentu, urut menurun."""
    m = model()[horizon]["model"]
    return pd.Series(m.feature_importances_, index=FITUR).sort_values(ascending=False)


@st.cache_data
def hasil_skenario() -> dict:
    with open(SKENARIO_PATH, encoding="utf-8") as f:
        return json.load(f)


@st.cache_data
def rentang_tanggal() -> tuple[pd.Timestamp, pd.Timestamp]:
    t = dataset()["tanggal"]
    return t.min(), t.max()


@st.cache_data
def nilai_spasial() -> pd.DataFrame:
    """Kepadatan & luas RTH per stasiun per tahun (nilai pertama tiap tahun, seperti cek di training)."""
    d = dataset()
    return (d.groupby(["stasiun", d["tanggal"].dt.year])[["kepadatan_penduduk_jiwa_km2", "luas_rth_km2"]]
            .first().rename_axis(["stasiun", "tahun"]).reset_index())


@st.cache_data(show_spinner=False)
def template_unggah() -> bytes:
    return buat_template(dataset_mentah())


@st.cache_data
def titik_rth() -> pd.DataFrame:
    """Titik RTH yang lokasinya terverifikasi (presisi objek/manual) dari data/rth_koordinat.csv.

    File dihasilkan sekali oleh scripts/geocode_rth.py; jika belum ada, peta tampil tanpa titik RTH.
    """
    if not RTH_KOORDINAT_PATH.exists():
        return pd.DataFrame(columns=["kecamatan", "kelurahan", "nama_rth", "jenis_rth", "luas_m2", "lat", "lon", "presisi"])
    d = pd.read_csv(RTH_KOORDINAT_PATH, encoding="utf-8-sig")
    return d[d["presisi"].isin(["objek", "manual"])].dropna(subset=["lat", "lon"]).reset_index(drop=True)
