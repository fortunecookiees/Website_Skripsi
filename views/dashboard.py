"""Halaman Dashboard — Mode Prediksi Aktual (L10.1) & Mode Simulasi (L10.2)."""
import math
from datetime import datetime
from zoneinfo import ZoneInfo
from html import escape

import streamlit as st

from components import sumber_data as sd
from core.teks import terjemah
from components.bahasa import t
from components.format import tanggal_panjang
from components.grafik import grafik_7_hari
from components.kartu import (angka_besar, banner_simulasi, chip, judul_kartu, panel_prediksi, panel_simulasi,
                              teks_bandingkan, teks_perubahan, teks_puncak, teks_simulasi)
from components.panel_variabel import daftar_perubahan, panel_variabel, reset_slider, samakan_aktif
from components.peta import peta_stasiun
from components.tabel import ringkasan_selisih, tabel_perbandingan_mode, tabel_status_stasiun
from components.tema import judul, label
from core.config import STASIUN
from core.inference import prediksi_7_hari
from core.simulasi import samakan_riwayat_pm25

MODE_AKTUAL, MODE_SIMULASI = "aktual", "simulasi"  # nilai tetap; label mengikuti bahasa
NAMA_MODE = {MODE_AKTUAL: ("Mode Aktual", "Actual Mode"), MODE_SIMULASI: ("Mode Simulasi", "Simulation Mode")}
SUBJUDUL = {
    MODE_AKTUAL: ("Prediksi indeks ISPU PM2.5 satu sampai tujuh hari ke depan per stasiun",
                  "PM2.5 ISPU index forecast one to seven days ahead per station"),
    MODE_SIMULASI: ("Simulasi pengaruh perubahan variabel terhadap hasil prediksi",
                    "Simulate how changing variables affects the forecast"),
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
            st.html(judul_kartu(t("Kondisi", "Conditions on") + f" {tanggal_panjang(baris['tanggal'])}", t("terkunci", "locked")))
            panel_variabel(baris, sd.rentang_fitur(), terkunci=True, prefix=f"aktual_{stasiun}")
    with kanan:
        with st.container(key="card_prediksi"):
            st.html(judul_kartu(t("Prediksi Besok", "Next-Day Forecast"), tanggal_panjang(t1["tanggal"]))
                    + angka_besar(t1["pm25"]) + chip(t1["pm25"])
                    + f'<div class="meta">{teks_perubahan(t1["pm25"], baris["pm25"])}</div>')
            grafik_7_hari(prediksi, key="grafik_aktual")
            st.html(f'<div class="note">{teks_puncak(prediksi)}</div>')
        with st.container(key="card_status"):
            st.html(judul_kartu(t("Status Seluruh Stasiun", "All Stations"), t("prediksi t+1", "t+1 forecast")))
            tabel_status_stasiun(pred_t1, stasiun)

    st.html(panel_prediksi(t("Hasil Prediksi", "Forecast Results"), f"{stasiun} · {sd.label_sumber_dashboard()}",
                           t("MODE AKTUAL", "ACTUAL MODE"),
                           f"PM2.5 {tanggal_panjang(baris['tanggal'])} " + t("(kondisi terakhir data)",
                                                                             "(latest data condition)"),
                           baris["pm25"], prediksi,
                           t("Prediksi dihitung dari kondisi terakhir data, bukan kondisi hari ini.",
                             "The forecast is computed from the latest data condition, not today's condition."),
                           tanggal=True))
    label(t("Peta Stasiun Pemantauan — Prediksi t+1", "Monitoring Station Map — t+1 Forecast"))
    with st.container(key="card_peta"):
        peta_stasiun(pred_t1, luas_rth, key="peta_aktual", titik_rth=sd.titik_rth())


def _sama(a: dict, b: dict) -> bool:
    """Bandingkan nilai slider; NaN (data tidak tersedia) dianggap sama dengan NaN."""
    return a.keys() == b.keys() and all(
        (math.isnan(a[k]) and math.isnan(b[k])) or a[k] == b[k] for k in a)


def _kembalikan(baris, rentang, prefix: str, kunci_hasil: str) -> None:
    reset_slider(baris, rentang, prefix)
    st.session_state.pop(kunci_hasil, None)


def mode_simulasi(stasiun: str) -> None:
    baris = sd.kondisi(stasiun)
    rentang = sd.rentang_fitur()
    aktual = sd.prediksi_aktual(stasiun)
    prefix = f"sim_{stasiun}"
    kunci_hasil = f"sim_hasil_{stasiun}_{sd.kunci_dashboard()}"  # (nilai slider, hasil 7 hari, waktu klik)

    banner_simulasi()
    kiri, kanan = st.columns([1.15, 1], gap="medium")
    with kiri:
        with st.container(key="card_variabel"):
            st.html(judul_kartu(t("Atur Nilai Variabel", "Set Variable Values"), t("dapat digeser", "adjustable")))
            nilai = panel_variabel(baris, rentang, terkunci=False, prefix=prefix)
            c_prediksi, c_reset = st.columns([1, 1.6])
            klik = c_prediksi.button(t("Prediksi", "Predict"), type="primary", key="prediksi_simulasi", width="stretch")
            c_reset.button(t("Kembalikan ke nilai aktual", "Reset to actual values"), on_click=_kembalikan,
                           args=(baris, rentang, prefix, kunci_hasil), key="reset_simulasi")

    # model hanya dijalankan saat tombol Prediksi diklik; menggeser slider tidak memicu prediksi
    samakan = samakan_aktif(prefix, nilai["pm25"])
    if klik:
        # bulan & hari tetap dari kondisi aktual; lag/rolling PM2.5 ikut data historis kecuali toggle riwayat menyala
        fitur_sim = baris.copy()
        for f, v in nilai.items():
            fitur_sim[f] = v
        if samakan:
            fitur_sim = samakan_riwayat_pm25(fitur_sim, nilai["pm25"])
        with st.spinner(t("Menghitung prediksi…", "Computing forecast…")):
            dijalankan = datetime.now(ZoneInfo("Asia/Jakarta")).strftime("%d-%m-%Y, %H.%M WIB")
            st.session_state[kunci_hasil] = (dict(nilai), prediksi_7_hari(sd.model(), fitur_sim), dijalankan,
                                             samakan)

    if kunci_hasil not in st.session_state:
        with kanan, st.container(key="card_prediksi"):
            st.html(judul_kartu(t("Hasil Simulasi", "Simulation Result"), t("belum dihitung", "not computed yet"))
                    + '<div class="simKosong">' + t(
                        "Slider dimulai dari nilai terendah pada dataset. Geser nilai variabel di panel kiri, lalu "
                        "klik <b>Prediksi</b> untuk melihat hasil simulasi 7 hari ke depan dan perbandingannya dengan "
                        "mode aktual. Tombol <i>Kembalikan ke nilai aktual</i> mengisi semua slider dengan kondisi "
                        "terakhir.",
                        "Sliders start at the lowest value in the dataset. Move the variables in the left panel, then "
                        "click <b>Predict</b> to see the 7-day simulation and how it compares with actual mode. "
                        "<i>Reset to actual values</i> fills every slider with the latest conditions.") + '</div>')
        return

    nilai_dipakai, simulasi, *sisa = st.session_state[kunci_hasil]
    dijalankan = sisa[0] if sisa else None
    samakan_dipakai = sisa[1] if len(sisa) > 1 else False
    perubahan = daftar_perubahan(baris, nilai_dipakai)
    if samakan_dipakai:
        perubahan.append(t("PM2.5 tiga hari sebelumnya disamakan dengan nilai hari ini",
                            "PM2.5 of the previous three days set to today's value"))
    t1 = simulasi.iloc[0]
    with kanan:
        if not _sama(nilai, nilai_dipakai) or samakan != samakan_dipakai:
            st.html('<div class="banner"><span class="dot"></span><span>' + t(
                "Nilai variabel sudah diubah sejak prediksi terakhir. Klik <b>Prediksi</b> untuk memperbarui hasil "
                "di bawah.", "Variable values changed since the last forecast. Click <b>Predict</b> to update the "
                "results below.") + '</span></div>')
        with st.container(key="card_prediksi"):
            st.html(judul_kartu(t("Hasil Simulasi", "Simulation Result"), tanggal_panjang(t1["tanggal"]))
                    + angka_besar(t1["pm25"]) + chip(t1["pm25"])
                    + f'<div class="meta">{teks_simulasi(t1["pm25"], aktual["pm25"].iloc[0], perubahan)}</div>')
            grafik_7_hari(simulasi, key="grafik_simulasi")
            st.html(f'<div class="note">{teks_bandingkan(aktual, simulasi)}</div>')
        with st.container(key="card_banding"):
            st.html(judul_kartu(t("Perbandingan Mode", "Mode Comparison"), t("aktual vs simulasi", "actual vs simulation")))
            tabel_perbandingan_mode(aktual, simulasi)
            st.html(f'<div class="note">{ringkasan_selisih(aktual, simulasi)}</div>')

    st.html(panel_simulasi(stasiun, nilai_dipakai["pm25"], simulasi, dijalankan))


# --- halaman ------------------------------------------------------------
if st.session_state.get("pil_mode") not in NAMA_MODE:  # nilai lama dari sesi sebelum pilihan bahasa
    st.session_state.pop("pil_mode", None)
judul(t("Prediksi PM2.5", "PM2.5 Forecast"), t(*SUBJUDUL[st.session_state.get("pil_mode") or MODE_AKTUAL]))
sumber = sd.sumber_dashboard()
kelas = "srcAdmin" if sumber.versi else "srcRiset"
st.html(f'<div class="sumberData {kelas}"><span class="dot"></span><b>{t("Sumber data:", "Data source:")}</b> '
        f'{escape(sd.label_sumber_dashboard())}</div>')
if sumber.peringatan:
    st.html(f'<div class="banner"><span class="dot"></span><span>{escape(terjemah(sumber.peringatan))}</span></div>')

with st.container(key="pemilih"):
    k_stasiun, k_mode = st.columns([3, 1.15], gap="medium")
    with k_stasiun:
        label(t("Pilih Stasiun", "Choose Station"), 1)
        pilihan = st.pills("Pilih Stasiun", daftar_stasiun, default=daftar_stasiun[0],
                           key="pil_stasiun", label_visibility="collapsed")
    with k_mode:
        label(t("Pilih Mode", "Choose Mode"), 2)
        mode = st.segmented_control("Mode", [MODE_AKTUAL, MODE_SIMULASI], default=MODE_AKTUAL,
                                    format_func=lambda m: t(*NAMA_MODE[m]),
                                    key="pil_mode", label_visibility="collapsed") or MODE_AKTUAL
stasiun = pilihan or st.session_state.get("stasiun_terakhir", daftar_stasiun[0])  # pills tidak boleh kosong
st.session_state["stasiun_terakhir"] = stasiun

if mode == MODE_SIMULASI:
    mode_simulasi(stasiun)
else:
    mode_aktual(stasiun)
