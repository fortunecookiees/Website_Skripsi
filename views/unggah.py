"""Halaman Unggah Data — prediksi 7 hari dari data terbaru yang diunggah pengguna, plus validasi
prediksi vs aktual jika file cukup panjang (hanya selama sesi)."""
import pandas as pd
import streamlit as st

from components import akun, riwayat
from components import sumber_data as sd
from components.format import tanggal_panjang, tanggal_pendek
from components.grafik import grafik_7_hari, grafik_sekitar_acuan
from components.kartu import angka_besar, chip, judul_kartu, kotak_7_horizon, teks_perubahan, teks_puncak
from components.panel_variabel import nilai_tampil
from components.pilih_tanggal import pilih_tanggal
from components.tabel import nilai_turunan, tabel_kondisi, tabel_status_unggah
from components.tabel_evaluasi import (CATATAN_DIISI, legend_sekitar_acuan, strip_metrik_acuan,
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
    st.html('<div class="infoBox"><span class="dot"></span><span>Data yang diunggah <b>hanya dipakai selama sesi '
            'ini</b> di memori aplikasi. Data tidak disimpan dan tidak menimpa dataset maupun model aplikasi '
            '(folder <code>data/</code> dan <code>models/</code>). Menutup atau memuat ulang halaman akan '
            'menghapusnya.</span></div>')
    kiri, kanan = st.columns(2, gap="medium")
    with kiri, st.container(key="card_unggah_template"):
        st.html(judul_kartu("Langkah 1 · Unduh Template", "Excel")
                + f'<div class="langkah">Isi template dengan data harian terbaru. Ketentuan:<ul>'
                f"<li>Kolom: <code>tanggal</code>, <code>stasiun</code>, 6 polutan (indeks ISPU), dan 7 meteorologi.</li>"
                f"<li>Minimal <b>{MIN_HARI} hari berturut-turut</b> per stasiun; boleh sebagian stasiun saja.</li>"
                "<li>PM2.5 wajib terisi pada 4 hari terakhir; meteorologi wajib pada hari terakhir; polutan lain "
                "boleh kosong.</li>"
                "<li>Kepadatan penduduk &amp; luas RTH tidak perlu diisi.</li>"
                f"<li>Untuk tab <b>Validasi</b> (prediksi vs aktual), unggah minimal <b>{MIN_HARI_VALIDASI} hari "
                "berturut-turut</b>.</li></ul></div>")
        st.download_button("Unduh template (.xlsx)", sd.template_unggah(), file_name="template_unggah_pm25.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                           key="unduh_template")
    with kanan, st.container(key="card_unggah_file"):
        st.html(judul_kartu("Langkah 2 · Unggah File", ".xlsx / .csv")
                + '<div class="langkah">Prediksi dihitung dari tanggal terakhir di file untuk setiap stasiun. '
                'CSV boleh memakai pemisah koma atau titik koma dan desimal koma.</div>')
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
        st.html(judul_kartu(f"Kondisi {tanggal_panjang(baris['tanggal'])}", "dari file unggahan"))
        tabel_kondisi(baris, sd.rentang_fitur(), [
            ("Variabel spasial · otomatis dari dataset", FITUR_SPASIAL, True),
            ("Meteorologi", FITUR_METEOROLOGI, False),
            ("Polutan udara", ["pm25"] + [f for f in FITUR_POLUTAN if f != "pm25"], False),
            ("Turunan · dihitung otomatis", FITUR_TURUNAN, False),
        ], _tampil)
    with kanan:
        with st.container(key="card_unggah_prediksi"):
            st.html(judul_kartu("Prediksi Besok", tanggal_panjang(t1["tanggal"]))
                    + angka_besar(t1["pm25"]) + chip(t1["pm25"])
                    + f'<div class="meta">{teks_perubahan(t1["pm25"], baris["pm25"])}</div>')
            grafik_7_hari(prediksi, key=f"grafik_unggah_{kunci}")
            st.html(f'<div class="note">{teks_puncak(prediksi)}</div>')
        with st.container(key="card_unggah_status"):
            st.html(judul_kartu("Stasiun yang Diunggah", f"{len(daftar)} stasiun"))
            tabel_status_unggah(hasil.prediksi, stasiun)
            st.download_button("Unduh hasil prediksi (.csv)", hasil_ke_csv(hasil.prediksi),
                               file_name="prediksi_pm25_unggahan.csv", mime="text/csv", key="unduh_hasil")

    kotak_7_horizon(prediksi)


def _teks_dilewati(n: int) -> str:
    return (f"{n} tanggal acuan dilewati karena data meteorologi pada tanggal tersebut tidak lengkap "
            "(sama dengan aturan meteorologi hari terakhir wajib lengkap).")


def tampil_validasi(hasil, kunci: str) -> None:
    """Prediksi vs aktual dari tanggal acuan di dalam file (data unggahan dianggap seluruhnya data uji)."""
    val = hasil.validasi
    daftar = [s for s in hasil.kondisi if s in set(val["stasiun"])]
    if not daftar:
        rincian = []
        for s, n in hasil.hari.items():
            alasan = (_teks_dilewati(hasil.dilewati_meteo[s]) if s in hasil.dilewati_meteo
                      else f"butuh minimal {MIN_HARI_VALIDASI} hari.")
            rincian.append(f"{s}: {n} hari di file — {alasan}")
        st.html(f'<div class="infoBox"><span class="dot"></span><span><b>Validasi belum tersedia: butuh minimal '
                f'{MIN_HARI_VALIDASI} hari berturut-turut untuk validasi</b> ({MIN_HARI} hari untuk lag + 7 hari '
                f'nilai aktual) pada setidaknya satu stasiun.{_daftar(rincian)}</span></div>')
        return

    st.html('<div class="note" style="margin:0 0 12px">Prediksi dihitung dari tanggal acuan di dalam file lalu '
            'dibandingkan dengan PM2.5 aktual t+1 … t+7 yang juga ada di file. Hanya tanggal yang data '
            'lag, nilai aktual 7 hari ke depan, dan meteorologinya lengkap yang dapat dipilih.</div>')
    label("Pilih Stasiun")
    pilihan = st.pills("Stasiun validasi", daftar, default=daftar[0], key=f"val_stasiun_{kunci}",
                       label_visibility="collapsed")
    stasiun = pilihan or daftar[0]
    val_st = val[val["stasiun"] == stasiun].set_index("tanggal", drop=False)
    if stasiun in hasil.dilewati_meteo:
        st.html(f'<div class="note" style="margin:-4px 0 10px">{_teks_dilewati(hasil.dilewati_meteo[stasiun])}</div>')

    label("Tanggal Acuan")
    acuan, kolom_hint = pilih_tanggal(list(val_st.index), prefix="val")
    baris = val_st.loc[acuan]
    k = kategori_ispu(baris["pm25"])
    diisi = "" if baris["pm25_asli"] else " (data diisi)"
    kolom_hint.html(f'<div class="stepHint">PM2.5 aktual hari acuan: <b>{k["nilai"]} ISPU</b>{diisi} · '
                    f'{k["kategori"]}</div>')

    with st.container(key="card_val_tabel"):
        st.html(judul_kartu("Prediksi vs Aktual — 7 Horizon", "dari file unggahan"))
        tabel_prediksi_vs_aktual(baris)
        st.html(strip_metrik_acuan(metrik_acuan(baris)))
        if not all(baris[f"target_h{h}_asli"] for h in HORIZONS):
            st.html(f'<div class="note">{CATATAN_DIISI}</div>')

    label("Grafik PM2.5 di Sekitar Tanggal Acuan")
    data = hasil.data
    sekitar = data[(data["stasiun"] == stasiun)
                   & data["tanggal"].between(acuan - pd.Timedelta(days=JENDELA_HARI),
                                             acuan + pd.Timedelta(days=JENDELA_HARI))].dropna(subset=["pm25"])
    prediksi = pd.DataFrame({"tanggal": [acuan + pd.Timedelta(days=h) for h in HORIZONS],
                             "pm25": [baris[f"pred_h{h}"] for h in HORIZONS]})
    with st.container(key="card_val_grafik"):
        grafik_sekitar_acuan(sekitar, acuan, prediksi, key=f"grafik_val_{kunci}")
        st.html(legend_sekitar_acuan(sekitar["pm25_asli"].all()))

    label("Ringkasan Seluruh Tanggal Acuan")
    with st.container(key="card_val_ringkasan"):
        st.html(judul_kartu(f"MAE &amp; RMSE per Horizon · {stasiun}",
                            f"{len(val_st)} tanggal acuan, {tanggal_pendek(val_st.index.min(), tahun=True)} – "
                            f"{tanggal_pendek(val_st.index.max(), tahun=True)}"))
        tabel_ringkasan_validasi(ringkasan_horizon(val_st))
        st.html('<div class="note">Kolom jumlah tanggal acuan menghitung nilai aktual asli saja; nilai aktual '
                'berupa data diisi tidak masuk perhitungan. Metrik ini hanya menggambarkan data pada file unggahan '
                'dan tidak menggantikan metrik data uji penelitian di halaman Evaluation.</div>')


judul("Unggah Data", "Prediksi PM2.5 tujuh hari ke depan dari data terbaru yang Anda unggah")
akun.wajib_masuk("views/unggah.py", "Unggah Data")
berkas = langkah_unggah()
if berkas is None:
    st.stop()

try:
    mentah = baca_file(berkas.getvalue(), berkas.name)
except ValueError as e:
    st.html(f'<div class="errBox"><b class="h">File tidak dapat dibaca</b>{e}</div>')
    st.stop()

hasil = proses(mentah, sd.model(), sd.dataset(), sd.rentang_fitur())
if hasil.error:
    st.html(f'<div class="errBox"><b class="h">Data belum dapat diproses — perbaiki {len(hasil.error)} masalah '
            f'berikut lalu unggah ulang</b>{_daftar(hasil.error)}</div>')
    st.stop()
if hasil.peringatan:
    st.html(f'<div class="banner"><span class="dot"></span><span><b class="h">Peringatan</b>'
            f'{_daftar(hasil.peringatan)}</span></div>')
if hasil.info:
    st.html(f'<div class="note" style="margin:-6px 0 14px">{" ".join(hasil.info)}</div>')

riwayat.catat(berkas.file_id, berkas.name, berkas.size, hasil)  # ringkasan saja, hanya di memori sesi
n_val = hasil.validasi["tanggal"].nunique() if len(hasil.validasi) else 0
tab_prediksi, tab_validasi = st.tabs(["Hasil Prediksi", f"Validasi · {n_val} tanggal" if n_val else "Validasi"])
with tab_prediksi:
    tampil_hasil(hasil, berkas.file_id)
with tab_validasi:
    tampil_validasi(hasil, berkas.file_id)
