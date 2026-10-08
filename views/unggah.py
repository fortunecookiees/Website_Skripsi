"""Halaman Unggah Data — prediksi 7 hari dari data terbaru yang diunggah pengguna (hanya selama sesi)."""
import streamlit as st

from components import akun
from components import sumber_data as sd
from components.format import tanggal_panjang
from components.grafik import grafik_7_hari
from components.kartu import angka_besar, chip, judul_kartu, kotak_7_horizon, teks_perubahan, teks_puncak
from components.panel_variabel import nilai_tampil
from components.tabel import nilai_turunan, tabel_kondisi, tabel_status_unggah
from components.tema import judul, label
from core.config import FITUR_METEOROLOGI, FITUR_POLUTAN, FITUR_SPASIAL, FITUR_TURUNAN
from core.unggah import MIN_HARI, baca_file, hasil_ke_csv, proses


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
                "<li>Kepadatan penduduk &amp; luas RTH tidak perlu diisi.</li></ul></div>")
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
    label("Hasil Prediksi")
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

tampil_hasil(hasil, berkas.file_id)
