"""Entry point aplikasi Prediksi PM2.5 DKI Jakarta.

Jalankan:  streamlit run app.py
"""
import streamlit as st

from components import akun
from components.format import tanggal_panjang, tanggal_pendek
from components.sumber_data import periode_uji, tanggal_terakhir
from components.tema import pasang_css

st.set_page_config(page_title="Prediksi PM2.5 DKI Jakarta", page_icon="🌫️",
                   layout="wide", initial_sidebar_state="expanded")
pasang_css()

MENU = [
    st.Page("views/dashboard.py", title="Dashboard", default=True),
    st.Page("views/evaluation.py", title="Evaluation", url_path="evaluation"),
    st.Page("views/unggah.py", title="Unggah Data", url_path="unggah"),
    st.Page("views/information.py", title="Information", url_path="information"),
]
HALAMAN_AKUN = st.Page(akun.HALAMAN_AKUN, title="Masuk / Daftar", url_path="akun")
PERLU_MASUK = {"Unggah Data"}
aktif = st.navigation(MENU + [HALAMAN_AKUN], position="hidden")


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
    if judul == "Information":
        return "Sumber data<br>Satu Data Jakarta<br>BPS DKI Jakarta<br>Open-Meteo"
    return (f"Data terakhir<br><b>{tanggal_panjang(tanggal_terakhir())}</b><br><br>"
            "Model XGBoost + PSO<br>7 horizon (t+1 … t+7)")


with st.sidebar:
    st.html('<div class="brand"><div class="brandMark"></div>'
            '<div class="brandText">Prediksi PM2.5<span>DKI Jakarta</span></div></div>')
    sesi = akun.pengguna_aktif()
    for hal in MENU + ([] if sesi else [HALAMAN_AKUN]):
        if hal.title == aktif.title:
            st.html(f'<div class="navActive">{hal.title}</div>')
        else:
            st.page_link(hal, label=hal.title)
        if hal.title in PERLU_MASUK and sesi is None:
            st.html('<div class="navNote">perlu masuk</div>')
    st.html(f'<div class="sideFoot">{_catatan_sidebar(aktif.title)}</div>')
    akun.blok_sidebar()

if pesan := st.session_state.pop(akun.KUNCI_PESAN, None):
    st.toast(pesan)

aktif.run()
