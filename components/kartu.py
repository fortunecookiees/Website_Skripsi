"""Elemen kartu: judul kartu, angka besar, chip/tag kategori ISPU, papan hasil prediksi 7 hari."""
import pandas as pd
import streamlit as st

from core.config import KATEGORI_ISPU, kategori_ispu

from .bahasa import kategori, saran, t
from .format import tanggal_pendek


def judul_kartu(teks: str, keterangan: str = "") -> str:
    em = f"<em>{keterangan}</em>" if keterangan else ""
    return f'<div class="cardTitle">{teks} {em}</div>'


def chip(nilai: float) -> str:
    k = kategori_ispu(nilai)
    return f'<span class="chip" style="background:{k["bg"]};color:{k["warna_teks"]}">{kategori(k["kategori"])}</span>'


def tag(nilai: float) -> str:
    k = kategori_ispu(nilai)
    return f'<span class="tag" style="background:{k["bg"]};color:{k["warna_teks"]}">{kategori(k["kategori"])}</span>'


def angka_besar(nilai: float) -> str:
    k = kategori_ispu(nilai)
    return f'<div class="big"><span class="n" style="color:{k["warna_teks"]}">{k["nilai"]}</span><span class="u">ISPU</span></div>'


def saran_kesehatan(nilai: float) -> str:
    """Rekomendasi PermenLHK P.14/2020 untuk PM2.5 sesuai kategori nilai."""
    sensitif, umum = saran(kategori_ispu(nilai)["kategori"])
    if sensitif is None:
        return f"{umum}."
    kecil = lambda s: s[0].lower() + s[1:]  # noqa: E731
    return t(f"Kelompok sensitif: {kecil(sensitif)}. Setiap orang: {kecil(umum)}.",
             f"Sensitive groups: {kecil(sensitif)}. Everyone: {kecil(umum)}.")


def _selisih(baru: int, lama: int, acuan: str) -> str:
    d = baru - lama
    if d > 0:
        return t(f"Naik {d} poin dari {acuan} ({lama})", f"Up {d} points from {acuan} ({lama})")
    if d < 0:
        return t(f"Turun {-d} poin dari {acuan} ({lama})", f"Down {-d} points from {acuan} ({lama})")
    return t(f"Sama dengan {acuan} ({lama})", f"Same as {acuan} ({lama})")


def teks_perubahan(pred_t1: float, pm25_hari_ini: float) -> str:
    """'Naik/Turun X poin dari hari terakhir (Y).' + saran kesehatan kategori t+1."""
    baru, lama = kategori_ispu(pred_t1)["nilai"], kategori_ispu(pm25_hari_ini)["nilai"]
    return f"{_selisih(baru, lama, t('hari terakhir', 'the latest day'))}. {saran_kesehatan(pred_t1)}"


def teks_puncak(prediksi: pd.DataFrame) -> str:
    """Kalimat puncak 7 hari. 'Melewati ambang' hanya jika kategori puncak berbeda dari t+1."""
    nilai = [kategori_ispu(v)["nilai"] for v in prediksi["pm25"]]
    i = max(range(len(nilai)), key=nilai.__getitem__)  # puncak pertama jika ada nilai sama
    r = prediksi.iloc[i]
    k_puncak, k_t1 = kategori_ispu(r["pm25"]), kategori_ispu(prediksi["pm25"].iloc[0])
    if i == 0:
        return t(f"Nilai tertinggi ada pada t+1 ({k_t1['nilai']} ISPU); hari-hari berikutnya diperkirakan tidak "
                 "melebihi nilai tersebut.",
                 f"The highest value is at t+1 ({k_t1['nilai']} ISPU); the following days are not expected to "
                 "exceed it.")
    h, tgl, n = int(r["horizon"]), tanggal_pendek(r["tanggal"]), k_puncak["nilai"]
    awal = t(f"Puncak diperkirakan pada t+{h} ({tgl}) dengan {n} ISPU", f"The peak is expected at t+{h} ({tgl}) "
             f"with {n} ISPU")
    if k_puncak["kategori"] != k_t1["kategori"]:
        return t(f"{awal}, melewati ambang kategori {kategori(k_puncak['kategori'])}.",
                 f"{awal}, crossing into the {kategori(k_puncak['kategori'])} category.")
    return t(f"{awal}; selama 7 hari kategori tetap {kategori(k_t1['kategori'])} seperti t+1.",
             f"{awal}; the category stays {kategori(k_t1['kategori'])} for all 7 days, as at t+1.")


def teks_simulasi(pred_sim_t1: float, pred_akt_t1: float, perubahan: list[str]) -> str:
    """Kalimat hasil simulasi t+1 dibanding mode aktual + daftar variabel yang diubah."""
    baru, lama = kategori_ispu(pred_sim_t1)["nilai"], kategori_ispu(pred_akt_t1)["nilai"]
    dan = t("dan", "and")
    if not perubahan:
        return t(f"Sama dengan mode aktual ({lama}). Geser slider untuk mengubah nilai variabel.",
                 f"Same as actual mode ({lama}). Move the sliders to change variable values.")
    if len(perubahan) > 3:
        daftar = ", ".join(perubahan[:3]) + t(f", dan {len(perubahan) - 3} variabel lain diubah",
                                              f", and {len(perubahan) - 3} other variables changed")
    elif len(perubahan) == 3:
        daftar = ", ".join(perubahan[:2]) + f", {dan} {perubahan[2]}"
    elif len(perubahan) == 2:
        daftar = f"{perubahan[0]} {dan} {perubahan[1]}"
    else:
        daftar = perubahan[0]
    if baru == lama:
        return t(f"Tetap sama dengan mode aktual ({lama}) meskipun {daftar}.",
                 f"Still the same as actual mode ({lama}) even though {daftar}.")
    return t(f"{_selisih(baru, lama, 'mode aktual')}, setelah {daftar}.",
             f"{_selisih(baru, lama, 'actual mode')}, after {daftar}.")


def teks_bandingkan(akt: pd.DataFrame, sim: pd.DataFrame, horizon=(1, 4, 7)) -> str:
    bagian = [f"t+{h} {kategori_ispu(akt['pm25'].iloc[h - 1])['nilai']} → "
              f"{kategori_ispu(sim['pm25'].iloc[h - 1])['nilai']}" for h in horizon]
    return t("Perbandingan terhadap mode aktual: ", "Compared with actual mode: ") + " · ".join(bagian)


def banner_simulasi() -> None:
    st.html('<div class="banner"><span class="dot"></span><span>' + t(
        "Hasil pada mode simulasi <b>bukan prediksi kondisi sebenarnya</b>. Nilai variabel diatur oleh pengguna dan "
        "hanya digunakan untuk mengamati pengaruh perubahan terhadap keluaran model.",
        "Simulation results are <b>not forecasts of real conditions</b>. Variable values are set by the user and "
        "only used to observe how changes affect the model output.") + "</span></div>")


def kpi(item: list[tuple[str, str, str]], ispu: list[float | None] | None = None) -> str:
    """Deretan kartu angka ringkas: [(label, nilai, keterangan)]. `ispu` opsional: nilai untuk warna angka."""
    ispu = ispu or [None] * len(item)
    kotak = []
    for (lbl, nilai, ket), v in zip(item, ispu):
        gaya = f' style="color:{kategori_ispu(v)["warna_teks"]}"' if v is not None else ""
        kotak.append(f'<div class="kpi"><div class="kl">{lbl}</div><div class="kv2"{gaya}>{nilai}</div>'
                     f'<div class="kk">{ket}</div></div>')
    return f'<div class="kpiRow">{"".join(kotak)}</div>'


def kosong(judul: str, teks: str) -> str:
    """Keadaan kosong (filter tanpa hasil, belum dihitung, dsb.)."""
    return f'<div class="simKosong"><b>{judul}</b><br>{teks}</div>'


def panel_prediksi(judul: str, sub: str, badge: str, label_acuan: str, pm25_acuan: float,
                   prediksi: pd.DataFrame, catatan: str, tanggal: bool = False) -> str:
    """Papan hasil prediksi: kartu besar kondisi acuan + 7 kartu 'n hari ke depan' + legenda ISPU.

    Dipakai Mode Aktual & Unggah Data (dengan tanggal) dan Mode Simulasi (tanpa tanggal, skenario hipotetis).
    """
    acuan = kategori_ispu(pm25_acuan)
    kartu = []
    for _, r in prediksi.iterrows():
        ks = kategori_ispu(r["pm25"])
        h = int(r["horizon"])
        ke_depan = t(f"{h} hari ke depan", f"{h} day{'s' if h > 1 else ''} ahead")
        tgl = f'<div class="psTgl">{tanggal_pendek(r["tanggal"], tahun=True)}</div>' if tanggal else ""
        kartu.append(f'<div class="psKartu"><div class="psH">{ke_depan}</div>{tgl}'
                     f'<div class="psN">{ks["nilai"]}<small>ISPU</small></div>{chip(r["pm25"])}</div>')
    legenda = "".join(f'<span><span class="chip" style="background:{bg};color:{teks}">{kategori(nama)}</span> '
                      f'{rentang}</span>' for _, nama, rentang, _, bg, teks in KATEGORI_ISPU)
    return (f'<div class="papanSim"><div class="psKepala"><div><div class="psJudul">{judul}</div>'
            f'<div class="psSub">{sub}</div></div>'
            f'<span class="psBadge"><span class="psDenyut"></span>{badge}</span></div>'
            f'<div class="psAcuan"><div class="psH">{label_acuan}</div>'
            f'<div class="psN besar">{acuan["nilai"]}<small>ISPU</small></div>{chip(pm25_acuan)}</div>'
            f'<div class="psGrid">{"".join(kartu)}</div><div class="psLegenda">{legenda}</div>'
            f'<div class="psCatatan">{catatan}</div></div>')


def panel_simulasi(stasiun: str, pm25_acuan: float, simulasi: pd.DataFrame, dijalankan: str | None) -> str:
    """Papan Mode Simulasi; 'dijalankan' hanya waktu tombol Prediksi diklik."""
    jalan = f" · {t('dijalankan', 'run on')} {dijalankan}" if dijalankan else ""
    return panel_prediksi(t("Hasil Prediksi Simulasi", "Simulation Forecast"), f"{stasiun}{jalan}",
                          t("SIMULASI", "SIMULATION"),
                          t("PM2.5 hari ini (nilai yang Anda atur)", "Today's PM2.5 (the value you set)"),
                          pm25_acuan, simulasi,
                          t("Hasil simulasi bukan prediksi kondisi sebenarnya.",
                            "Simulation results are not forecasts of real conditions."))
