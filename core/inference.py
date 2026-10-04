"""Memuat 7 model .pkl dan menjalankan prediksi PM2.5 t+1..t+7."""
import pickle

import numpy as np
import pandas as pd
import xgboost as xgb

from .config import FITUR, HORIZONS, MODEL_DIR
from .preprocessing import matriks_fitur

# ---------------------------------------------------------------------
# Fallback pemuatan .pkl lintas OS
# Model dilatih di Colab (Linux). Field `rng_state` di config booster
# disimpan dalam format libstdc++ yang tidak terbaca xgboost Windows (MSVC)
# -> "input stream corrupted". rng_state hanya dipakai saat training,
# jadi aman diganti dengan state valid lokal; prediksi tidak berubah.
# ---------------------------------------------------------------------
_RNG_KEY = b"L" + (9).to_bytes(8, "big") + b"rng_state"


def _posisi_rng(raw: bytes) -> tuple[int, int]:
    """Posisi awal & akhir nilai string `rng_state` di buffer UBJSON."""
    i = raw.find(_RNG_KEY)
    j = i + len(_RNG_KEY)
    if i < 0 or raw[j:j + 2] != b"SL":
        raise ValueError("rng_state tidak ditemukan di booster")
    return j, j + 10 + int.from_bytes(raw[j + 2:j + 10], "big")


def _rng_lokal() -> bytes:
    dm = xgb.DMatrix(np.zeros((2, 1)), label=[0, 1])
    raw = bytes(xgb.train({"verbosity": 0}, dm, num_boost_round=1).__getstate__()["handle"])
    j, k = _posisi_rng(raw)
    return raw[j:k]


class _BoosterLintasOS(xgb.Booster):
    def __setstate__(self, state):
        raw = bytes(state["handle"])
        j, k = _posisi_rng(raw)
        super().__setstate__({**state, "handle": bytearray(raw[:j] + _rng_lokal() + raw[k:])})


class _UnpicklerLintasOS(pickle.Unpickler):
    def find_class(self, module, name):
        if (module, name) == ("xgboost.core", "Booster"):
            return _BoosterLintasOS
        return super().find_class(module, name)


def muat_pkl(path) -> dict:
    """pickle.load biasa; patch rng_state hanya jika booster gagal dibaca."""
    with open(path, "rb") as f:
        try:
            return pickle.load(f)
        except xgb.core.XGBoostError:
            f.seek(0)
            return _UnpicklerLintasOS(f).load()


def muat_model(model_dir=MODEL_DIR) -> dict[int, dict]:
    """Muat model_pm25_h1..h7.pkl -> {h: {'model', 'scaler', 'fitur', 'horizon'}}."""
    models = {}
    for h in HORIZONS:
        d = muat_pkl(model_dir / f"model_pm25_h{h}.pkl")
        if list(d["fitur"]) != FITUR:
            raise ValueError(f"Urutan fitur model h{h} tidak sesuai konfigurasi aplikasi")
        models[h] = d
    return models


# ---------------------------------------------------------------------
# Prediksi
# ---------------------------------------------------------------------
def prediksi_batch(models: dict, data: pd.DataFrame) -> pd.DataFrame:
    """Prediksi semua horizon untuk banyak baris. Kolom hasil: pred_h1..pred_h7."""
    X = matriks_fitur(data)
    hasil = {f"pred_h{h}": models[h]["model"].predict(models[h]["scaler"].transform(X))
             for h in HORIZONS}
    return pd.DataFrame(hasil, index=data.index)


def prediksi_7_hari(models: dict, fitur: pd.Series | dict) -> pd.DataFrame:
    """Prediksi PM2.5 t+1..t+7 dari satu baris fitur hari t.

    `fitur` minimal berisi 21 kolom FITUR + `tanggal`. Hasil: horizon, tanggal, pm25.
    """
    baris = pd.Series(fitur)
    pred = prediksi_batch(models, baris.to_frame().T).iloc[0].to_numpy()
    tanggal = pd.Timestamp(baris["tanggal"])
    return pd.DataFrame({
        "horizon": HORIZONS,
        "tanggal": [tanggal + pd.Timedelta(days=h) for h in HORIZONS],
        "pm25": pred.astype(float),
    })
