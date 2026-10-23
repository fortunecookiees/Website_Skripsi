"""Halaman Data Historis — jelajahi PM2.5 dataset dengan filter stasiun, rentang tanggal, kategori, dan agregasi."""
import pandas as pd
import streamlit as st

from components import sumber_data as sd
from components.bahasa import kategori as nama_kategori, t
from components.format import angka, tanggal_panjang, tanggal_pendek
from components.grafik import grafik_distribusi, grafik_historis
from components.kartu import judul_kartu, kosong, kpi
from components.tabel import tabel_rata_bulanan
from components.tema import judul, label
from core import historis as hs
from core.config import STASIUN, kategori_ispu

daftar_stasiun = list(STASIUN)
MULAI, AKHIR = (tg.date() for tg in sd.rentang_tanggal())
PRESET = {
    "Semua": (MULAI, AKHIR),
    "2024": (max(MULAI, pd.Timestamp("2024-01-01").date()), pd.Timestamp("2024-12-31").date()),
    "2025": (pd.Timestamp("2025-01-01").date(), AKHIR),
    "3 bulan": ((pd.Timestamp(AKHIR) - pd.DateOffset(months=3) + pd.Timedelta(days=1)).date(), AKHIR),
    "30 hari": ((pd.Timestamp(AKHIR) - pd.Timedelta(days=29)).date(), AKHIR),
}
NAMA_PRESET_EN = {"Semua": "All", "3 bulan": "3 months", "30 hari": "30 days"}
NAMA_FREK_EN = {"Harian": "Daily", "Mingguan": "Weekly", "Bulanan": "Monthly"}


def _preset(p: str) -> str:
    return t(p, NAMA_PRESET_EN.get(p, p))


def _frek(f: str) -> str:
    return t(f, NAMA_FREK_EN[f])


def _pakai_preset() -> None:
    if (p := st.session_state.get("hs_preset")) in PRESET:
        st.session_state["hs_rentang"] = PRESET[p]


def panel_filter():
    st.session_state.setdefault("hs_rentang", PRESET["3 bulan"])
    with st.container(key="card_hs_filter"):
        st.html(judul_kartu(t("Filter Data", "Data Filter"), f"dataset {tanggal_pendek(MULAI, tahun=True)} – "
                                                       f"{tanggal_pendek(AKHIR, tahun=True)}"))
        st.html(f'<div class="fLbl">{t("Stasiun", "Station")}</div>')
        stasiun = st.pills("Stasiun", daftar_stasiun, selection_mode="multi", default=daftar_stasiun,
                           key="hs_stasiun", label_visibility="collapsed")
        c1, c2, c3 = st.columns([1.15, 1.25, 1], gap="medium")
        with c1:
            st.html(f'<div class="fLbl">{t("Periode cepat", "Quick period")}</div>')
            st.pills("Periode", list(PRESET), key="hs_preset", on_change=_pakai_preset, format_func=_preset,
                     label_visibility="collapsed")
            st.html(f'<div class="fLbl">{t("Rentang tanggal", "Date range")}</div>')
            rentang = st.date_input("Rentang tanggal", key="hs_rentang", min_value=MULAI, max_value=AKHIR,
                                    format="DD/MM/YYYY", label_visibility="collapsed",
                                    on_change=lambda: st.session_state.update(hs_preset=None))
        with c2:
            st.html(f'<div class="fLbl">{t("Kategori ISPU", "ISPU category")} <span class="fOpsi">'
                    f'{t("kosong = semua", "empty = all")}</span></div>')
            kategori = st.pills("Kategori", hs.URUTAN_KATEGORI, selection_mode="multi", key="hs_kategori",
                                format_func=nama_kategori, label_visibility="collapsed")
        with c3:
            st.html(f'<div class="fLbl">{t("Tampilan", "View")}</div>')
            frek = st.segmented_control("Tampilan", list(hs.FREKUENSI), default="Harian", key="hs_frek",
                                        format_func=_frek, label_visibility="collapsed") or "Harian"
            diisi = st.toggle(t("Sertakan data diisi", "Include filled data"), key="hs_diisi",
                              help=t("Nilai PM2.5 hasil pengisian data kosong (forward fill, maks. 7 hari).",
                                     "PM2.5 values from filling missing data (forward fill, max. 7 days)."))
    # saat baru memilih tanggal awal, date_input mengembalikan 1 tanggal saja
    mulai = rentang[0] if len(rentang) > 0 else MULAI
    akhir = rentang[1] if len(rentang) > 1 else AKHIR
    return stasiun or [], (mulai, akhir), kategori or [], frek, diisi


def baris_kpi(data: pd.DataFrame) -> None:
    r = hs.ringkasan(data)
    k = kategori_ispu(r["rata"])
    p, lo = r["puncak"], r["terendah"]
    st.html(kpi([
        (t("Rata-rata PM2.5", "Mean PM2.5"), f'{angka(r["rata"], 1)}',
         f'ISPU · {t("kategori", "category")} {nama_kategori(k["kategori"])}'),
        (t("Tertinggi", "Highest"), f'{int(p["pm25"])}',
         f'{p["stasiun"].split()[0]} · {tanggal_pendek(p["tanggal"], tahun=True)}'),
        (t("Terendah", "Lowest"), f'{int(lo["pm25"])}',
         f'{lo["stasiun"].split()[0]} · {tanggal_pendek(lo["tanggal"], tahun=True)}'),
        (t("Hari Baik/Sedang", "Good/Moderate Days"), f'{angka(r["persen_baik_sedang"], 1)}%',
         t(f'dari {angka(r["n"])} hari-stasiun', f'of {angka(r["n"])} station-days')),
    ], ispu=[r["rata"], p["pm25"], lo["pm25"], None]))


# --- halaman ------------------------------------------------------------
judul(t("Data Historis", "Historical Data"),
      t("Jelajahi indeks ISPU PM2.5 harian dari dataset penelitian",
        "Explore the daily PM2.5 ISPU index of the research dataset"))
stasiun, (mulai, akhir), kategori, frek, diisi = panel_filter()

data = hs.saring(sd.dataset(), stasiun, mulai, akhir, kategori, diisi) if stasiun else pd.DataFrame()
ket_filter = (f'{len(stasiun)} {t("stasiun", "stations")} · {tanggal_panjang(mulai)} – {tanggal_panjang(akhir)}'
              + (f' · {t("kategori", "category")} {", ".join(map(nama_kategori, kategori))}' if kategori else ""))
st.html(f'<div class="filterInfo"><span class="dot"></span>{ket_filter}</div>')

if data.empty:
    st.html(kosong(t("Tidak ada data yang cocok dengan filter", "No data matches the filter"),
                   t("Pilih minimal satu stasiun, perluas rentang tanggal, atau kosongkan filter kategori.",
                     "Choose at least one station, widen the date range, or clear the category filter.")))
    st.stop()

baris_kpi(data)

label(t("Tren PM2.5", "PM2.5 Trend") + f" · {_frek(frek).lower()}")
with st.container(key="card_hs_tren"):
    grafik_historis(hs.agregasi(data, frek), stasiun, key="grafik_hs")
    catatan = t("Garis putus-putus menandai ambang kategori ISPU. Stasiun dibedakan dengan nada dan pola garis.",
                "Dashed lines mark ISPU category thresholds. Stations differ by shade and line pattern.")
    if frek != "Harian":
        catatan += t(f" Nilai {frek.lower()} adalah rata-rata harian dalam periode tersebut.",
                     f" {_frek(frek)} values are the mean of daily values in that period.")
    if kategori:
        catatan += t(" Filter kategori diterapkan per hari sebelum dirata-rata.",
                     " The category filter is applied per day before averaging.")
    st.html(f'<div class="note">{catatan}</div>')

kiri, kanan = st.columns([1, 1], gap="medium")
with kiri:
    label(t("Distribusi Kategori per Stasiun", "Category Distribution per Station"))
    with st.container(key="card_hs_distribusi"):
        grafik_distribusi(hs.distribusi_kategori(data), key="grafik_hs_dist")
        st.html('<div class="note">' + t("Persentase hari pada tiap kategori ISPU selama periode terpilih.",
                                         "Share of days in each ISPU category during the selected period.")
                + '</div>')
with kanan:
    label(t("Rata-rata Bulanan", "Monthly Average"))
    with st.container(key="card_hs_bulanan"):
        tabel_rata_bulanan(hs.rata_bulanan(data))
        st.html('<div class="note">' + t("Rata-rata indeks ISPU per bulan; warna sel mengikuti kategori ISPU.",
                                         "Mean ISPU index per month; cell colors follow the ISPU category.")
                + '</div>')

label(t("Tabel Data", "Data Table"))
with st.container(key="card_hs_tabel"):
    st.html(judul_kartu(t("Data Harian", "Daily Data"), t(f"{angka(len(data))} baris", f"{angka(len(data))} rows")))
    tampil = data.assign(
        tanggal=data["tanggal"].dt.date,
        stasiun=data["stasiun"],
        kategori=data["kategori"].map(nama_kategori),
        keterangan=data["pm25_asli"].map({True: "", False: t("data diisi", "filled data")}),
    )[["tanggal", "stasiun", "pm25", "kategori", "keterangan"]]
    st.dataframe(tampil, hide_index=True, width="stretch", height=320, column_config={
        "tanggal": st.column_config.DateColumn(t("Tanggal", "Date"), format="DD/MM/YYYY"),
        "stasiun": st.column_config.TextColumn(t("Stasiun", "Station")),
        "pm25": st.column_config.NumberColumn("PM2.5 (ISPU)", format="%d"),
        "kategori": st.column_config.TextColumn(t("Kategori", "Category")),
        "keterangan": st.column_config.TextColumn(t("Keterangan", "Note")),
    })
    st.download_button(t("Unduh data terfilter (.csv)", "Download filtered data (.csv)"), hs.ke_csv(data), file_name="pm25_historis_terfilter.csv",
                       mime="text/csv", key="unduh_historis", icon=":material/download:")
    if n_diisi := int((~data["pm25_asli"]).sum()):
        st.html('<div class="note">' + t(f"{n_diisi} baris bertanda <i>data diisi</i> berasal dari pengisian "
                                         "data kosong (forward fill).",
                                         f"{n_diisi} rows marked <i>filled data</i> come from filling missing "
                                         "data (forward fill).") + '</div>')
