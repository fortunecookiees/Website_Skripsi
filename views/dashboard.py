"""Halaman Dashboard — Mode Prediksi Aktual (L10.1). Mode Simulasi menyusul di tahap 4."""
import streamlit as st

from components import sumber_data as sd
from components.format import tanggal_panjang
from components.grafik import grafik_7_hari
from components.kartu import angka_besar, chip, judul_kartu, kotak_7_horizon, teks_perubahan, teks_puncak
from components.panel_variabel import panel_variabel
from components.peta import peta_stasiun
from components.tabel import tabel_status_stasiun
from components.tema import judul, label
from core.config import STASIUN

MODE_AKTUAL, MODE_SIMULASI = "Mode Aktual", "Mode Simulasi"
daftar_stasiun = list(STASIUN)

judul("Prediksi PM2.5", "Prediksi indeks ISPU PM2.5 satu sampai tujuh hari ke depan per stasiun")

# --- pilihan stasiun & mode (pills tidak boleh kosong) -----------------
label("Pilih Stasiun")
pilihan = st.pills("Pilih Stasiun", daftar_stasiun, default=daftar_stasiun[0],
                   key="pil_stasiun", label_visibility="collapsed")
stasiun = pilihan or st.session_state.get("stasiun_terakhir", daftar_stasiun[0])
st.session_state["stasiun_terakhir"] = stasiun

mode = st.segmented_control("Mode", [MODE_AKTUAL, MODE_SIMULASI], default=MODE_AKTUAL,
                            key="pil_mode", label_visibility="collapsed") or MODE_AKTUAL

if mode == MODE_SIMULASI:
    st.info("Mode Simulasi akan tersedia pada tahap berikutnya.")
    st.stop()

# --- data ---------------------------------------------------------------
baris = sd.kondisi(stasiun)
prediksi = sd.prediksi_aktual(stasiun)
pred_t1 = {s: sd.prediksi_aktual(s)["pm25"].iloc[0] for s in daftar_stasiun}
luas_rth = {s: sd.kondisi(s)["luas_rth_km2"] for s in daftar_stasiun}
t1 = prediksi.iloc[0]

# --- panel variabel | kartu prediksi + status ---------------------------
kiri, kanan = st.columns([1.15, 1], gap="medium")
with kiri:
    with st.container(key="card_variabel"):
        st.html(judul_kartu(f"Kondisi {tanggal_panjang(baris['tanggal'])}", "terkunci"))
        panel_variabel(baris, sd.rentang_fitur(), terkunci=True, prefix=f"aktual_{stasiun}")

with kanan:
    with st.container(key="card_prediksi"):
        st.html(judul_kartu("Prediksi Besok", tanggal_panjang(t1["tanggal"]))
                + angka_besar(t1["pm25"]) + chip(t1["pm25"])
                + f'<div class="meta">{teks_perubahan(t1["pm25"], baris["pm25"])}</div>')
        grafik_7_hari(prediksi, key="grafik_aktual")
        st.html(f'<div class="note">{teks_puncak(prediksi)}</div>')
    with st.container(key="card_status"):
        st.html(judul_kartu("Status Seluruh Stasiun", "prediksi t+1"))
        tabel_status_stasiun(pred_t1, stasiun)

# --- 7 horizon & peta ---------------------------------------------------
kotak_7_horizon(prediksi)

label("Peta Stasiun Pemantauan — Prediksi t+1")
with st.container(key="card_peta"):
    peta_stasiun(pred_t1, luas_rth, key="peta_aktual")
