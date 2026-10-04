"""Entry point aplikasi Prediksi PM2.5 DKI Jakarta.

Jalankan:  streamlit run app.py
"""
import streamlit as st

from components.format import tanggal_panjang, tanggal_pendek
from components.sumber_data import periode_uji, tanggal_terakhir
from components.tema import pasang_css

st.set_page_config(page_title="Prediksi PM2.5 DKI Jakarta", page_icon="🌫️",
                   layout="wide", initial_sidebar_state="expanded")
pasang_css()

HALAMAN = [
    st.Page("views/dashboard.py", title="Dashboard", default=True),
    st.Page("views/evaluation.py", title="Evaluation", url_path="evaluation"),
    st.Page("views/information.py", title="Information", url_path="information"),
]
aktif = st.navigation(HALAMAN, position="hidden")


def _catatan_sidebar(judul: str) -> str:
    if judul == "Evaluation":
        mulai, akhir, n = periode_uji()
        return (f"Periode uji<br><b>{tanggal_pendek(mulai)} – {tanggal_pendek(akhir, tahun=True)}</b><br><br>"
                f"{n} baris data uji<br>5 stasiun")
    return (f"Data terakhir<br><b>{tanggal_panjang(tanggal_terakhir())}</b><br><br>"
            "Model XGBoost + PSO<br>7 horizon (t+1 … t+7)")


with st.sidebar:
    st.html('<div class="brand"><div class="brandMark"></div>'
            '<div class="brandText">Prediksi PM2.5<span>DKI Jakarta</span></div></div>')
    for hal in HALAMAN:
        if hal.title == aktif.title:
            st.html(f'<div class="navActive">{hal.title}</div>')
        else:
            st.page_link(hal, label=hal.title)
    st.html(f'<div class="sideFoot">{_catatan_sidebar(aktif.title)}</div>')

aktif.run()
