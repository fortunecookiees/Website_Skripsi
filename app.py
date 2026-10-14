"""Entry point aplikasi NafasKota — Prediksi PM2.5 DKI Jakarta.

Jalankan:  streamlit run app.py
"""
from pathlib import Path

import streamlit as st

from components import akun
from components.logo import NAMA, TAGLINE, logo_svg
from components.format import tanggal_panjang, tanggal_pendek
from components.sumber_data import periode_uji, rentang_tanggal, sumber_dashboard, tanggal_terakhir_dashboard
from components.tema import pasang_css

st.set_page_config(page_title=f"{NAMA} · {TAGLINE}", page_icon=str(Path(__file__).with_name("assets") / "logo.png"),
                   layout="wide", initial_sidebar_state="auto")  # auto: terbuka di desktop, tertutup di HP
pasang_css()

IKON = {"Dashboard": "space_dashboard", "Data Historis": "monitoring", "Evaluation": "fact_check",
        "Unggah Data": "upload_file", "Information": "info", "Masuk / Daftar": "login", "Profil": "account_circle",
        "Admin": "admin_panel_settings"}


def _halaman(path: str, judul_hal: str, **kw) -> st.Page:
    return st.Page(path, title=judul_hal, icon=f":material/{IKON[judul_hal]}:", **kw)


MENU = [
    _halaman("views/dashboard.py", "Dashboard", default=True),
    _halaman("views/historis.py", "Data Historis", url_path="historis"),
    _halaman("views/evaluation.py", "Evaluation", url_path="evaluation"),
    _halaman("views/unggah.py", "Unggah Data", url_path="unggah"),
    _halaman("views/information.py", "Information", url_path="information"),
]
HALAMAN_AKUN = _halaman(akun.HALAMAN_AKUN, "Masuk / Daftar", url_path="akun")
HALAMAN_PROFIL = _halaman("views/profil.py", "Profil", url_path="profil")
HALAMAN_ADMIN = _halaman("views/admin.py", "Admin", url_path="admin")
PERLU_MASUK = {"Unggah Data"}
aktif = st.navigation(MENU + [HALAMAN_AKUN, HALAMAN_PROFIL, HALAMAN_ADMIN], position="hidden")


def _catatan_sidebar(judul: str) -> str:
    if judul == "Evaluation":
        mulai, akhir, n = periode_uji()
        return (f"Periode uji<br><b>{tanggal_pendek(mulai)} – {tanggal_pendek(akhir, tahun=True)}</b><br><br>"
                f"{n} baris data uji<br>5 stasiun")
    if judul == "Unggah Data":
        return ("Data unggahan<br><b>hanya selama sesi</b><br><br>Tidak disimpan &amp; tidak menimpa "
                "dataset atau model")
    if judul == "Masuk / Daftar":
        return "Akun hanya diperlukan<br>untuk fitur <b>Unggah Data</b>"
    if judul == "Admin":
        return "Khusus peran <b>admin</b><br><br>Data Dashboard saja;<br>Evaluation &amp; Data Historis<br>tetap dataset penelitian"
    if judul == "Profil":
        return "Data akun dikelola<br><b>Supabase Auth</b><br><br>Riwayat unggahan<br>hanya selama sesi"
    if judul == "Data Historis":
        mulai, akhir = rentang_tanggal()
        return (f"Rentang dataset<br><b>{tanggal_pendek(mulai, tahun=True)} – {tanggal_pendek(akhir, tahun=True)}</b>"
                "<br><br>5 stasiun SPKU<br>indeks ISPU harian")
    if judul == "Information":
        return "Sumber data<br>Satu Data Jakarta<br>BPS DKI Jakarta<br>Open-Meteo"
    sumber = "data diperbarui admin" if sumber_dashboard().versi else "dataset penelitian"
    return (f"Data terakhir<br><b>{tanggal_panjang(tanggal_terakhir_dashboard())}</b><br>{sumber}<br><br>"
            "Model XGBoost + PSO<br>7 horizon (t+1 … t+7)")


with st.sidebar:
    st.html(f'<div class="brand">{logo_svg(30)}<div class="brandText">{NAMA}<span>{TAGLINE}</span></div></div>')
    sesi = akun.pengguna_aktif()
    # menu Admin hanya tampilan; halaman Admin sendiri memeriksa ulang role di server
    for hal in MENU + [HALAMAN_PROFIL if sesi else HALAMAN_AKUN] + ([HALAMAN_ADMIN] if akun.admin_untuk_menu() else []):
        if hal.title == aktif.title:
            st.html(f'<div class="navActive"><span class="material-symbols-rounded">{IKON[hal.title]}</span>'
                    f'{hal.title}</div>')
        else:
            st.page_link(hal, label=hal.title, icon=hal.icon)
        if hal.title in PERLU_MASUK and sesi is None:
            st.html('<div class="navNote">perlu masuk</div>')
    st.html(f'<div class="sideFoot">{_catatan_sidebar(aktif.title)}</div>')
    akun.blok_sidebar()

if pesan := st.session_state.pop(akun.KUNCI_PESAN, None):
    st.toast(pesan)

aktif.run()

st.html(f'<div class="footer"><span class="footBrand">{logo_svg(16, latar="#1C1C1C", garis="#FFFFFF")}<b>{NAMA}</b> · {TAGLINE}</span>'
        '<span>XGBoost + PSO · 5 SPKU · t+1 … t+7</span>'
        '<span>Fortuna · 535230144 · Teknik Informatika, Universitas Tarumanagara</span></div>')
