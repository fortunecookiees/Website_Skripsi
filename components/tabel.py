"""Tabel HTML bergaya desain (kelas .tbl)."""
import math

import pandas as pd
import streamlit as st

from core.config import STASIUN, kategori_ispu

from .bahasa import kategori, label_fitur, t
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
    st.html(f'<table class="tbl"><tr><th>{t("Stasiun", "Station")}</th><th>{t("Kecamatan", "District")}</th>'
            f'<th class="num">t+1</th><th>{t("Kategori", "Category")}</th></tr>{"".join(baris)}</table>')


def _selisih(d: int) -> str:
    return f"+{d}" if d > 0 else (f"−{-d}" if d < 0 else "0")


def tabel_perbandingan_mode(aktual: pd.DataFrame, simulasi: pd.DataFrame) -> None:
    """Tabel horizon | aktual | simulasi | selisih (nilai ISPU bulat)."""
    baris = []
    for h, a, s in zip(aktual["horizon"], aktual["pm25"], simulasi["pm25"]):
        na, ns = kategori_ispu(a)["nilai"], kategori_ispu(s)["nilai"]
        baris.append(f'<tr><td>t+{int(h)}</td><td class="num">{na}</td><td class="num">{ns}</td>'
                     f'<td class="num">{_selisih(ns - na)}</td></tr>')
    st.html(f'<table class="tbl"><tr><th>Horizon</th><th class="num">{t("Aktual", "Actual")}</th>'
            f'<th class="num">{t("Simulasi", "Simulation")}</th><th class="num">{t("Selisih", "Difference")}</th>'
            f'</tr>{"".join(baris)}</table>')


def ringkasan_selisih(aktual: pd.DataFrame, simulasi: pd.DataFrame) -> str:
    """Kalimat ringkas besar pergeseran simulasi terhadap aktual."""
    d = [kategori_ispu(s)["nilai"] - kategori_ispu(a)["nilai"] for a, s in zip(aktual["pm25"], simulasi["pm25"])]
    if not any(d):
        return t("Tidak ada horizon yang berubah dibanding mode aktual.",
                 "No horizon changed compared with actual mode.")
    i = max(range(len(d)), key=lambda j: abs(d[j]))
    rata = sum(abs(x) for x in d) / len(d)
    return t(f"Rata-rata pergeseran {angka(rata, 1)} poin per horizon; terbesar pada t+{i + 1} "
             f"({_selisih(d[i])} poin).",
             f"Average shift of {angka(rata, 1)} points per horizon; largest at t+{i + 1} "
             f"({_selisih(d[i])} points).")


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
    st.html(f'<table class="tbl"><tr><th>{t("Stasiun", "Station")}</th><th>{t("Kecamatan", "District")}</th>'
            f'<th>{t("Data terakhir", "Latest data")}</th><th class="num">t+1</th>'
            f'<th>{t("Kategori", "Category")}</th><th class="num">t+7</th></tr>{"".join(baris)}</table>')


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
                nilai = f'<span class="diisi">{t("data tidak tersedia", "data not available")}</span>'
            else:
                nilai = tampil(f, v)
                if not spasial and not rentang.loc[f, "min"] <= v <= rentang.loc[f, "max"]:
                    nilai += (f' <span class="luar" title="{t("di luar rentang dataset", "outside the dataset range")}">'
                              f'⚠ {t("di luar rentang", "out of range")}</span>')
            kelas = ' class="spRow"' if spasial else ""
            isi.append(f'<tr{kelas}><td>{label_fitur(f)[0]}</td><td class="num">{nilai}</td></tr>')
    st.html(f'<table class="tbl kondisi">{"".join(isi)}</table>')


def nilai_turunan(f: str, v: float) -> str:
    if f == "bulan":
        return BULAN[int(v) - 1]
    if f == "hari":
        return HARI[int(v)]
    return angka(v, 1 if f == "pm25_roll3" else 0) + " ISPU"


def tabel_rata_bulanan(tabel: pd.DataFrame) -> None:
    """Rata-rata PM2.5 bulanan (baris) per stasiun (kolom); sel diwarnai lembut sesuai kategori ISPU."""
    kepala = "".join(f'<th class="num">{s.split()[0]}</th>' for s in tabel.columns)
    isi = []
    for periode, baris in tabel.iterrows():
        sel = []
        for v in baris:
            if pd.isna(v):
                sel.append('<td class="num heat">–</td>')
                continue
            k = kategori_ispu(v)
            sel.append(f'<td class="num heat" style="background:{k["bg"]};color:{k["warna_teks"]}" '
                       f'title="{kategori(k["kategori"])}">{k["nilai"]}</td>')
        isi.append(f"<tr><td>{BULAN[periode.month - 1][:3]} {periode.year}</td>{''.join(sel)}</tr>")
    st.html(f'<table class="tbl heatTbl"><tr><th>{t("Bulan", "Month")}</th>{kepala}</tr>{"".join(isi)}</table>')
