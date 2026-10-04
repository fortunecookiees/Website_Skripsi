"""Pemuatan model & data dengan cache Streamlit (lapisan tipis di atas core/)."""
import pandas as pd
import streamlit as st

from core.config import FITUR
from core.inference import muat_model, prediksi_7_hari
from core.preprocessing import data_evaluasi, kondisi_terakhir, muat_dataset, preprocess


@st.cache_resource(show_spinner="Memuat model…")
def model() -> dict:
    return muat_model()


@st.cache_data(show_spinner="Memuat dataset…")
def dataset() -> pd.DataFrame:
    return preprocess(muat_dataset())


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
