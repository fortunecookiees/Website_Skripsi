"""Tabel HTML bergaya desain (kelas .tbl)."""
import math

import pandas as pd
import streamlit as st

from core.config import FITUR_TURUNAN, LABEL_FITUR, STASIUN, kategori_ispu

from .format import BULAN, HARI, angka, tanggal_pendek
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


def tabel_status_unggah(prediksi: pd.DataFrame, terpilih: str) -> None:
    """Ringkasan stasiun yang diunggah: tanggal dasar, t+1, kategori, t+7."""
    baris = []
    for st_nama, g in prediksi.groupby("stasiun", sort=False):
        t1, t7 = g["pm25"].iloc[0], g["pm25"].iloc[-1]
        kelas = ' class="sel"' if st_nama == terpilih else ""
        baris.append(f"<tr{kelas}><td>{st_nama.split()[0]}</td><td>{STASIUN[st_nama]['kecamatan']}</td>"
                     f"<td>{tanggal_pendek(g['tanggal_dasar'].iloc[0], tahun=True)}</td>"
                     f'<td class="num">{kategori_ispu(t1)["nilai"]}</td><td>{tag(t1)}</td>'
                     f'<td class="num">{kategori_ispu(t7)["nilai"]}</td></tr>')
    st.html('<table class="tbl"><tr><th>Stasiun</th><th>Kecamatan</th><th>Data terakhir</th><th class="num">t+1</th>'
            f'<th>Kategori</th><th class="num">t+7</th></tr>{"".join(baris)}</table>')


def tabel_kondisi(baris: pd.Series, rentang: pd.DataFrame, kelompok: list, tampil) -> None:
    """Nilai fitur hari terakhir (tanpa slider). Nilai di luar rentang dataset diberi tanda ⚠.

    `kelompok`: [(nama, [fitur], spasial?)]; `tampil(fitur, nilai)` -> teks nilai bersatuan.
    """
    isi = []
    for nama, daftar, spasial in kelompok:
        isi.append(f'<tr class="grpRow"><td colspan="2">{nama}</td></tr>')
        for f in daftar:
            v = baris[f]
            if v is None or (isinstance(v, float) and math.isnan(v)):
                nilai = '<span class="diisi">data tidak tersedia</span>'
            else:
                nilai = tampil(f, v)
                if not spasial and not rentang.loc[f, "min"] <= v <= rentang.loc[f, "max"]:
                    nilai += ' <span class="luar" title="di luar rentang dataset">⚠ di luar rentang</span>'
            kelas = ' class="spRow"' if spasial else ""
            isi.append(f'<tr{kelas}><td>{LABEL_FITUR[f][0]}</td><td class="num">{nilai}</td></tr>')
    st.html(f'<table class="tbl kondisi">{"".join(isi)}</table>')


def nilai_turunan(f: str, v: float) -> str:
    if f == "bulan":
        return BULAN[int(v) - 1]
    if f == "hari":
        return HARI[int(v)]
    return angka(v, 1 if f == "pm25_roll3" else 0) + " ISPU"
