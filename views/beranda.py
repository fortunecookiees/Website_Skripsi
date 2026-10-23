"""Halaman Beranda (landing page) — hero, ringkasan prediksi t+1 lima stasiun, dan pintasan fitur.

Ringkasan memakai fungsi & cache yang sama dengan Mode Aktual Dashboard (components/sumber_data.py),
termasuk versi data admin bila aktif. Penjelasan detail tetap di halaman Information.
"""
from base64 import b64encode
from html import escape

import streamlit as st

from components import akun
from core.teks import terjemah
from components.bahasa import t
from components.format import tanggal_panjang, tanggal_pendek
from components.kartu import chip
from components.logo import NAMA, hiasan_uri, judul_skripsi, logo_svg, tagline
from components.tema import label
from core.config import STASIUN, kategori_ispu

# (path, ikon, (nama ID, nama EN), (deskripsi ID, deskripsi EN))
KARTU_FITUR = [
    ("views/dashboard.py", "space_dashboard", ("Dashboard", "Dashboard"),
     ("Prediksi PM2.5 tujuh hari ke depan per stasiun, mode simulasi, dan peta lokasi SPKU.",
      "Seven-day PM2.5 forecast per station, simulation mode, and a map of SPKU locations.")),
    ("views/historis.py", "monitoring", ("Data Historis", "Historical Data"),
     ("Jelajahi indeks ISPU PM2.5 harian dari dataset penelitian dengan filter dan grafik tren.",
      "Explore the daily PM2.5 ISPU index of the research dataset with filters and trend charts.")),
    ("views/evaluation.py", "fact_check", ("Evaluation", "Evaluation"),
     ("Bandingkan prediksi model dengan nilai aktual dan lihat kinerja model pada data uji.",
      "Compare model predictions with actual values and review model performance on test data.")),
    ("views/unggah.py", "upload_file", ("Unggah Data", "Upload Data"),
     ("Unggah data harian terbaru untuk mendapat prediksi 7 hari dari data Anda sendiri.",
      "Upload your latest daily data to get a 7-day forecast from your own data.")),
]


def hero() -> None:
    with st.container(key="hero_beranda"):
        st.html(f'<img class="heroMotif" src="{hiasan_uri("#FFFFFF")}" alt="">'
                f'<div class="heroIsi"><div class="heroLogo">{logo_svg(56)}</div><div>'
                f'<div class="heroNama">{NAMA}</div><div class="heroTag">{tagline()}</div></div></div>'
                f'<p class="heroDesk heroJudul">{judul_skripsi()}</p>')
        c1, c2, _ = st.columns([1, 1.25, 2.6], gap="small")
        with c1, st.container(key="cta_prediksi"):
            st.page_link("views/dashboard.py", label=t("Lihat Prediksi", "View Forecast"), icon=":material/arrow_forward:")
        with c2, st.container(key="cta_info"):
            st.page_link("views/information.py", label=t("Pelajari Lebih Lanjut", "Learn More"), icon=":material/info:")


def _garis(nilai: list[int]) -> str:
    """Garis kecil prediksi 7 hari (nilai yang sama dengan grafik Dashboard), tanpa sumbu."""
    w, h, p = 180, 30, 3  # kira-kira selebar kartu agar titik tidak lonjong
    lo, hi = min(nilai), max(nilai)
    rentang = max(hi - lo, 1)
    xs = [p + i * (w - 2 * p) / (len(nilai) - 1) for i in range(len(nilai))]
    ys = [h - p - (v - lo) / rentang * (h - 2 * p) for v in nilai]
    titik = " ".join(f"{x:.1f},{y:.1f}" for x, y in zip(xs, ys))
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" preserveAspectRatio="none">'
           f'<polyline points="{titik}" fill="none" stroke="#648ba6" stroke-width="1.5" stroke-linejoin="round" '
           f'vector-effect="non-scaling-stroke"/><circle cx="{xs[0]:.1f}" cy="{ys[0]:.1f}" r="3" fill="#347653"/></svg>')
    # st.html membuang tag <svg> mentah, jadi disisipkan sebagai gambar (data URI) seperti logo
    return f'<img class="bsGaris" src="data:image/svg+xml;base64,{b64encode(svg.encode()).decode()}" alt="">'


def ringkasan_besok() -> None:
    label(t("Prediksi t+1 dari Kondisi Data Terakhir", "t+1 Forecast from the Latest Data"))
    try:
        from components import sumber_data as sd  # memuat model & dataset (sama dengan Dashboard Mode Aktual)
        sumber = sd.sumber_dashboard()
        pred = {s: sd.prediksi_aktual(s) for s in STASIUN}
        terakhir = sd.tanggal_terakhir_dashboard()
        teks_sumber = sd.label_sumber_dashboard()
    except Exception:  # noqa: BLE001 — halaman tetap tampil walau data/model gagal dimuat
        st.html('<div class="banner"><span class="dot"></span><span><b class="h">'
                + t("Ringkasan prediksi belum dapat dimuat", "The forecast summary could not be loaded") + '</b>'
                + t("Data atau model gagal dimuat. Coba muat ulang halaman, atau buka Dashboard.",
                    "The data or model failed to load. Try reloading the page, or open the Dashboard.")
                + '</span></div>')
        return

    kelas = "srcAdmin" if sumber.versi else "srcRiset"
    st.html(f'<div class="sumberData {kelas}"><span class="dot"></span><b>{t("Kondisi terakhir:", "Latest condition:")}</b> '
            f'{tanggal_panjang(terakhir)} · {escape(teks_sumber)}</div>')
    if sumber.peringatan:
        st.html(f'<div class="banner"><span class="dot"></span><span>{escape(terjemah(sumber.peringatan))}</span></div>')

    kartu = []
    for nama, info in STASIUN.items():
        p = pred[nama]
        k = kategori_ispu(p["pm25"].iloc[0])
        nilai7 = [kategori_ispu(v)["nilai"] for v in p["pm25"]]
        kode, lokasi = nama.split()[0], " ".join(nama.split()[1:])
        kartu.append(f'<div class="bStasiun"><div class="bsAtas"><span class="bsKode">{kode}'
                     f'</span>{chip(p["pm25"].iloc[0])}</div><div class="bsNama">{lokasi}</div>'
                     f'<div class="bsKec">{t("Kec.", "District")} {info["kecamatan"]}</div>'
                     f'<div class="bsNilai" style="color:{k["warna_teks"]}">{k["nilai"]}<span>ISPU</span></div>'
                     f'<div class="bsTren">{_garis(nilai7)}<span>{t("7 hari", "7 days")}: {min(nilai7)}–{max(nilai7)}</span>'
                     '</div></div>')
    t1 = next(iter(pred.values()))["tanggal"].iloc[0]
    t7 = next(iter(pred.values()))["tanggal"].iloc[-1]
    st.html(f'<div class="bRingkas">{"".join(kartu)}</div>'
            f'<div class="note">'
            + t(f"Prediksi untuk {tanggal_panjang(t1)} (t+1), satu hari setelah data terakhir, bukan kondisi hari ini; "
                f"garis kecil menunjukkan perkiraan t+1 sampai t+7 ({tanggal_pendek(t1)} – {tanggal_pendek(t7)}). "
                "Rincian, mode simulasi, dan peta tersedia di Dashboard.",
                f"Forecast for {tanggal_panjang(t1)} (t+1), one day after the latest data, not today's condition; "
                f"the small line shows the t+1 to t+7 forecast ({tanggal_pendek(t1)} – {tanggal_pendek(t7)}). "
                "Details, simulation mode, and the map are available on the Dashboard.")
            + '</div>')


def kartu_fitur() -> None:
    label(t("Fitur Aplikasi", "App Features"))
    tamu = akun.pengguna_aktif() is None
    kolom = st.columns(len(KARTU_FITUR), gap="medium")
    for kol, (path, ikon, nama_, desk_) in zip(kolom, KARTU_FITUR):
        nama, desk = t(*nama_), t(*desk_)
        catatan = (f'<span class="fNote">{t("perlu masuk", "sign-in required")}</span>'
                   if tamu and path == "views/unggah.py" else "")
        with kol, st.container(key=f"fitur_{ikon}"):
            st.html(f'<div class="fIkon"><span class="material-symbols-rounded">{ikon}</span></div>'
                    f'<div class="fJudul">{nama}{catatan}</div><div class="fDesk">{desk}</div>')
            st.page_link(path, label=t(f"Buka {nama}", f"Open {nama}"), icon=":material/arrow_forward:")


hero()
ringkasan_besok()
kartu_fitur()
