"""Tes modul preprocessing & inference di terminal.

Pemakaian:  python tes_inference.py ["DKI1 Bundaran HI"]
"""
import json
import sys
import time

import numpy as np
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

from core.config import EVAL_PATH, FITUR, HORIZONS, STASIUN, kategori_ispu
from core.inference import muat_model, prediksi_7_hari, prediksi_batch
from core.preprocessing import data_evaluasi, kondisi_terakhir, muat_dataset, preprocess

stasiun = sys.argv[1] if len(sys.argv) > 1 else "DKI1 Bundaran HI"
if stasiun not in STASIUN:
    sys.exit(f"Stasiun tidak dikenal. Pilihan: {', '.join(STASIUN)}")

t0 = time.perf_counter()
models = muat_model()
df = preprocess(muat_dataset())
print(f"Model & data dimuat dalam {time.perf_counter() - t0:.1f} detik\n")

# --- 1. Prediksi 7 hari dari kondisi terakhir --------------------------
baris = kondisi_terakhir(df, stasiun)
print(f"=== {stasiun} | kondisi terakhir {baris['tanggal']:%d %b %Y} ===")
for f in FITUR:
    v = baris[f]
    print(f"  {f:28s} {'data tidak tersedia' if np.isnan(v) else round(float(v), 3)}")

hasil = prediksi_7_hari(models, baris)
print(f"\n{'Horizon':8s}{'Tanggal':14s}{'PM2.5':>8s}  Kategori")
for _, r in hasil.iterrows():
    print(f"t+{r['horizon']:<6d}{r['tanggal']:%d %b %Y}   {r['pm25']:7.1f}  {kategori_ispu(r['pm25'])['kategori']}")

# --- 2. Ringkasan t+1 semua stasiun ------------------------------------
print("\n=== Prediksi t+1 kelima stasiun ===")
for st in STASIUN:
    p = prediksi_7_hari(models, kondisi_terakhir(df, st)).iloc[0]
    print(f"  {st:20s} {p['tanggal']:%d %b %Y}  {p['pm25']:6.1f}  {kategori_ispu(p['pm25'])['kategori']}")

# --- 3. Verifikasi: metrik data uji harus sama dengan hasil_evaluasi.json
uji, batas = data_evaluasi(df)
pred = prediksi_batch(models, uji)
ev = json.load(open(EVAL_PATH))["pso"]
print(f"\n=== Verifikasi data uji ({len(uji)} baris, {batas:%d %b %Y} s.d. {uji['tanggal'].max():%d %b %Y}) ===")
print(f"{'h':>2} {'MAE':>8} {'RMSE':>8} {'MAPE':>7} {'R2':>7}  vs json")
semua_cocok = True
for h in HORIZONS:
    a = uji[f"target_h{h}_asli"].to_numpy()
    yt, yp = uji[f"target_h{h}"].to_numpy()[a], pred[f"pred_h{h}"].to_numpy()[a]
    v = yt != 0
    m = dict(MAE=mean_absolute_error(yt, yp), RMSE=np.sqrt(mean_squared_error(yt, yp)),
             MAPE=np.mean(np.abs((yt[v] - yp[v]) / yt[v])) * 100, R2=r2_score(yt, yp))
    cocok = all(np.isclose(m[k], ev[str(h)][k], atol=1e-4) for k in m)
    semua_cocok &= cocok
    print(f"{h:>2} {m['MAE']:8.3f} {m['RMSE']:8.3f} {m['MAPE']:6.2f}% {m['R2']:7.3f}  {'COCOK' if cocok else 'BEDA'}")
print("\nHASIL:", "semua metrik identik dengan training" if semua_cocok else "ADA PERBEDAAN — cek preprocessing")
