"""Entry point aplikasi NafasKota — Prediksi PM2.5 DKI Jakarta.

Jalankan:  streamlit run app.py
"""
from datetime import date
from pathlib import Path

import streamlit as st

from components import akun
from components.bahasa import pemilih, t
from components.logo import NAMA, logo_svg, tagline
from components.format import tanggal_panjang, tanggal_pendek
from components.tema import pasang_css, tandai_halaman

st.set_page_config(page_title=f"{NAMA} · {tagline()}", page_icon=str(Path(__file__).with_name("assets") / "logo.png"),
                   layout="wide", initial_sidebar_state="auto")  # auto: terbuka di desktop, tertutup di HP
pasang_css()

# kunci halaman tetap (dipakai untuk logika); judul mengikuti bahasa aktif
HALAMAN = {  # kunci: (path, url_path, judul ID, judul EN, ikon)
    "beranda": ("views/beranda.py", None, "Beranda", "Home", "home"),
    "dashboard": ("views/dashboard.py", "dashboard", "Dashboard", "Dashboard", "space_dashboard"),
    "historis": ("views/historis.py", "historis", "Data Historis", "Historical Data", "monitoring"),
    "evaluation": ("views/evaluation.py", "evaluation", "Evaluation", "Evaluation", "fact_check"),
    "unggah": ("views/unggah.py", "unggah", "Unggah Data", "Upload Data", "upload_file"),
    "information": ("views/information.py", "information", "Information", "Information", "info"),
    "akun": (akun.HALAMAN_AKUN, "akun", "Masuk / Daftar", "Sign In / Register", "login"),
    "profil": ("views/profil.py", "profil", "Profil", "Profile", "account_circle"),
    "admin": ("views/admin.py", "admin", "Admin", "Admin", "admin_panel_settings"),
}
MENU_UTAMA = ["beranda", "dashboard", "historis", "evaluation", "unggah", "information"]
PERLU_MASUK = {"unggah"}


def _halaman(kunci: str) -> st.Page:
    path, url, judul_id, judul_en, ikon = HALAMAN[kunci]
    kw = {"default": True} if url is None else {"url_path": url}
    return st.Page(path, title=t(judul_id, judul_en), icon=f":material/{ikon}:", **kw)


PAGE = {k: _halaman(k) for k in HALAMAN}
aktif = st.navigation(list(PAGE.values()), position="hidden")
kunci_aktif = next(k for k, p in PAGE.items() if p.url_path == aktif.url_path)


def _catatan_sidebar(kunci: str) -> str:
    # impor di sini, bukan di atas: sumber_data memuat xgboost/model/dataset (bisa >10 detik saat start dingin),
    # jadi CSS, brand, dan menu sudah terkirim ke browser lebih dulu dan halaman tidak putih kosong
    from components.sumber_data import periode_uji, rentang_tanggal, sumber_dashboard, tanggal_terakhir_dashboard
    if kunci == "evaluation":
        mulai, akhir, n = periode_uji()
        return (t("Periode uji", "Test period") + f"<br><b>{tanggal_pendek(mulai)} – {tanggal_pendek(akhir, tahun=True)}"
                f"</b><br><br>{n} " + t("baris data uji<br>5 stasiun", "test rows<br>5 stations"))
    if kunci == "unggah":
        return t("Data unggahan<br><b>tidak disimpan</b><br><br>Hilang saat halaman<br>dimuat ulang",
                 "Uploaded data<br><b>is not stored</b><br><br>Cleared when the page<br>is reloaded")
    if kunci == "akun":
        return t("Akun hanya diperlukan<br>untuk fitur <b>Unggah Data</b>",
                 "An account is only needed<br>for <b>Upload Data</b>")
    if kunci == "admin":
        return t("Khusus peran <b>admin</b><br><br>Data Dashboard saja;<br>Evaluation &amp; Data Historis<br>tetap "
                 "dataset penelitian", "<b>Admin</b> role only<br><br>Dashboard data only;<br>Evaluation &amp; "
                 "Historical Data<br>keep the research dataset")
    if kunci == "profil":
        return t("Data akun dikelola<br><b>Supabase Auth</b><br><br>Riwayat unggahan<br>hanya selama sesi",
                 "Account data managed by<br><b>Supabase Auth</b><br><br>Upload history<br>kept for this session only")
    if kunci == "historis":
        mulai, akhir = rentang_tanggal()
        return (t("Rentang dataset", "Dataset range") + f"<br><b>{tanggal_pendek(mulai, tahun=True)} – "
                f"{tanggal_pendek(akhir, tahun=True)}</b><br><br>"
                + t("5 stasiun SPKU<br>indeks ISPU harian", "5 SPKU stations<br>daily ISPU index"))
    if kunci == "information":
        return t("Sumber data", "Data sources") + "<br>Satu Data Jakarta<br>BPS DKI Jakarta<br>Open-Meteo"
    sumber = (t("data diperbarui admin", "data updated by admin") if sumber_dashboard().versi
              else t("dataset penelitian", "research dataset"))
    return t("Data terakhir", "Latest data") + f"<br><b>{tanggal_panjang(tanggal_terakhir_dashboard())}</b><br>{sumber}"


with st.sidebar:
    st.html(f'<div class="brand">{logo_svg(30)}<div class="brandText">{NAMA}<span>{tagline()}</span></div></div>')
    pemilih()
    sesi = akun.pengguna_aktif()
    # menu Admin hanya tampilan; halaman Admin sendiri memeriksa ulang role di server
    menu = MENU_UTAMA + ["profil" if sesi else "akun"] + (["admin"] if akun.admin_untuk_menu() else [])
    for k in menu:
        hal = PAGE[k]
        if k == kunci_aktif:
            st.html(f'<div class="navActive"><span class="material-symbols-rounded">{HALAMAN[k][4]}</span>'
                    f'{hal.title}</div>')
        else:
            st.page_link(hal, label=hal.title, icon=hal.icon)
        if k in PERLU_MASUK and sesi is None:
            st.html(f'<div class="navNote">{t("perlu masuk", "sign-in required")}</div>')
    st.html(f'<div class="sideFoot">{_catatan_sidebar(kunci_aktif)}</div>')
    akun.blok_sidebar()

if pesan := st.session_state.pop(akun.KUNCI_PESAN, None):
    st.toast(pesan)

tandai_halaman(aktif.title, HALAMAN[kunci_aktif][4])
aktif.run()


st.html(f'<div class="footer"><div class="ftLogo">{logo_svg(28)}<div><b>{NAMA}</b><span>{tagline()}</span></div></div>'
        f'<div class="ftKanan">© {date.today().year} {NAMA} · Fortuna Arleo Sahara · 535230144<br>'
        + t("Teknik Informatika, Universitas Tarumanagara", "Informatics Engineering, Tarumanagara University")
        + f'</div><div class="ftWord" aria-hidden="true">{NAMA}</div></div>')
