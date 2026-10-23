"""Halaman Unggah Data — prediksi 7 hari dari data terbaru yang diunggah pengguna, plus validasi
prediksi vs aktual jika file cukup panjang (hanya selama sesi)."""
import pandas as pd
import streamlit as st

from components import akun, riwayat
from components import sumber_data as sd
from components.bahasa import kategori, t
from components.format import tanggal_panjang, tanggal_pendek
from components.grafik import grafik_7_hari, grafik_sekitar_acuan
from components.kartu import angka_besar, chip, judul_kartu, panel_prediksi, teks_perubahan, teks_puncak
from components.panel_variabel import nilai_tampil
from components.pilih_tanggal import pilih_tanggal
from components.tabel import nilai_turunan, tabel_kondisi, tabel_status_unggah
from components.tabel_evaluasi import (catatan_diisi, legend_sekitar_acuan, strip_metrik_acuan,
                                       tabel_prediksi_vs_aktual, tabel_ringkasan_validasi)
from components.tema import judul, label
from core.config import FITUR_METEOROLOGI, FITUR_POLUTAN, FITUR_SPASIAL, FITUR_TURUNAN, HORIZONS, kategori_ispu
from core.metrik import metrik_acuan, ringkasan_horizon
from core.unggah import MIN_HARI, MIN_HARI_VALIDASI, baca_file, hasil_ke_csv, proses

JENDELA_HARI = 7  # rentang grafik validasi: acuan ± 7 hari (sama dengan Evaluation)


def _tampil(fitur: str, nilai: float) -> str:
    return nilai_turunan(fitur, nilai) if fitur in FITUR_TURUNAN else nilai_tampil(fitur, nilai)


def _daftar(pesan: list[str]) -> str:
    return "<ul>" + "".join(f"<li>{p}</li>" for p in pesan) + "</ul>"


def langkah_unggah():
    kiri, kanan = st.columns(2, gap="medium")
    with kiri, st.container(key="card_unggah_template"):
        st.html(judul_kartu(t("Langkah 1 · Unduh Template", "Step 1 · Download Template"), "Excel")
                + '<div class="langkah">' + t(
                    "Isi template dengan data harian terbaru:<ul>"
                    "<li>Isi tanggal, nama stasiun, data polutan udara, dan data cuaca sesuai kolom di template.</li>"
                    f"<li>Isi minimal <b>{MIN_HARI} hari berturut-turut</b> untuk setiap stasiun. Boleh satu "
                    "stasiun saja.</li>"
                    f"<li>PM2.5 wajib diisi untuk {MIN_HARI} hari terakhir, dan data cuaca wajib diisi untuk hari "
                    "terakhir. Polutan lain boleh dikosongkan.</li>"
                    "<li>Kepadatan penduduk dan luas RTH tidak perlu diisi.</li>"
                    f"<li>Ingin membandingkan prediksi dengan nilai sebenarnya? Isi minimal <b>{MIN_HARI_VALIDASI} "
                    "hari berturut-turut</b>, lalu buka tab <b>Validasi</b>.</li></ul>",
                    "Fill in the template with the latest daily data:<ul>"
                    "<li>Enter the date, station name, air pollutant data, and weather data in the template "
                    "columns.</li>"
                    f"<li>Enter at least <b>{MIN_HARI} consecutive days</b> for each station. One station is "
                    "enough.</li>"
                    f"<li>PM2.5 is required for the last {MIN_HARI} days, and weather is required for the last day. "
                    "Other pollutants may be left empty.</li>"
                    "<li>Population density and green open space do not need to be filled in.</li>"
                    f"<li>Want to compare forecasts with real values? Enter at least <b>{MIN_HARI_VALIDASI} "
                    "consecutive days</b>, then open the <b>Validation</b> tab.</li></ul>") + "</div>")
        st.download_button(t("Unduh template (.xlsx)", "Download template (.xlsx)"), sd.template_unggah(), file_name="template_unggah_pm25.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                           key="unduh_template")
    with kanan, st.container(key="card_unggah_file"):
        st.html(judul_kartu(t("Langkah 2 · Unggah File", "Step 2 · Upload File"), ".xlsx / .csv")
                + '<div class="langkah">' + t("Prediksi dihitung mulai dari tanggal terakhir di file Anda, untuk "
                                              "setiap stasiun.",
                                              "Forecasts start from the last date in your file, for each station.")
                + '</div>')
        return st.file_uploader("Unggah file", type=["xlsx", "csv"], key="berkas_unggah",
                                label_visibility="collapsed")


def tampil_hasil(hasil, kunci: str) -> None:
    daftar = list(hasil.kondisi)
    pilihan = st.pills("Stasiun", daftar, default=daftar[0], key=f"unggah_stasiun_{kunci}",
                       label_visibility="collapsed")
    stasiun = pilihan or daftar[0]
    baris = hasil.kondisi[stasiun]
    prediksi = hasil.prediksi[hasil.prediksi["stasiun"] == stasiun].reset_index(drop=True)
    t1 = prediksi.iloc[0]

    kiri, kanan = st.columns([1.15, 1], gap="medium")
    with kiri, st.container(key="card_unggah_kondisi"):
        st.html(judul_kartu(t("Kondisi", "Conditions on") + f" {tanggal_panjang(baris['tanggal'])}",
                            t("dari file unggahan", "from the uploaded file")))
        tabel_kondisi(baris, sd.rentang_fitur(), [
            (t("Kepadatan penduduk & luas RTH · terisi otomatis",
               "Population density & green open space · filled automatically"), FITUR_SPASIAL, True),
            (t("Cuaca", "Weather"), FITUR_METEOROLOGI, False),
            (t("Polutan udara", "Air pollutants"), ["pm25"] + [f for f in FITUR_POLUTAN if f != "pm25"], False),
            (t("Dihitung otomatis dari data Anda", "Computed automatically from your data"), FITUR_TURUNAN, False),
        ], _tampil)
    with kanan:
        with st.container(key="card_unggah_prediksi"):
            st.html(judul_kartu(t("Prediksi Besok", "Next-Day Forecast"), tanggal_panjang(t1["tanggal"]))
                    + angka_besar(t1["pm25"]) + chip(t1["pm25"])
                    + f'<div class="meta">{teks_perubahan(t1["pm25"], baris["pm25"])}</div>')
            grafik_7_hari(prediksi, key=f"grafik_unggah_{kunci}")
            st.html(f'<div class="note">{teks_puncak(prediksi)}</div>')
        with st.container(key="card_unggah_status"):
            st.html(judul_kartu(t("Stasiun yang Diunggah", "Uploaded Stations"),
                                t(f"{len(daftar)} stasiun", f"{len(daftar)} stations")))
            tabel_status_unggah(hasil.prediksi, stasiun)
            st.download_button(t("Unduh hasil prediksi (.csv)", "Download forecast results (.csv)"), hasil_ke_csv(hasil.prediksi),
                               file_name="prediksi_pm25_unggahan.csv", mime="text/csv", key="unduh_hasil")

    st.html(panel_prediksi(t("Hasil Prediksi", "Forecast Results"),
                           f"{stasiun} · " + t("dari data terakhir di file Anda", "from the latest data in your file"),
                           t("DATA ANDA", "YOUR DATA"),
                           f"PM2.5 {tanggal_panjang(baris['tanggal'])} " + t("(tanggal terakhir di file)",
                                                                             "(last date in the file)"),
                           baris["pm25"], prediksi,
                           t("Prediksi dihitung dari data yang Anda unggah dan hanya disimpan selama sesi.",
                             "The forecast is computed from your uploaded data and kept for this session only."),
                           tanggal=True))


def _teks_dilewati(n: int) -> str:
    return t(f"{n} tanggal tidak bisa dipilih karena data cuacanya tidak lengkap.",
             f"{n} dates cannot be selected because their weather data is incomplete.")


def tampil_validasi(hasil, kunci: str) -> None:
    """Prediksi vs aktual dari tanggal acuan di dalam file (data unggahan dianggap seluruhnya data uji)."""
    val = hasil.validasi
    daftar = [s for s in hasil.kondisi if s in set(val["stasiun"])]
    if not daftar:
        rincian = []
        for s, n in hasil.hari.items():
            alasan = (_teks_dilewati(hasil.dilewati_meteo[s]) if s in hasil.dilewati_meteo
                      else t(f"perlu minimal {MIN_HARI_VALIDASI} hari.",
                             f"at least {MIN_HARI_VALIDASI} days are needed."))
            rincian.append(t(f"{s}: {n} hari di file — {alasan}", f"{s}: {n} days in the file — {alasan}"))
        st.html('<div class="infoBox"><span class="dot"></span><span>' + t(
            f"<b>Validasi belum tersedia.</b> Unggah minimal {MIN_HARI_VALIDASI} hari berturut-turut untuk "
            "setidaknya satu stasiun.",
            f"<b>Validation is not available yet.</b> Upload at least {MIN_HARI_VALIDASI} consecutive days for at "
            "least one station.") + f'{_daftar(rincian)}</span></div>')
        return

    st.html('<div class="note" style="margin:0 0 12px">' + t(
        "Pilih satu tanggal di dalam file. Prediksi 7 hari setelah tanggal itu dibandingkan dengan nilai PM2.5 "
        "sebenarnya yang ada di file Anda.",
        "Choose a date in the file. The 7-day forecast after that date is compared with the real PM2.5 values in "
        "your file.") + '</div>')
    label(t("Pilih Stasiun", "Choose Station"))
    pilihan = st.pills("Stasiun validasi", daftar, default=daftar[0], key=f"val_stasiun_{kunci}",
                       label_visibility="collapsed")
    stasiun = pilihan or daftar[0]
    val_st = val[val["stasiun"] == stasiun].set_index("tanggal", drop=False)
    if stasiun in hasil.dilewati_meteo:
        st.html(f'<div class="note" style="margin:-4px 0 10px">{_teks_dilewati(hasil.dilewati_meteo[stasiun])}</div>')

    label(t("Tanggal Acuan", "Reference Date"))
    acuan, kolom_hint = pilih_tanggal(list(val_st.index), prefix="val")
    baris = val_st.loc[acuan]
    k = kategori_ispu(baris["pm25"])
    diisi = "" if baris["pm25_asli"] else t(" (data diisi)", " (filled data)")
    kolom_hint.html(f'<div class="stepHint">{t("PM2.5 aktual hari acuan", "Actual PM2.5 on the reference date")}: '
                    f'<b>{k["nilai"]} ISPU</b>{diisi} · {kategori(k["kategori"])}</div>')

    data = hasil.data
    sekitar = data[(data["stasiun"] == stasiun)
                   & data["tanggal"].between(acuan - pd.Timedelta(days=JENDELA_HARI),
                                             acuan + pd.Timedelta(days=JENDELA_HARI))].dropna(subset=["pm25"])
    prediksi = pd.DataFrame({"tanggal": [acuan + pd.Timedelta(days=h) for h in HORIZONS],
                             "pm25": [baris[f"pred_h{h}"] for h in HORIZONS]})

    # kiri: tabel per horizon; kanan: grafik + ringkasan seluruh tanggal (tinggi kedua sisi disamakan lewat CSS)
    with st.container(key="baris_validasi"):
        kiri, kanan = st.columns([1.1, 1], gap="medium")
        with kiri, st.container(key="card_val_tabel"):
            st.html(judul_kartu(t("Prediksi vs Aktual — 7 Horizon", "Predicted vs Actual — 7 Horizons"),
                                t("dari file unggahan", "from the uploaded file")))
            tabel_prediksi_vs_aktual(baris)
            st.html(strip_metrik_acuan(metrik_acuan(baris)))
            if not all(baris[f"target_h{h}_asli"] for h in HORIZONS):
                st.html(f'<div class="note">{catatan_diisi()}</div>')
        with kanan:
            with st.container(key="card_val_grafik"):
                st.html(judul_kartu(t("Grafik PM2.5 di Sekitar Tanggal Acuan", "PM2.5 Around the Reference Date"),
                                    t(f"±{JENDELA_HARI} hari", f"±{JENDELA_HARI} days")))
                grafik_sekitar_acuan(sekitar, acuan, prediksi, key=f"grafik_val_{kunci}", tinggi=250)
                st.html(legend_sekitar_acuan(sekitar["pm25_asli"].all()))
            with st.container(key="card_val_ringkasan"):
                rentang = f"{tanggal_pendek(val_st.index.min())} – {tanggal_pendek(val_st.index.max(), tahun=True)}"
                st.html(judul_kartu(t("Ringkasan", "Summary") + f" · {stasiun}",
                                    t(f"{len(val_st)} tanggal acuan, {rentang}",
                                      f"{len(val_st)} reference dates, {rentang}")))
                tabel_ringkasan_validasi(ringkasan_horizon(val_st))
                st.html('<div class="note">' + t(
                    "MAE &amp; RMSE dari seluruh tanggal acuan di file Anda. Kinerja model pada data penelitian ada "
                    "di halaman Evaluation.",
                    "MAE &amp; RMSE over all reference dates in your file. Model performance on the research data "
                    "is on the Evaluation page.") + '</div>')


judul(t("Unggah Data", "Upload Data"), t("Prediksi PM2.5 tujuh hari ke depan dari data terbaru yang Anda unggah",
                                          "Seven-day PM2.5 forecast from the latest data you upload"))
akun.wajib_masuk("views/unggah.py", t("Unggah Data", "Upload Data"), [
    t("Mengunduh template dan mengisi data harian terbaru", "Download the template and fill in the latest daily data"),
    t("Mengunggah file Excel/CSV lalu memeriksa hasil validasinya", "Upload an Excel/CSV file and check its validation"),
    t("Melihat prediksi PM2.5 tujuh hari ke depan untuk tiap stasiun", "See the seven-day PM2.5 forecast per station"),
])
berkas = langkah_unggah()
if berkas is None:
    st.stop()

try:
    mentah = baca_file(berkas.getvalue(), berkas.name)
except ValueError as e:
    st.html(f'<div class="errBox"><b class="h">{t("File tidak dapat dibaca", "The file could not be read")}</b>'
            f'{e}</div>')
    st.stop()

hasil = proses(mentah, sd.model(), sd.dataset(), sd.rentang_fitur())
if hasil.error:
    n_err = len(hasil.error)
    st.html('<div class="errBox"><b class="h">' + t(
        f"Data belum dapat diproses — perbaiki {n_err} masalah berikut lalu unggah ulang",
        f"The data cannot be processed yet — fix the following {n_err} issues and upload again")
        + f'</b>{_daftar(hasil.error)}</div>')
    st.stop()
if hasil.peringatan:
    st.html(f'<div class="banner"><span class="dot"></span><span><b class="h">{t("Peringatan", "Warning")}</b>'
            f'{_daftar(hasil.peringatan)}</span></div>')
if hasil.info:
    st.html(f'<div class="note" style="margin:-6px 0 14px">{" ".join(hasil.info)}</div>')

riwayat.catat(berkas.file_id, berkas.name, berkas.size, hasil)  # ringkasan saja, hanya di memori sesi
n_val = hasil.validasi["tanggal"].nunique() if len(hasil.validasi) else 0
tab_prediksi, tab_validasi = st.tabs([t("Hasil Prediksi", "Forecast Results"),
                                     t(f"Validasi · {n_val} tanggal", f"Validation · {n_val} dates") if n_val
                                     else t("Validasi", "Validation")])
with tab_prediksi:
    tampil_hasil(hasil, berkas.file_id)
with tab_validasi:
    tampil_validasi(hasil, berkas.file_id)
