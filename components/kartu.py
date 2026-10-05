"""Elemen kartu: judul kartu, angka besar, chip/tag kategori ISPU, kotak 7 horizon."""
import pandas as pd
import streamlit as st

from core.config import SARAN_ISPU_PM25, kategori_ispu

from .format import tanggal_pendek


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


def saran_kesehatan(nilai: float) -> str:
    """Rekomendasi PermenLHK P.14/2020 untuk PM2.5 sesuai kategori nilai."""
    sensitif, umum = SARAN_ISPU_PM25[kategori_ispu(nilai)["kategori"]]
    if sensitif is None:
        return f"{umum}."
    kecil = lambda t: t[0].lower() + t[1:]  # noqa: E731
    return f"Kelompok sensitif: {kecil(sensitif)}. Setiap orang: {kecil(umum)}."


def _selisih(baru: int, lama: int, acuan: str) -> str:
    d = baru - lama
    if d > 0:
        return f"Naik {d} poin dari {acuan} ({lama})"
    if d < 0:
        return f"Turun {-d} poin dari {acuan} ({lama})"
    return f"Sama dengan {acuan} ({lama})"


def teks_perubahan(pred_t1: float, pm25_hari_ini: float) -> str:
    """'Naik/Turun X poin dari hari terakhir (Y).' + saran kesehatan kategori t+1."""
    baru, lama = kategori_ispu(pred_t1)["nilai"], kategori_ispu(pm25_hari_ini)["nilai"]
    return f"{_selisih(baru, lama, 'hari terakhir')}. {saran_kesehatan(pred_t1)}"


def teks_puncak(prediksi: pd.DataFrame) -> str:
    """Kalimat puncak 7 hari. 'Melewati ambang' hanya jika kategori puncak berbeda dari t+1."""
    nilai = [kategori_ispu(v)["nilai"] for v in prediksi["pm25"]]
    i = max(range(len(nilai)), key=nilai.__getitem__)  # puncak pertama jika ada nilai sama
    r = prediksi.iloc[i]
    k_puncak, k_t1 = kategori_ispu(r["pm25"]), kategori_ispu(prediksi["pm25"].iloc[0])
    if i == 0:
        return (f"Nilai tertinggi ada pada t+1 ({k_t1['nilai']} ISPU); "
                "hari-hari berikutnya diperkirakan tidak melebihi nilai tersebut.")
    awal = f"Puncak diperkirakan pada t+{int(r['horizon'])} ({tanggal_pendek(r['tanggal'])}) dengan {k_puncak['nilai']} ISPU"
    if k_puncak["kategori"] != k_t1["kategori"]:
        return f"{awal}, melewati ambang kategori {k_puncak['kategori']}."
    return f"{awal}; selama 7 hari kategori tetap {k_t1['kategori']} seperti t+1."


def teks_simulasi(pred_sim_t1: float, pred_akt_t1: float, perubahan: list[str]) -> str:
    """Kalimat hasil simulasi t+1 dibanding mode aktual + daftar variabel yang diubah."""
    baru, lama = kategori_ispu(pred_sim_t1)["nilai"], kategori_ispu(pred_akt_t1)["nilai"]
    if not perubahan:
        return f"Sama dengan mode aktual ({lama}). Geser slider untuk mengubah nilai variabel."
    if len(perubahan) > 3:
        daftar = ", ".join(perubahan[:3]) + f", dan {len(perubahan) - 3} variabel lain diubah"
    elif len(perubahan) == 3:
        daftar = ", ".join(perubahan[:2]) + f", dan {perubahan[2]}"
    elif len(perubahan) == 2:
        daftar = f"{perubahan[0]} dan {perubahan[1]}"
    else:
        daftar = perubahan[0]
    if baru == lama:
        return f"Tetap sama dengan mode aktual ({lama}) meskipun {daftar}."
    return f"{_selisih(baru, lama, 'mode aktual')}, setelah {daftar}."


def teks_bandingkan(akt: pd.DataFrame, sim: pd.DataFrame, horizon=(1, 4, 7)) -> str:
    bagian = [f"t+{h} {kategori_ispu(akt['pm25'].iloc[h - 1])['nilai']} → "
              f"{kategori_ispu(sim['pm25'].iloc[h - 1])['nilai']}" for h in horizon]
    return "Perbandingan terhadap mode aktual: " + " · ".join(bagian)


def banner_simulasi() -> None:
    st.html('<div class="banner"><span class="dot"></span><span>Hasil pada mode simulasi '
            '<b>bukan prediksi kondisi sebenarnya</b>. Nilai variabel diatur oleh pengguna dan hanya '
            'digunakan untuk mengamati pengaruh perubahan terhadap keluaran model.</span></div>')


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
