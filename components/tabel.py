"""Tabel HTML bergaya desain (kelas .tbl)."""
import pandas as pd
import streamlit as st

from core.config import STASIUN, kategori_ispu

from .format import angka
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


def _selisih(d: int) -> str:
    return f"+{d}" if d > 0 else (f"−{-d}" if d < 0 else "0")


def tabel_perbandingan_mode(aktual: pd.DataFrame, simulasi: pd.DataFrame) -> None:
    """Tabel horizon | aktual | simulasi | selisih (nilai ISPU bulat)."""
    baris = []
    for h, a, s in zip(aktual["horizon"], aktual["pm25"], simulasi["pm25"]):
        na, ns = kategori_ispu(a)["nilai"], kategori_ispu(s)["nilai"]
        baris.append(f'<tr><td>t+{int(h)}</td><td class="num">{na}</td><td class="num">{ns}</td>'
                     f'<td class="num">{_selisih(ns - na)}</td></tr>')
    st.html('<table class="tbl"><tr><th>Horizon</th><th class="num">Aktual</th><th class="num">Simulasi</th>'
            f'<th class="num">Selisih</th></tr>{"".join(baris)}</table>')


def ringkasan_selisih(aktual: pd.DataFrame, simulasi: pd.DataFrame) -> str:
    """Kalimat ringkas besar pergeseran simulasi terhadap aktual."""
    d = [kategori_ispu(s)["nilai"] - kategori_ispu(a)["nilai"] for a, s in zip(aktual["pm25"], simulasi["pm25"])]
    if not any(d):
        return "Tidak ada horizon yang berubah dibanding mode aktual."
    i = max(range(len(d)), key=lambda j: abs(d[j]))
    rata = sum(abs(x) for x in d) / len(d)
    return (f"Rata-rata pergeseran {angka(rata, 1)} poin per horizon; "
            f"terbesar pada t+{i + 1} ({_selisih(d[i])} poin).")
