"""Pemuatan model & data dengan cache Streamlit (lapisan tipis di atas core/)."""
import json

import pandas as pd
import streamlit as st

from core.config import EVAL_PATH, FITUR, RTH_KOORDINAT_PATH, SKENARIO_PATH
from core.inference import muat_model, prediksi_7_hari, prediksi_batch
from core.metrik import bentuk_panjang
from core.preprocessing import data_evaluasi, kondisi_terakhir, muat_dataset, preprocess
from core.unggah import buat_template
from core.versi_data import SumberDashboard, label_sumber, muat_data_dashboard

from .bahasa import inggris


@st.cache_resource(show_spinner=False)
def model() -> dict:
    return muat_model()


@st.cache_data(show_spinner=False)
def dataset_mentah() -> pd.DataFrame:
    return muat_dataset()


@st.cache_data(show_spinner=False)
def dataset() -> pd.DataFrame:
    return preprocess(dataset_mentah())


@st.cache_data(show_spinner=False)
def tanggal_terakhir() -> pd.Timestamp:
    return dataset()["tanggal"].max()


# ---------------------------------------------------------------------
# Data Dashboard (Mode Aktual & titik awal simulasi): versi aktif admin, atau dataset penelitian.
# Evaluation, Data Historis, dan rentang slider TETAP memakai dataset() penelitian.
# ---------------------------------------------------------------------
@st.cache_data(ttl=300, show_spinner=False)
def _dashboard() -> tuple[pd.DataFrame, SumberDashboard]:
    from components.akun import klien_admin  # impor lokal: hindari impor melingkar
    konfigurasi, _ = klien_admin()
    unduh = None
    if konfigurasi is not None:
        klien, bucket = konfigurasi
        unduh = lambda path: klien.unduh(bucket, path)  # noqa: E731
    return muat_data_dashboard(unduh, dataset())


def sumber_dashboard() -> SumberDashboard:
    return _dashboard()[1]


def kunci_dashboard() -> str:
    s = sumber_dashboard()
    return s.versi.id if s.versi else "penelitian"


def label_sumber_dashboard() -> str:
    return label_sumber(sumber_dashboard(), tanggal_terakhir(), en=inggris())


def tanggal_terakhir_dashboard() -> pd.Timestamp:
    return _dashboard()[0]["tanggal"].max()


@st.cache_data(show_spinner=False)
def _kondisi(stasiun: str, kunci: str) -> pd.Series:
    return kondisi_terakhir(_dashboard()[0], stasiun)


@st.cache_data(show_spinner=False)
def _prediksi_aktual(stasiun: str, kunci: str) -> pd.DataFrame:
    return prediksi_7_hari(model(), _kondisi(stasiun, kunci))


def kondisi(stasiun: str) -> pd.Series:
    """Baris fitur hari terakhir data Dashboard untuk satu stasiun."""
    return _kondisi(stasiun, kunci_dashboard())


def prediksi_aktual(stasiun: str) -> pd.DataFrame:
    """Prediksi t+1..t+7 dari kondisi terakhir data Dashboard (Mode Prediksi Aktual)."""
    return _prediksi_aktual(stasiun, kunci_dashboard())


def segarkan_dashboard() -> None:
    """Dipanggil setelah admin mengganti versi aktif: semua pengguna memuat ulang data Dashboard."""
    _dashboard.clear()


@st.cache_data(show_spinner=False)
def rentang_fitur() -> pd.DataFrame:
    """Nilai min & maks tiap fitur di seluruh dataset (batas slider)."""
    return dataset()[FITUR].agg(["min", "max"]).T


@st.cache_data(show_spinner=False)
def periode_uji() -> tuple[pd.Timestamp, pd.Timestamp, int]:
    uji, batas = data_evaluasi(dataset())
    return batas, uji["tanggal"].max(), len(uji)


@st.cache_data(show_spinner=False)
def data_uji() -> pd.DataFrame:
    """Data uji (replikasi split training), tanpa prediksi; prediksi dihitung saat tombol Prediksi diklik."""
    uji, _ = data_evaluasi(dataset())
    return uji


def prediksi_baris_uji(baris: pd.Series) -> pd.Series:
    """Satu baris data uji + kolom pred_h1..pred_h7."""
    pred = prediksi_batch(model(), baris.to_frame().T).iloc[0]
    return pd.concat([baris, pred])


@st.cache_data(show_spinner=False)
def prediksi_uji_panjang() -> pd.DataFrame:
    """Seluruh prediksi data uji, satu baris per (stasiun, tanggal acuan, horizon). Dihitung sekali saat diminta."""
    uji = data_uji()
    return bentuk_panjang(pd.concat([uji, prediksi_batch(model(), uji)], axis=1))


@st.cache_data(show_spinner=False)
def hasil_evaluasi() -> dict:
    with open(EVAL_PATH, encoding="utf-8") as f:
        return json.load(f)


@st.cache_data(show_spinner=False)
def feature_importance(horizon: int = 1) -> pd.Series:
    """Importance (gain, bawaan xgboost) model horizon tertentu, urut menurun."""
    m = model()[horizon]["model"]
    return pd.Series(m.feature_importances_, index=FITUR).sort_values(ascending=False)


@st.cache_data(show_spinner=False)
def hasil_skenario() -> dict:
    with open(SKENARIO_PATH, encoding="utf-8") as f:
        return json.load(f)


@st.cache_data(show_spinner=False)
def rentang_tanggal() -> tuple[pd.Timestamp, pd.Timestamp]:
    t = dataset()["tanggal"]
    return t.min(), t.max()


@st.cache_data(show_spinner=False)
def nilai_spasial() -> pd.DataFrame:
    """Kepadatan & luas RTH per stasiun per tahun (nilai pertama tiap tahun, seperti cek di training)."""
    d = dataset()
    return (d.groupby(["stasiun", d["tanggal"].dt.year])[["kepadatan_penduduk_jiwa_km2", "luas_rth_km2"]]
            .first().rename_axis(["stasiun", "tahun"]).reset_index())


@st.cache_data(show_spinner=False)
def template_unggah() -> bytes:
    return buat_template(dataset_mentah())


@st.cache_data(show_spinner=False)
def titik_rth() -> pd.DataFrame:
    """Titik RTH yang lokasinya terverifikasi (presisi objek/manual) dari data/rth_koordinat.csv.

    File dihasilkan sekali oleh scripts/geocode_rth.py; jika belum ada, peta tampil tanpa titik RTH.
    """
    if not RTH_KOORDINAT_PATH.exists():
        return pd.DataFrame(columns=["kecamatan", "kelurahan", "nama_rth", "jenis_rth", "luas_m2", "lat", "lon", "presisi"])
    d = pd.read_csv(RTH_KOORDINAT_PATH, encoding="utf-8-sig")
    return d[d["presisi"].isin(["objek", "manual"])].dropna(subset=["lat", "lon"]).reset_index(drop=True)
