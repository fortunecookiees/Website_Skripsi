"""Halaman Dashboard — Mode Prediksi Aktual (L10.1) & Mode Simulasi (L10.2)."""
import streamlit as st

from components import sumber_data as sd
from components.format import tanggal_panjang
from components.grafik import grafik_7_hari
from components.kartu import (angka_besar, banner_simulasi, chip, judul_kartu, kotak_7_horizon,
                              teks_bandingkan, teks_perubahan, teks_puncak, teks_simulasi)
from components.panel_variabel import daftar_perubahan, panel_variabel, reset_slider
from components.peta import peta_stasiun
from components.tabel import ringkasan_selisih, tabel_perbandingan_mode, tabel_status_stasiun
from components.tema import judul, label
from core.config import STASIUN
from core.inference import prediksi_7_hari

MODE_AKTUAL, MODE_SIMULASI = "Mode Aktual", "Mode Simulasi"
SUBJUDUL = {
    MODE_AKTUAL: "Prediksi indeks ISPU PM2.5 satu sampai tujuh hari ke depan per stasiun",
    MODE_SIMULASI: "Simulasi pengaruh perubahan variabel terhadap hasil prediksi",
}
daftar_stasiun = list(STASIUN)


def mode_aktual(stasiun: str) -> None:
    baris = sd.kondisi(stasiun)
    prediksi = sd.prediksi_aktual(stasiun)
    pred_t1 = {s: sd.prediksi_aktual(s)["pm25"].iloc[0] for s in daftar_stasiun}
    luas_rth = {s: sd.kondisi(s)["luas_rth_km2"] for s in daftar_stasiun}
    t1 = prediksi.iloc[0]

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

    kotak_7_horizon(prediksi)
    label("Peta Stasiun Pemantauan — Prediksi t+1")
    with st.container(key="card_peta"):
        peta_stasiun(pred_t1, luas_rth, key="peta_aktual")


def mode_simulasi(stasiun: str) -> None:
    baris = sd.kondisi(stasiun)
    rentang = sd.rentang_fitur()
    aktual = sd.prediksi_aktual(stasiun)
    prefix = f"sim_{stasiun}"

    banner_simulasi()
    kiri, kanan = st.columns([1.15, 1], gap="medium")
    with kiri:
        with st.container(key="card_variabel"):
            st.html(judul_kartu("Atur Nilai Variabel", "dapat digeser"))
            nilai = panel_variabel(baris, rentang, terkunci=False, prefix=prefix)
            st.button("Kembalikan ke nilai aktual", on_click=reset_slider,
                      args=(baris, rentang, prefix), key="reset_simulasi")

    # fitur turunan & tanggal tetap dari kondisi aktual; hanya 15 fitur slider yang diganti
    fitur_sim = baris.copy()
    for f, v in nilai.items():
        fitur_sim[f] = v
    simulasi = prediksi_7_hari(sd.model(), fitur_sim)
    t1 = simulasi.iloc[0]

    with kanan:
        with st.container(key="card_prediksi"):
            st.html(judul_kartu("Hasil Simulasi", tanggal_panjang(t1["tanggal"]))
                    + angka_besar(t1["pm25"]) + chip(t1["pm25"])
                    + f'<div class="meta">{teks_simulasi(t1["pm25"], aktual["pm25"].iloc[0], daftar_perubahan(baris, nilai))}</div>')
            grafik_7_hari(simulasi, key="grafik_simulasi")
            st.html(f'<div class="note">{teks_bandingkan(aktual, simulasi)}</div>')
        with st.container(key="card_banding"):
            st.html(judul_kartu("Perbandingan Mode", "aktual vs simulasi"))
            tabel_perbandingan_mode(aktual, simulasi)
            st.html(f'<div class="note">{ringkasan_selisih(aktual, simulasi)}</div>')

    kotak_7_horizon(simulasi)


# --- halaman ------------------------------------------------------------
judul("Prediksi PM2.5", SUBJUDUL[st.session_state.get("pil_mode") or MODE_AKTUAL])

label("Pilih Stasiun")
pilihan = st.pills("Pilih Stasiun", daftar_stasiun, default=daftar_stasiun[0],
                   key="pil_stasiun", label_visibility="collapsed")
stasiun = pilihan or st.session_state.get("stasiun_terakhir", daftar_stasiun[0])  # pills tidak boleh kosong
st.session_state["stasiun_terakhir"] = stasiun

mode = st.segmented_control("Mode", [MODE_AKTUAL, MODE_SIMULASI], default=MODE_AKTUAL,
                            key="pil_mode", label_visibility="collapsed") or MODE_AKTUAL

if mode == MODE_SIMULASI:
    mode_simulasi(stasiun)
else:
    mode_aktual(stasiun)
