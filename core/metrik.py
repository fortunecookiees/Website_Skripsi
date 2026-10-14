"""Metrik prediksi vs aktual per tanggal acuan & per horizon (hanya target PM2.5 asli, bukan hasil ffill)."""
import numpy as np
import pandas as pd

from .config import HORIZONS


def _hitung(pred: np.ndarray, akt: np.ndarray) -> dict:
    """MAE, RMSE, MAPE dari prediksi mentah (desimal) seperti saat training. MAPE melewati aktual 0."""
    if len(pred) == 0:
        return {"n": 0, "MAE": None, "RMSE": None, "MAPE": None}
    galat = pred - akt
    bukan_nol = akt != 0
    mape = float(np.mean(np.abs(galat[bukan_nol]) / akt[bukan_nol]) * 100) if bukan_nol.any() else None
    return {"n": int(len(pred)), "MAE": float(np.mean(np.abs(galat))),
            "RMSE": float(np.sqrt(np.mean(galat ** 2))), "MAPE": mape}


def metrik_acuan(baris: pd.Series) -> dict:
    """Metrik 7 horizon untuk satu tanggal acuan (kolom pred_hX, target_hX, target_hX_asli)."""
    asli = [h for h in HORIZONS if bool(baris[f"target_h{h}_asli"])]
    pred = np.array([baris[f"pred_h{h}"] for h in asli], dtype=float)
    akt = np.array([baris[f"target_h{h}"] for h in asli], dtype=float)
    return _hitung(pred, akt)


def bentuk_panjang(data: pd.DataFrame) -> pd.DataFrame:
    """Data uji lebar (pred_hX, target_hX) -> satu baris per (stasiun, tanggal acuan, horizon).

    Kolom: stasiun, tanggal_acuan, horizon, tanggal_target, prediksi, aktual, asli, selisih, kategori_aktual.
    """
    bagian = []
    for h in HORIZONS:
        bagian.append(pd.DataFrame({
            "stasiun": data["stasiun"].to_numpy(), "tanggal_acuan": data["tanggal"].to_numpy(), "horizon": h,
            "tanggal_target": (data["tanggal"] + pd.Timedelta(days=h)).to_numpy(),
            "prediksi": data[f"pred_h{h}"].to_numpy(float), "aktual": data[f"target_h{h}"].to_numpy(float),
            "asli": data[f"target_h{h}_asli"].astype(bool).to_numpy()}))
    p = pd.concat(bagian, ignore_index=True)
    p["selisih"] = p["prediksi"] - p["aktual"]
    return p.sort_values(["tanggal_acuan", "stasiun", "horizon"]).reset_index(drop=True)


def metrik_panjang(p: pd.DataFrame) -> dict:
    """MAE, RMSE, MAPE dari baris bentuk_panjang (hanya nilai aktual asli)."""
    a = p[p["asli"]]
    return _hitung(a["prediksi"].to_numpy(float), a["aktual"].to_numpy(float))


def ringkasan_horizon(data: pd.DataFrame) -> pd.DataFrame:
    """MAE & RMSE per horizon atas semua tanggal acuan di `data`. Kolom: horizon, n, MAE, RMSE."""
    isi = []
    for h in HORIZONS:
        d = data[data[f"target_h{h}_asli"].astype(bool)]
        m = _hitung(d[f"pred_h{h}"].to_numpy(float), d[f"target_h{h}"].to_numpy(float))
        isi.append({"horizon": h, "n": m["n"], "MAE": m["MAE"], "RMSE": m["RMSE"]})
    return pd.DataFrame(isi)
