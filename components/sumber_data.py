"""Pemuatan model & data dengan cache Streamlit (lapisan tipis di atas core/)."""
import json

import pandas as pd
import streamlit as st

from core.config import EVAL_PATH, FITUR
from core.inference import muat_model, prediksi_7_hari, prediksi_batch
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
