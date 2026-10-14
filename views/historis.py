"""Halaman Data Historis — jelajahi PM2.5 dataset dengan filter stasiun, rentang tanggal, kategori, dan agregasi."""
import pandas as pd
import streamlit as st

from components import sumber_data as sd
from components.format import angka, tanggal_panjang, tanggal_pendek
from components.grafik import grafik_distribusi, grafik_historis
from components.kartu import judul_kartu, kosong, kpi
from components.tabel import tabel_rata_bulanan
from components.tema import judul, label
from core import historis as hs
from core.config import STASIUN, kategori_ispu

daftar_stasiun = list(STASIUN)
MULAI, AKHIR = (t.date() for t in sd.rentang_tanggal())
PRESET = {
    "Semua": (MULAI, AKHIR),
    "2024": (max(MULAI, pd.Timestamp("2024-01-01").date()), pd.Timestamp("2024-12-31").date()),
    "2025": (pd.Timestamp("2025-01-01").date(), AKHIR),
    "3 bulan": ((pd.Timestamp(AKHIR) - pd.DateOffset(months=3) + pd.Timedelta(days=1)).date(), AKHIR),
    "30 hari": ((pd.Timestamp(AKHIR) - pd.Timedelta(days=29)).date(), AKHIR),
}


def _pakai_preset() -> None:
    if (p := st.session_state.get("hs_preset")) in PRESET:
        st.session_state["hs_rentang"] = PRESET[p]


def panel_filter():
    st.session_state.setdefault("hs_rentang", PRESET["3 bulan"])
    with st.container(key="card_hs_filter"):
        st.html(judul_kartu("Filter Data", "dataset 24 Jan 2024 – 8 Nov 2025"))
        st.html('<div class="fLbl">Stasiun</div>')
        stasiun = st.pills("Stasiun", daftar_stasiun, selection_mode="multi", default=daftar_stasiun,
                           key="hs_stasiun", label_visibility="collapsed")
        c1, c2, c3 = st.columns([1.15, 1.25, 1], gap="medium")
        with c1:
            st.html('<div class="fLbl">Periode cepat</div>')
            st.pills("Periode", list(PRESET), key="hs_preset", on_change=_pakai_preset,
                     label_visibility="collapsed")
            st.html('<div class="fLbl">Rentang tanggal</div>')
            rentang = st.date_input("Rentang tanggal", key="hs_rentang", min_value=MULAI, max_value=AKHIR,
                                    format="DD/MM/YYYY", label_visibility="collapsed",
                                    on_change=lambda: st.session_state.update(hs_preset=None))
        with c2:
            st.html('<div class="fLbl">Kategori ISPU <span class="fOpsi">kosong = semua</span></div>')
            kategori = st.pills("Kategori", hs.URUTAN_KATEGORI, selection_mode="multi", key="hs_kategori",
                                label_visibility="collapsed")
        with c3:
            st.html('<div class="fLbl">Tampilan</div>')
            frek = st.segmented_control("Tampilan", list(hs.FREKUENSI), default="Harian", key="hs_frek",
                                        label_visibility="collapsed") or "Harian"
            diisi = st.toggle("Sertakan data diisi", key="hs_diisi",
                              help="Nilai PM2.5 hasil pengisian data kosong (forward fill, maks. 7 hari).")
    # saat baru memilih tanggal awal, date_input mengembalikan 1 tanggal saja
    mulai = rentang[0] if len(rentang) > 0 else MULAI
    akhir = rentang[1] if len(rentang) > 1 else AKHIR
    return stasiun or [], (mulai, akhir), kategori or [], frek, diisi


def baris_kpi(data: pd.DataFrame) -> None:
    r = hs.ringkasan(data)
    k = kategori_ispu(r["rata"])
    p, t = r["puncak"], r["terendah"]
    st.html(kpi([
        ("Rata-rata PM2.5", f'{angka(r["rata"], 1)}', f'ISPU · kategori {k["kategori"]}'),
        ("Tertinggi", f'{int(p["pm25"])}', f'{p["stasiun"].split()[0]} · {tanggal_pendek(p["tanggal"], tahun=True)}'),
        ("Terendah", f'{int(t["pm25"])}', f'{t["stasiun"].split()[0]} · {tanggal_pendek(t["tanggal"], tahun=True)}'),
        ("Hari Baik/Sedang", f'{angka(r["persen_baik_sedang"], 1)}%', f'dari {angka(r["n"])} hari-stasiun'),
    ], ispu=[r["rata"], p["pm25"], t["pm25"], None]))


# --- halaman ------------------------------------------------------------
judul("Data Historis", "Jelajahi indeks ISPU PM2.5 harian dari dataset penelitian")
stasiun, (mulai, akhir), kategori, frek, diisi = panel_filter()

data = hs.saring(sd.dataset(), stasiun, mulai, akhir, kategori, diisi) if stasiun else pd.DataFrame()
ket_filter = (f'{len(stasiun)} stasiun · {tanggal_panjang(mulai)} – {tanggal_panjang(akhir)}'
              + (f' · kategori {", ".join(kategori)}' if kategori else ""))
st.html(f'<div class="filterInfo"><span class="dot"></span>{ket_filter}</div>')

if data.empty:
    st.html(kosong("Tidak ada data yang cocok dengan filter",
                   "Pilih minimal satu stasiun, perluas rentang tanggal, atau kosongkan filter kategori."))
    st.stop()

baris_kpi(data)

label(f"Tren PM2.5 · {frek.lower()}")
with st.container(key="card_hs_tren"):
    grafik_historis(hs.agregasi(data, frek), stasiun, key="grafik_hs")
    catatan = "Garis putus-putus menandai ambang kategori ISPU. Stasiun dibedakan dengan nada dan pola garis."
    if frek != "Harian":
        catatan += f" Nilai {frek.lower()} adalah rata-rata harian dalam periode tersebut."
    if kategori:
        catatan += " Filter kategori diterapkan per hari sebelum dirata-rata."
    st.html(f'<div class="note">{catatan}</div>')

kiri, kanan = st.columns([1, 1], gap="medium")
with kiri:
    label("Distribusi Kategori per Stasiun")
    with st.container(key="card_hs_distribusi"):
        grafik_distribusi(hs.distribusi_kategori(data), key="grafik_hs_dist")
        st.html('<div class="note">Persentase hari pada tiap kategori ISPU selama periode terpilih.</div>')
with kanan:
    label("Rata-rata Bulanan")
    with st.container(key="card_hs_bulanan"):
        tabel_rata_bulanan(hs.rata_bulanan(data))
        st.html('<div class="note">Rata-rata indeks ISPU per bulan; warna sel mengikuti kategori ISPU.</div>')

label("Tabel Data")
with st.container(key="card_hs_tabel"):
    st.html(judul_kartu("Data Harian", f"{angka(len(data))} baris"))
    tampil = data.assign(
        tanggal=data["tanggal"].dt.date,
        stasiun=data["stasiun"],
        keterangan=data["pm25_asli"].map({True: "", False: "data diisi"}),
    )[["tanggal", "stasiun", "pm25", "kategori", "keterangan"]]
    st.dataframe(tampil, hide_index=True, width="stretch", height=320, column_config={
        "tanggal": st.column_config.DateColumn("Tanggal", format="DD/MM/YYYY"),
        "stasiun": st.column_config.TextColumn("Stasiun"),
        "pm25": st.column_config.NumberColumn("PM2.5 (ISPU)", format="%d"),
        "kategori": st.column_config.TextColumn("Kategori"),
        "keterangan": st.column_config.TextColumn("Keterangan"),
    })
    st.download_button("Unduh data terfilter (.csv)", hs.ke_csv(data), file_name="pm25_historis_terfilter.csv",
                       mime="text/csv", key="unduh_historis", icon=":material/download:")
    if n_diisi := int((~data["pm25_asli"]).sum()):
        st.html(f'<div class="note">{n_diisi} baris bertanda <i>data diisi</i> berasal dari pengisian data kosong '
                '(forward fill).</div>')
