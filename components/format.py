"""Format angka & tanggal sesuai bahasa aktif.

Indonesia: desimal koma, ribuan titik, "8 November 2025". English: desimal titik, ribuan koma, "8 November 2025".
"""
import math

import pandas as pd

from .bahasa import inggris

BULAN_ID = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli",
            "Agustus", "September", "Oktober", "November", "Desember"]
BULAN_EN = ["January", "February", "March", "April", "May", "June", "July",
            "August", "September", "October", "November", "December"]
HARI_ID = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]
HARI_EN = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


class _Daftar:
    """Daftar nama yang mengikuti bahasa aktif saat diakses (BULAN[i], HARI[i])."""

    def __init__(self, id_: list[str], en: list[str]):
        self._id, self._en = id_, en

    def _aktif(self) -> list[str]:
        return self._en if inggris() else self._id

    def __getitem__(self, i):
        return self._aktif()[i]

    def __len__(self) -> int:
        return len(self._id)

    def __iter__(self):
        return iter(self._aktif())


BULAN = _Daftar(BULAN_ID, BULAN_EN)
HARI = _Daftar(HARI_ID, HARI_EN)


def angka(nilai: float, desimal: int = 0) -> str:
    """12959 -> '12.959' (ID) / '12,959' (EN); 0.273 -> '0,273' / '0.273'."""
    if nilai is None or (isinstance(nilai, float) and math.isnan(nilai)):
        return "–"
    s = f"{nilai:,.{desimal}f}"
    if not inggris():
        s = s.replace(",", "_").replace(".", ",").replace("_", ".")
    return s.replace("-", "−")


def tanggal_panjang(t) -> str:
    t = pd.Timestamp(t)
    return f"{t.day} {BULAN[t.month - 1]} {t.year}"


def waktu_jakarta(iso: str | None, bulan_pendek: bool = False, jam: bool = True, wib: bool = False) -> str:
    """Waktu ISO dari server (UTC jika tanpa zona) -> WIB, mis. '8 November 2025, 13.05 WIB'. '–' jika kosong."""
    if not iso:
        return "–"
    w = pd.Timestamp(iso)
    w = w.tz_convert("Asia/Jakarta") if w.tzinfo else w.tz_localize("UTC").tz_convert("Asia/Jakarta")
    bulan = BULAN[w.month - 1]
    teks = f"{w.day} {bulan[:3] if bulan_pendek else bulan} {w.year}"
    if jam:
        teks += f", {w:%H.%M}" + (" WIB" if wib else "")
    return teks


def tanggal_pendek(t, tahun: bool = False) -> str:
    t = pd.Timestamp(t)
    s = f"{t.day} {BULAN[t.month - 1][:3]}"
    return f"{s} {t.year}" if tahun else s
