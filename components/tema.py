"""Pemasangan CSS kustom dan elemen judul halaman."""
from pathlib import Path

import streamlit as st

_CSS = Path(__file__).with_name("styles.css")


def pasang_css() -> None:
    st.html(f"<style>{_CSS.read_text(encoding='utf-8')}</style>")


def judul(teks: str, sub: str) -> None:
    st.html(f'<h2 class="title">{teks}</h2><div class="subt">{sub}</div>')


def label(teks: str) -> None:
    st.html(f'<div class="lbl">{teks}</div>')
