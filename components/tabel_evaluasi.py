"""Tabel halaman Evaluation: prediksi vs aktual, metrik, metode optimasi, feature importance."""
import pandas as pd
import streamlit as st

from core.config import (FITUR_METEOROLOGI, FITUR_POLUTAN, FITUR_SPASIAL, HORIZONS,
                         LABEL_FITUR, kategori_ispu)

from .format import angka, tanggal_pendek
from .kartu import tag

KELOMPOK_FITUR = {**{f: "Spasial" for f in FITUR_SPASIAL}, **{f: "Meteorologi" for f in FITUR_METEOROLOGI},
                  **{f: "Polutan" for f in FITUR_POLUTAN}}
NAMA_IMPORTANCE = {"pm25": "PM2.5 hari ini", "pm10": "PM10"}


def _tanda(d: int) -> str:
    return f"+{d}" if d > 0 else (f"−{-d}" if d < 0 else "0")


def tabel_prediksi_vs_aktual(baris: pd.Series) -> None:
    """Satu baris data uji -> 7 baris horizon. Nilai aktual hasil ffill ditandai & tidak dihitung kesalahannya."""
    isi = []
    for h in HORIZONS:
        pred, akt, asli = baris[f"pred_h{h}"], baris[f"target_h{h}"], bool(baris[f"target_h{h}_asli"])
        np_, na = kategori_ispu(pred)["nilai"], kategori_ispu(akt)["nilai"]
        if asli and akt != 0:
            err = f"{angka(abs(pred - akt) / akt * 100, 1)} %"
        else:
            err = '<span class="diisi">tidak dihitung</span>'
        ket = "" if asli else ' <span class="diisi">data diisi</span>'
        isi.append(f"<tr><td>t+{h}</td><td>{tanggal_pendek(baris['tanggal'] + pd.Timedelta(days=h), tahun=True)}</td>"
                   f'<td class="num">{np_}</td><td class="num">{na}{ket}</td><td class="num">{_tanda(np_ - na)}</td>'
                   f'<td class="num">{err}</td><td>{tag(akt)}</td></tr>')
    st.html('<table class="tbl"><tr><th>Horizon</th><th>Tanggal</th><th class="num">Prediksi</th>'
            '<th class="num">Aktual</th><th class="num">Selisih</th><th class="num">Kesalahan</th>'
            f'<th>Kategori Aktual</th></tr>{"".join(isi)}</table>')


def tabel_metrik(ev: dict) -> str:
    """Tabel metrik XGBoost+PSO + RMSE persistensi. Mengembalikan catatan perbandingan dengan persistensi."""
    isi, menang = [], []
    for h in map(str, HORIZONS):
        m, rp = ev["pso"][h], ev["persistence"][h]["RMSE"]
        if m["RMSE"] < rp:
            menang.append(int(h))
        isi.append(f'<tr><td>t+{h}</td><td class="num">{angka(m["MAE"], 1)}</td><td class="num">{angka(m["RMSE"], 1)}</td>'
                   f'<td class="num">{angka(m["MAPE"], 1)} %</td><td class="num">{angka(m["R2"], 3)}</td>'
                   f'<td class="num">{angka(rp, 1)}</td></tr>')
    st.html('<table class="tbl"><tr><th>Horizon</th><th class="num">MAE</th><th class="num">RMSE</th>'
            '<th class="num">MAPE</th><th class="num">R²</th><th class="num">RMSE Persistensi</th></tr>'
            f'{"".join(isi)}</table>')
    if len(menang) == len(HORIZONS):
        return "Nilai RMSE model lebih kecil daripada <i>baseline</i> persistensi pada seluruh horizon."
    kalah = ", ".join(f"t+{h}" for h in HORIZONS if h not in menang)
    return (f"Nilai RMSE model lebih kecil daripada <i>baseline</i> persistensi pada {len(menang)} dari "
            f"{len(HORIZONS)} horizon (tidak lebih kecil pada {kalah}).")


def tabel_optimasi(ev: dict) -> None:
    """RMSE uji: hyperparameter bawaan vs Random Search vs PSO; nilai terkecil per horizon ditebalkan."""
    kolom = [("default", "Hyperparameter Bawaan"), ("random_search", "Random Search"), ("pso", "PSO")]
    isi = []
    for h in map(str, HORIZONS):
        nilai = {k: ev[k][h]["RMSE"] for k, _ in kolom}
        terbaik = min(nilai, key=nilai.get)
        sel = "".join(f'<td class="num{" best" if k == terbaik else ""}">{angka(nilai[k], 3)}</td>' for k, _ in kolom)
        isi.append(f"<tr><td>t+{h}</td>{sel}</tr>")
    kepala = "".join(f'<th class="num">{judul}</th>' for _, judul in kolom)
    st.html(f'<table class="tbl"><tr><th>Horizon</th>{kepala}</tr>{"".join(isi)}</table>')


def _baris_importance(rank: int, fitur: str, nilai: float, maks: float) -> str:
    kelompok = KELOMPOK_FITUR.get(fitur, "Turunan")
    sp = kelompok == "Spasial"
    gaya = "background:#e4e4e4;color:#1c1c1c" if sp else "background:#edf1f3;color:var(--sub)"
    nama = NAMA_IMPORTANCE.get(fitur, LABEL_FITUR[fitur][0])
    kelas_tr = ' class="spRow"' if sp else ""
    kelas_bar = "impbar sp" if sp else "impbar"
    return (f'<tr{kelas_tr}><td class="num">{rank}</td><td>{nama}</td>'
            f'<td><span class="tag" style="{gaya}">{kelompok}</span></td>'
            f'<td class="impcell"><div class="{kelas_bar}" style="width:{nilai / maks * 100:.0f}%"></div></td>'
            f'<td class="num">{angka(nilai, 3)}</td></tr>')


def tabel_importance(imp: pd.Series, n: int = 10) -> str:
    """10 teratas; variabel spasial di luar 10 besar tetap ditampilkan di bawah. Mengembalikan catatan peringkat."""
    maks = imp.iloc[0]
    peringkat = {f: i + 1 for i, f in enumerate(imp.index)}
    isi = [_baris_importance(i + 1, f, v, maks) for i, (f, v) in enumerate(imp.iloc[:n].items())]
    di_luar = [f for f in FITUR_SPASIAL if peringkat[f] > n]
    if di_luar:
        isi.append('<tr class="gap"><td colspan="5">…</td></tr>')
        isi += [_baris_importance(peringkat[f], f, imp[f], maks) for f in sorted(di_luar, key=peringkat.get)]
    st.html('<table class="tbl"><tr><th class="num">#</th><th>Variabel</th><th>Kelompok</th>'
            f'<th>Kontribusi</th><th class="num">Nilai</th></tr>{"".join(isi)}</table>')
    rth, pdt = peringkat["luas_rth_km2"], peringkat["kepadatan_penduduk_jiwa_km2"]
    return (f"Luas RTH menempati peringkat <b>{rth}</b>, sedangkan kepadatan penduduk menempati peringkat "
            f"<b>{pdt}</b> dari {len(imp)} fitur masukan. Pengaruh kedua variabel spasial diuji lebih lanjut "
            "melalui perbandingan tiga skenario.")
