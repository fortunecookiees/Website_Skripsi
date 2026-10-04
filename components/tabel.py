"""Tabel HTML bergaya desain (kelas .tbl)."""
import streamlit as st

from core.config import STASIUN, kategori_ispu

from .kartu import tag


def tabel_status_stasiun(pred_t1: dict[str, float], terpilih: str) -> None:
    """Tabel prediksi t+1 kelima stasiun. `pred_t1` = {stasiun: nilai}."""
    baris = []
    for st_nama, nilai in pred_t1.items():
        kode = st_nama.split()[0]
        kelas = ' class="sel"' if st_nama == terpilih else ""
        baris.append(f"<tr{kelas}><td>{kode}</td><td>{STASIUN[st_nama]['kecamatan']}</td>"
                     f'<td class="num">{kategori_ispu(nilai)["nilai"]}</td><td>{tag(nilai)}</td></tr>')
    st.html('<table class="tbl"><tr><th>Stasiun</th><th>Kecamatan</th><th class="num">t+1</th>'
            f'<th>Kategori</th></tr>{"".join(baris)}</table>')
