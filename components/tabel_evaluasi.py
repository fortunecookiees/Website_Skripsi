"""Tabel halaman Evaluation: prediksi vs aktual, metrik, metode optimasi, feature importance."""
import pandas as pd
import streamlit as st

from core.config import FITUR_METEOROLOGI, FITUR_POLUTAN, FITUR_SPASIAL, HORIZONS, kategori_ispu

from .bahasa import label_fitur, t
from .format import angka, tanggal_pendek
from .kartu import tag

KELOMPOK_FITUR = {**{f: "Spasial" for f in FITUR_SPASIAL}, **{f: "Meteorologi" for f in FITUR_METEOROLOGI},
                  **{f: "Polutan" for f in FITUR_POLUTAN}}
NAMA_KELOMPOK_EN = {"Spasial": "Spatial", "Meteorologi": "Meteorological", "Polutan": "Pollutant",
                    "Turunan": "Derived"}
NAMA_IMPORTANCE = {"pm25": ("PM2.5 hari ini", "PM2.5 today"), "pm10": ("PM10", "PM10")}


def catatan_diisi() -> str:
    return t("Nilai bertanda <i>data diisi</i> berasal dari pengisian data kosong (forward fill), sehingga tidak "
             "dihitung kesalahannya, sama seperti perhitungan metrik saat pelatihan yang hanya memakai nilai asli.",
             "Values marked <i>filled data</i> come from filling missing data (forward fill), so their error is not "
             "computed, just like the training metrics, which only use original values.")


def legend_sekitar_acuan(semua_asli: bool) -> str:
    """Legend grafik sekitar tanggal acuan; item 'data diisi' hanya jika ada titik hasil ffill."""
    legend = [f'<span><i style="background:#347653"></i>{t("Nilai aktual", "Actual value")}</span>',
              f'<span><i style="background:#8c9b96"></i>{t("Nilai prediksi", "Predicted value")} (t+1 … t+7)</span>']
    if not semua_asli:
        legend.append('<span><i style="background:#fff;border:1.5px solid #347653;border-radius:50%"></i>'
                      + t("Titik berongga: data diisi", "Hollow point: filled data") + '</span>')
    return f'<div class="legend">{"".join(legend)}</div>'


def strip_metrik_acuan(m: dict) -> str:
    """MAE · RMSE · MAPE satu tanggal acuan (hasil core.metrik.metrik_acuan)."""
    if not m["n"]:
        return ('<div class="mStrip"><span class="diisi">' + t(
            "Metrik tidak dapat dihitung: seluruh nilai aktual t+1 … t+7 merupakan data diisi.",
            "Metrics cannot be computed: all actual values t+1 … t+7 are filled data.") + '</span></div>')
    sel = [("MAE", angka(m["MAE"], 1)), ("RMSE", angka(m["RMSE"], 1)),
           ("MAPE", "–" if m["MAPE"] is None else f"{angka(m['MAPE'], 1)} %")]
    isi = "".join(f'<div class="m"><span>{k}</span><b>{v}</b></div>' for k, v in sel)
    lewat = len(HORIZONS) - m["n"]
    ket = t(f"Dihitung dari {m['n']} horizon", f"Computed from {m['n']} horizons")
    if lewat:
        ket += t(f" ({lewat} nilai aktual berupa data diisi tidak dihitung)",
                 f" ({lewat} filled actual values not counted)")
    ket += t(", memakai nilai prediksi sebelum dibulatkan.", ", using predictions before rounding.")
    return f'<div class="mStrip">{isi}<div class="ket">{ket}</div></div>'


def tabel_ringkasan_validasi(r: pd.DataFrame) -> None:
    """MAE & RMSE per horizon atas semua tanggal acuan (hasil core.metrik.ringkasan_horizon)."""
    # horizon sebagai kolom agar tabel pendek (3 baris) dan bisa dibaca mendatar
    def sel(v, desimal=1):
        return "–" if v is None or pd.isna(v) else angka(v, desimal)
    kepala = "".join(f'<th class="num">t+{int(h)}</th>' for h in r["horizon"])
    baris = [("MAE", [sel(v) for v in r["MAE"]]), ("RMSE", [sel(v) for v in r["RMSE"]]),
             (t("Jumlah", "Count"), [str(int(v)) for v in r["n"]])]
    isi = "".join(f'<tr><td>{nama}</td>{"".join(f"<td class=num>{v}</td>" for v in nilai)}</tr>' for nama, nilai in baris)
    st.html(f'<table class="tbl tblMendatar"><tr><th>{t("Metrik", "Metric")}</th>{kepala}</tr>{isi}</table>')


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
            err = f'<span class="diisi">{t("tidak dihitung", "not computed")}</span>'
        ket = "" if asli else f' <span class="diisi">{t("data diisi", "filled data")}</span>'
        isi.append(f"<tr><td>t+{h}</td><td>{tanggal_pendek(baris['tanggal'] + pd.Timedelta(days=h), tahun=True)}</td>"
                   f'<td class="num">{np_}</td><td class="num">{na}{ket}</td><td class="num">{_tanda(np_ - na)}</td>'
                   f'<td class="num">{err}</td><td>{tag(akt)}</td></tr>')
    st.html(f'<table class="tbl"><tr><th>Horizon</th><th>{t("Tanggal", "Date")}</th>'
            f'<th class="num">{t("Prediksi", "Predicted")}</th><th class="num">{t("Aktual", "Actual")}</th>'
            f'<th class="num">{t("Selisih", "Difference")}</th><th class="num">{t("Kesalahan", "Error")}</th>'
            f'<th>{t("Kategori Aktual", "Actual Category")}</th></tr>{"".join(isi)}</table>')


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
            '<th class="num">MAPE</th><th class="num">R²</th>'
            f'<th class="num">{t("RMSE Persistensi", "Persistence RMSE")}</th></tr>'
            f'{"".join(isi)}</table>')
    if len(menang) == len(HORIZONS):
        return t("Nilai RMSE model lebih kecil daripada <i>baseline</i> persistensi pada seluruh horizon.",
                 "The model RMSE is lower than the persistence <i>baseline</i> at every horizon.")
    kalah = ", ".join(f"t+{h}" for h in HORIZONS if h not in menang)
    return t(f"Nilai RMSE model lebih kecil daripada <i>baseline</i> persistensi pada {len(menang)} dari "
             f"{len(HORIZONS)} horizon (tidak lebih kecil pada {kalah}).",
             f"The model RMSE is lower than the persistence <i>baseline</i> at {len(menang)} of "
             f"{len(HORIZONS)} horizons (not lower at {kalah}).")


def tabel_optimasi(ev: dict) -> None:
    """RMSE uji: hyperparameter bawaan vs Random Search vs PSO; nilai terkecil per horizon ditebalkan."""
    kolom = [("default", t("Hyperparameter Bawaan", "Default Hyperparameters")), ("random_search", "Random Search"),
             ("pso", "PSO")]
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
    gaya = "background:#ddeaf2;color:#22352c" if sp else "background:#edf1ef;color:var(--sub)"
    nama = t(*NAMA_IMPORTANCE[fitur]) if fitur in NAMA_IMPORTANCE else label_fitur(fitur)[0]
    kelas_tr = ' class="spRow"' if sp else ""
    kelas_bar = "impbar sp" if sp else "impbar"
    return (f'<tr{kelas_tr}><td class="num">{rank}</td><td>{nama}</td>'
            f'<td><span class="tag" style="{gaya}">{t(kelompok, NAMA_KELOMPOK_EN[kelompok])}</span></td>'
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
    st.html(f'<table class="tbl"><tr><th class="num">#</th><th>{t("Variabel", "Variable")}</th>'
            f'<th>{t("Kelompok", "Group")}</th><th>{t("Kontribusi", "Contribution")}</th>'
            f'<th class="num">{t("Nilai", "Value")}</th></tr>{"".join(isi)}</table>')
    rth, pdt = peringkat["luas_rth_km2"], peringkat["kepadatan_penduduk_jiwa_km2"]
    return t(f"Luas RTH menempati peringkat <b>{rth}</b>, sedangkan kepadatan penduduk menempati peringkat "
             f"<b>{pdt}</b> dari {len(imp)} fitur masukan. Pengaruh kedua variabel spasial diuji lebih lanjut "
             "melalui perbandingan tiga skenario.",
             f"Green open space area ranks <b>{rth}</b> and population density ranks <b>{pdt}</b> of "
             f"{len(imp)} input features. The effect of both spatial variables is tested further by comparing "
             "three scenarios.")


def tabel_skenario(data: dict, alpha: float = 0.05) -> str:
    """RMSE uji S1/S2/S3 + uji DM S1 vs S3; RMSE terkecil per horizon ditebalkan. Mengembalikan catatan."""
    sk = data["skenario"]
    isi, s3_lebih_baik, signifikan = [], [], []
    for h in map(str, HORIZONS):
        r = sk[h]
        terbaik = min(("S1", "S2", "S3"), key=r.get)
        sel = "".join(f'<td class="num{" best" if k == terbaik else ""}">{angka(r[k], 3)}</td>' for k in ("S1", "S2", "S3"))
        if r["S3"] < r["S1"]:
            s3_lebih_baik.append(h)
        if r["p"] < alpha:
            signifikan.append(h)
        isi.append(f'<tr><td>t+{h}</td>{sel}<td class="num">{angka(r["DM"], 3)}</td>'
                   f'<td class="num">{angka(r["p"], 4)}</td></tr>')
    st.html(f'<table class="tbl"><tr><th>Horizon</th><th class="num">S1 · {t("tanpa statis", "no static")}</th>'
            f'<th class="num">S2 · {t("+ penanda stasiun", "+ station marker")}</th>'
            f'<th class="num">S3 · {t("+ kepadatan &amp; RTH", "+ density &amp; GOS")}</th>'
            f'<th class="num">DM (S1 vs S3)</th><th class="num">p</th></tr>{"".join(isi)}</table>')

    daftar = ", ".join(f"t+{h}" for h in s3_lebih_baik)
    tambahan = f" ({daftar})" if s3_lebih_baik else ""
    n_s3, n_h, a = len(s3_lebih_baik), len(HORIZONS), angka(alpha, 2)
    kalimat = [t(f"S3 menghasilkan RMSE lebih kecil daripada S1 pada <b>{n_s3} dari {n_h}</b> horizon{tambahan}.",
                 f"S3 has a lower RMSE than S1 at <b>{n_s3} of {n_h}</b> horizons{tambahan}.")]
    if signifikan:
        daftar_sig = ", ".join(f"t+{h}" for h in signifikan)
        kalimat.append(t(f"Perbedaan S1 dan S3 signifikan pada p &lt; {a} di {daftar_sig}.",
                         f"The S1–S3 difference is significant at p &lt; {a} at {daftar_sig}."))
    else:
        h_min = min(sk, key=lambda h: sk[h]["p"])
        p_min = angka(sk[h_min]["p"], 4)
        kalimat.append(t(f"Uji Diebold-Mariano tidak menunjukkan perbedaan signifikan pada p &lt; {a} di seluruh "
                         f"horizon (p terkecil {p_min} pada t+{h_min}).",
                         f"The Diebold-Mariano test shows no significant difference at p &lt; {a} at any horizon "
                         f"(smallest p {p_min} at t+{h_min})."))
    kalimat.append(t("DM &gt; 0 berarti galat S3 lebih kecil daripada S1.",
                     "DM &gt; 0 means S3 has a smaller error than S1."))
    return " ".join(kalimat)
