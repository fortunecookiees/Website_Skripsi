"""Format angka & tanggal gaya Indonesia (desimal koma, ribuan titik)."""
import math

import pandas as pd

BULAN = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli",
         "Agustus", "September", "Oktober", "November", "Desember"]
HARI = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]


def angka(nilai: float, desimal: int = 0) -> str:
    """12959 -> '12.959', 0.273 -> '0,273'."""
    if nilai is None or (isinstance(nilai, float) and math.isnan(nilai)):
        return "–"
    s = f"{nilai:,.{desimal}f}"
    return s.replace(",", "_").replace(".", ",").replace("_", ".")


def tanggal_panjang(t) -> str:
    t = pd.Timestamp(t)
    return f"{t.day} {BULAN[t.month - 1]} {t.year}"


def tanggal_pendek(t, tahun: bool = False) -> str:
    t = pd.Timestamp(t)
    s = f"{t.day} {BULAN[t.month - 1][:3]}"
    return f"{s} {t.year}" if tahun else s
