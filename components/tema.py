"""Pemasangan CSS kustom dan elemen judul halaman."""
from pathlib import Path

import streamlit as st

from .logo import hiasan_uri

_CSS = Path(__file__).with_name("styles.css")
KUNCI_HALAMAN = "_halaman_aktif"  # (nama menu, ikon material) diisi app.py sebelum halaman dijalankan


def pasang_css() -> None:
    st.html(f"<style>{_CSS.read_text(encoding='utf-8')}</style>")


def tandai_halaman(nama: str, ikon: str) -> None:
    st.session_state[KUNCI_HALAMAN] = (nama, ikon)


def judul(teks: str, sub: str) -> None:
    """Header halaman berbentuk bar: ikon menu, jejak (NafasKota / menu), judul, dan subjudul."""
    nama, ikon = st.session_state.get(KUNCI_HALAMAN, (teks, "space_dashboard"))
    st.html(f'<div class="pageHead"><div class="phIkon"><span class="material-symbols-rounded">{ikon}</span></div>'
            f'<div class="phTeks"><div class="crumb">NafasKota<span>/</span>{nama}</div>'
            f'<h2 class="title">{teks}</h2><div class="subt">{sub}</div></div>'
            f'<img class="phDeko" src="{hiasan_uri()}" alt=""><img class="phDeko d2" src="{hiasan_uri()}" alt="">'
            '</div>')


def label(teks: str, nomor: int | None = None) -> None:
    """Label bagian; `nomor` opsional menampilkan penanda langkah (01, 02, …)."""
    langkah = f'<span class="step">{nomor:02d}</span>' if nomor else ""
    st.html(f'<div class="lbl">{langkah}{teks}</div>')
