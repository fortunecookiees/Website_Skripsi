"""Elemen kartu: judul kartu, angka besar, chip/tag kategori ISPU, kotak 7 horizon."""
import pandas as pd
import streamlit as st

from core.config import kategori_ispu

from .format import tanggal_pendek

SARAN_KESEHATAN = {
    "Baik": "Kualitas udara baik dan aman untuk beraktivitas di luar ruangan.",
    "Sedang": "Kelompok sensitif disarankan mengurangi aktivitas luar ruangan yang lama.",
    "Tidak Sehat": "Kelompok sensitif sebaiknya menghindari aktivitas luar ruangan; "
                   "masyarakat umum disarankan mengurangi aktivitas fisik berat di luar ruangan.",
    "Sangat Tidak Sehat": "Hindari aktivitas di luar ruangan dan gunakan masker bila harus keluar.",
    "Berbahaya": "Semua orang disarankan tetap berada di dalam ruangan.",
}


def judul_kartu(teks: str, keterangan: str = "") -> str:
    em = f"<em>{keterangan}</em>" if keterangan else ""
    return f'<div class="cardTitle">{teks} {em}</div>'


def chip(nilai: float) -> str:
    k = kategori_ispu(nilai)
    return f'<span class="chip" style="background:{k["bg"]};color:{k["warna_teks"]}">{k["kategori"]}</span>'


def tag(nilai: float) -> str:
    k = kategori_ispu(nilai)
    return f'<span class="tag" style="background:{k["bg"]};color:{k["warna_teks"]}">{k["kategori"]}</span>'


def angka_besar(nilai: float) -> str:
    k = kategori_ispu(nilai)
    return f'<div class="big"><span class="n" style="color:{k["warna_teks"]}">{k["nilai"]}</span><span class="u">ISPU</span></div>'


def teks_perubahan(pred_t1: float, pm25_hari_ini: float) -> str:
    """Kalimat 'Naik/Turun X poin dari hari terakhir (Y).' + saran kesehatan kategori t+1."""
    k = kategori_ispu(pred_t1)
    hari_ini = kategori_ispu(pm25_hari_ini)["nilai"]
    selisih = k["nilai"] - hari_ini
    if selisih > 0:
        arah = f"Naik {selisih} poin dari hari terakhir ({hari_ini})."
    elif selisih < 0:
        arah = f"Turun {-selisih} poin dari hari terakhir ({hari_ini})."
    else:
        arah = f"Sama dengan hari terakhir ({hari_ini})."
    return f"{arah} {SARAN_KESEHATAN[k['kategori']]}"


def teks_puncak(prediksi: pd.DataFrame) -> str:
    """Kalimat puncak prediksi 7 hari, dibandingkan dengan kategori t+1."""
    nilai = [kategori_ispu(v)["nilai"] for v in prediksi["pm25"]]
    i = max(range(len(nilai)), key=nilai.__getitem__)  # puncak pertama jika ada nilai sama
    r = prediksi.iloc[i]
    k_puncak, k_t1 = kategori_ispu(r["pm25"]), kategori_ispu(prediksi["pm25"].iloc[0])
    awal = f"Puncak diperkirakan pada t+{int(r['horizon'])} ({tanggal_pendek(r['tanggal'])}) dengan {k_puncak['nilai']} ISPU"
    if i == 0:
        return f"{awal}, kemudian menurun pada hari-hari berikutnya."
    if k_puncak["kategori"] != k_t1["kategori"]:
        return f"{awal}, melewati ambang kategori {k_puncak['kategori']}."
    return f"{awal}, masih dalam kategori {k_puncak['kategori']}."


def kotak_7_horizon(prediksi: pd.DataFrame) -> None:
    kotak = []
    for _, r in prediksi.iterrows():
        k = kategori_ispu(r["pm25"])
        nama = "Tdk Sehat" if k["kategori"] == "Tidak Sehat" else k["kategori"]
        kotak.append(
            f'<div class="hbox"><div class="d">t+{int(r["horizon"])}</div>'
            f'<div class="dt">{tanggal_pendek(r["tanggal"])}</div>'
            f'<div class="n" style="color:{k["warna_teks"]}">{k["nilai"]}</div>'
            f'<div class="k" style="background:{k["bg"]};color:{k["warna_teks"]}">{nama}</div></div>'
        )
    st.html(f'<div class="h7">{"".join(kotak)}</div>')
