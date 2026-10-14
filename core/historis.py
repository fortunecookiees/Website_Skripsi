"""Penjelajahan data historis PM2.5 dari dataset: filter, agregasi, ringkasan, distribusi kategori.

Hanya membaca dataset yang sudah dipreprocessing (kolom pm25 & pm25_asli); tidak ada model di sini.
"""
import pandas as pd

from .config import KATEGORI_ISPU, STASIUN, bulatkan_ispu, kategori_ispu

URUTAN_KATEGORI = [nama for _, nama, *_ in KATEGORI_ISPU]
FREKUENSI = {"Harian": None, "Mingguan": "W-MON", "Bulanan": "MS"}  # minggu diberi label Senin awal minggu


def saring(data: pd.DataFrame, stasiun: list[str], mulai, akhir, kategori: list[str] | None = None,
           sertakan_diisi: bool = False) -> pd.DataFrame:
    """Baris PM2.5 harian sesuai filter. Kolom: tanggal, stasiun, pm25 (ISPU bulat), pm25_asli, kategori."""
    d = data[data["stasiun"].isin(stasiun)
             & data["tanggal"].between(pd.Timestamp(mulai), pd.Timestamp(akhir))].dropna(subset=["pm25"])
    if not sertakan_diisi:
        d = d[d["pm25_asli"]]
    d = d[["tanggal", "stasiun", "pm25", "pm25_asli"]].copy()
    d["pm25"] = d["pm25"].map(bulatkan_ispu)
    d["kategori"] = d["pm25"].map(lambda v: kategori_ispu(v)["kategori"])
    if kategori:
        d = d[d["kategori"].isin(kategori)]
    urutan = {s: i for i, s in enumerate(STASIUN)}
    return d.sort_values(["tanggal", "stasiun"], key=lambda s: s.map(urutan) if s.name == "stasiun" else s) \
            .reset_index(drop=True)


def agregasi(data: pd.DataFrame, frekuensi: str) -> pd.DataFrame:
    """Rata-rata PM2.5 per stasiun per periode. Kolom: tanggal, stasiun, pm25, n_hari."""
    aturan = FREKUENSI[frekuensi]
    if aturan is None:
        return data.assign(n_hari=1)[["tanggal", "stasiun", "pm25", "n_hari"]]
    g = data.groupby(["stasiun", pd.Grouper(key="tanggal", freq=aturan, label="left", closed="left")])["pm25"]
    return g.agg(pm25="mean", n_hari="size").reset_index()[["tanggal", "stasiun", "pm25", "n_hari"]]


def ringkasan(data: pd.DataFrame) -> dict:
    """Angka ringkas untuk kartu KPI."""
    if data.empty:
        return {"n": 0}
    puncak = data.loc[data["pm25"].idxmax()]
    terendah = data.loc[data["pm25"].idxmin()]
    sehat = data["kategori"].isin(URUTAN_KATEGORI[:2]).mean() * 100  # Baik + Sedang
    return {"n": len(data), "n_stasiun": data["stasiun"].nunique(), "rata": float(data["pm25"].mean()),
            "median": float(data["pm25"].median()), "puncak": puncak, "terendah": terendah,
            "persen_baik_sedang": float(sehat), "n_diisi": int((~data["pm25_asli"]).sum())}


def distribusi_kategori(data: pd.DataFrame) -> pd.DataFrame:
    """Persentase hari per kategori per stasiun (baris = stasiun, kolom = kategori, nilai 0–100)."""
    if data.empty:
        return pd.DataFrame(columns=URUTAN_KATEGORI)
    tab = pd.crosstab(data["stasiun"], data["kategori"], normalize="index") * 100
    tab = tab.reindex(columns=URUTAN_KATEGORI, fill_value=0.0)
    return tab.reindex([s for s in STASIUN if s in tab.index])


def rata_bulanan(data: pd.DataFrame) -> pd.DataFrame:
    """Rata-rata PM2.5 per bulan (baris) per stasiun (kolom)."""
    if data.empty:
        return pd.DataFrame()
    t = data.assign(bulan=data["tanggal"].dt.to_period("M")).pivot_table(
        index="bulan", columns="stasiun", values="pm25", aggfunc="mean")
    return t.reindex(columns=[s for s in STASIUN if s in t.columns])


def ke_csv(data: pd.DataFrame) -> bytes:
    out = data.assign(tanggal=data["tanggal"].dt.strftime("%Y-%m-%d"),
                      keterangan=data["pm25_asli"].map({True: "", False: "data diisi"}))
    return out[["tanggal", "stasiun", "pm25", "kategori", "keterangan"]].to_csv(index=False).encode("utf-8-sig")
