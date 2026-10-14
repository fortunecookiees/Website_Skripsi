"""Tes modul Unggah Data (core/unggah.py) di terminal.

Pemakaian:  python tes_unggah.py
"""
import re

import numpy as np
import pandas as pd

from core.config import FITUR, HORIZONS
from core.inference import muat_model, prediksi_7_hari, prediksi_batch
from core.metrik import metrik_acuan, ringkasan_horizon
from core.preprocessing import data_evaluasi, kondisi_terakhir, muat_dataset, preprocess
from core.unggah import baca_file, buat_template, hasil_ke_csv, proses

models = muat_model()
mentah = muat_dataset()
dataset = preprocess(mentah)
rentang = dataset[FITUR].agg(["min", "max"]).T
lulus = gagal = 0


def cek(nama: str, kondisi: bool, detail: str = "") -> None:
    global lulus, gagal
    lulus, gagal = lulus + kondisi, gagal + (not kondisi)
    print(f"[{'OK ' if kondisi else 'GAGAL'}] {nama}" + (f"\n        {detail}" if detail else ""))


def jalankan(df: pd.DataFrame):
    return proses(df, models, dataset, rentang)


def teks(pesan: list[str]) -> str:
    return " | ".join(re.sub("<[^>]+>", "", p) for p in pesan)


def contoh(stasiun="DKI3 Jagakarsa", n=6) -> pd.DataFrame:
    kolom = ["tanggal", "stasiun", "pm10", "pm25", "so2", "co", "o3", "no2", "suhu_c", "kelembapan_pct",
             "curah_hujan_mm", "tutupan_awan_pct", "kecepatan_angin_kmh", "tekanan_hpa", "arah_angin_deg"]
    d = mentah[mentah["stasiun"] == stasiun].sort_values("tanggal").tail(n)[kolom].reset_index(drop=True)
    d["tanggal"] = d["tanggal"].dt.strftime("%Y-%m-%d")
    return d


# 1. Template -> hasil harus identik dengan Mode Aktual dashboard (DKI1, 8 Nov 2025)
tpl = buat_template(mentah)
h = jalankan(baca_file(tpl, "template.xlsx"))
ref = prediksi_7_hari(models, kondisi_terakhir(dataset, "DKI1 Bundaran HI"))
cek("template valid & prediksi = dashboard", h.ok and np.allclose(h.prediksi["pm25"], ref["pm25"]),
    f"unggah={h.prediksi['pm25'].round(1).tolist() if h.ok else h.error}  dashboard={ref['pm25'].round(1).tolist()}")

# 2. CSV pemisah ';' + desimal koma, 2 stasiun, kode 'dki3', kolom tambahan
d = pd.concat([contoh(), contoh("DKI5 Kebon Jeruk")])
d["stasiun"] = d["stasiun"].replace({"DKI3 Jagakarsa": "dki3"})
d["catatan"] = "x"
csv_id = d.to_csv(index=False, sep=";", decimal=",").encode("utf-8")
h = jalankan(baca_file(csv_id, "data.csv"))
cek("CSV ';' + desimal koma + kode stasiun", h.ok and set(h.kondisi) == {"DKI3 Jagakarsa", "DKI5 Kebon Jeruk"},
    teks(h.error or h.info))
ref3 = prediksi_7_hari(models, kondisi_terakhir(dataset, "DKI3 Jagakarsa"))
cek("  prediksi DKI3 dari CSV = dashboard", h.ok and np.allclose(
    h.prediksi[h.prediksi["stasiun"] == "DKI3 Jagakarsa"]["pm25"], ref3["pm25"]))
cek("  CSV hasil berisi 14 baris + kolom benar", h.ok and hasil_ke_csv(h.prediksi).decode("utf-8-sig").splitlines()[0]
    == "stasiun,tanggal_dasar,tanggal,horizon,pm25,kategori" and len(hasil_ke_csv(h.prediksi).splitlines()) == 15)

# 3–10. Error
kasus = {
    "kolom salah nama (pm2.5)": (lambda d: d.rename(columns={"pm25": "pm2.5"}), "pm2.5"),
    "format tanggal salah": (lambda d: d.assign(tanggal=d["tanggal"].where(d.index != 2, "08/11/2025")), "YYYY-MM-DD"),
    "stasiun tidak dikenal": (lambda d: d.assign(stasiun=d["stasiun"].where(d.index != 0, "DKI6")), "DKI6"),
    "tanggal duplikat": (lambda d: pd.concat([d, d.iloc[[3]]]), "duplikat"),
    "tanggal bolong": (lambda d: d.drop(index=2), "bolong"),
    "kurang dari 4 hari": (lambda d: d.tail(3), "minimal 4"),
    "pm25 kosong di 4 hari terakhir": (lambda d: d.assign(pm25=d["pm25"].where(d.index != 3, np.nan)), "PM2.5 kosong"),
    "meteorologi kosong hari terakhir": (lambda d: d.assign(suhu_c=d["suhu_c"].where(d.index != 5, np.nan)), "meteorologi"),
    "nilai bukan angka": (lambda d: d.assign(so2=d["so2"].astype(object).where(d.index != 1, "abc")), "bukan angka"),
    "nilai negatif": (lambda d: d.assign(co=d["co"].where(d.index != 4, -3)), "negatif"),
}
for nama, (ubah, kata) in kasus.items():
    h = jalankan(ubah(contoh()))
    cek(f"error: {nama}", not h.ok and kata.lower() in teks(h.error).lower(), teks(h.error))

# 11–12. Peringatan (prediksi tetap jalan)
h = jalankan(contoh().assign(pm10=np.nan))
cek("peringatan: PM10 kosong -> data tidak tersedia", h.ok and "PM10" in teks(h.peringatan)
    and np.isnan(h.kondisi["DKI3 Jagakarsa"]["pm10"]), teks(h.peringatan))
h = jalankan(contoh().assign(suhu_c=45.0))
cek("peringatan: suhu di luar rentang", h.ok and "di luar rentang" in teks(h.peringatan), teks(h.peringatan))

# 13. pm25 kosong di luar 4 hari terakhir -> diisi ffill, tetap valid
h = jalankan(contoh().assign(pm25=lambda d: d["pm25"].where(d.index != 0, np.nan)))
cek("pm25 kosong di hari awal (di luar 4 hari terakhir) tetap valid", h.ok, teks(h.error))

# 14–20. Tab Validasi
KOLOM_FILE = contoh().columns.tolist()


def potong(stasiun: str, mulai, n: int) -> pd.DataFrame:
    d = mentah[(mentah["stasiun"] == stasiun) & (mentah["tanggal"] >= pd.Timestamp(mulai))]
    d = d.sort_values("tanggal").head(n)[KOLOM_FILE].reset_index(drop=True)
    d["tanggal"] = d["tanggal"].dt.strftime("%Y-%m-%d")
    return d


h = jalankan(contoh(n=10))
cek("validasi: 10 hari -> belum ada tanggal acuan", h.ok and h.validasi.empty and h.hari == {"DKI3 Jagakarsa": 10})
h = jalankan(contoh(n=11))
cek("validasi: 11 hari -> tepat 1 tanggal acuan", h.ok and len(h.validasi) == 1,
    f"{len(h.validasi)} tanggal" if h.ok else teks(h.error))

# prediksi & aktual dari file = halaman Evaluation pada tanggal yang sama (data uji 2025)
uji, batas = data_evaluasi(dataset)
uji = pd.concat([uji, prediksi_batch(models, uji)], axis=1)
kol = [f"pred_h{k}" for k in HORIZONS] + [f"target_h{k}" for k in HORIZONS] + [f"target_h{k}_asli" for k in HORIZONS]
for st_nama in ["DKI1 Bundaran HI", "DKI4 Lubang Buaya"]:
    h = jalankan(potong(st_nama, batas - pd.Timedelta(days=3), 40))
    a = h.validasi.set_index("tanggal")
    b = uji[uji["stasiun"] == st_nama].set_index("tanggal")
    sama = a.index.intersection(b.index)
    cocok = len(sama) >= 25 and np.allclose(a.loc[sama, kol].astype(float), b.loc[sama, kol].astype(float))
    cek(f"validasi {st_nama.split()[0]}: prediksi & aktual = Evaluation", h.ok and cocok,
        f"{len(a)} tanggal acuan, {len(sama)} beririsan dengan data uji")

# meteorologi kosong di tengah file -> tanggal acuan itu dilewati & dihitung
d = potong("DKI1 Bundaran HI", batas, 15)
h_utuh = jalankan(d)
d.loc[5, "kelembapan_pct"] = np.nan
h = jalankan(d)
tgl_kosong = pd.Timestamp(d.loc[5, "tanggal"])
cek("validasi: meteorologi kosong -> tanggal acuan dilewati",
    h.ok and len(h.validasi) == len(h_utuh.validasi) - 1 and tgl_kosong not in set(h.validasi["tanggal"])
    and h.dilewati_meteo == {"DKI1 Bundaran HI": 1}, f"dilewati={h.dilewati_meteo}")

# PM2.5 aktual kosong -> ditandai data diisi, tidak masuk metrik
d = potong("DKI1 Bundaran HI", batas, 11)
d.loc[6, "pm25"] = np.nan  # = target t+3 dari satu-satunya tanggal acuan (indeks 3); 4 hari terakhir wajib terisi
h = jalankan(d)
b = h.validasi.iloc[0]
m = metrik_acuan(b)
asli = [k for k in HORIZONS if b[f"target_h{k}_asli"]]
galat = np.array([b[f"pred_h{k}"] - b[f"target_h{k}"] for k in asli])
cek("validasi: aktual kosong ditandai data diisi & dilewati metrik",
    h.ok and not b["target_h3_asli"] and m["n"] == 6 and np.isclose(m["MAE"], np.abs(galat).mean())
    and np.isclose(m["RMSE"], np.sqrt((galat ** 2).mean())), f"n={m['n']} asli={asli}")
r = ringkasan_horizon(h.validasi)
cek("ringkasan: n per horizon melewati data diisi", r.loc[r["horizon"] == 3, "n"].item() == 0
    and r.loc[r["horizon"] != 3, "n"].eq(1).all() and r["MAE"].isna().sum() == 1, r[["horizon", "n"]].to_string())

print(f"\n{lulus} lulus, {gagal} gagal")
