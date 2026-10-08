"""Halaman Evaluation — prediksi vs aktual per tanggal (L10.3) & metrik seluruh data uji (L10.4)."""
import pandas as pd
import streamlit as st

from components import sumber_data as sd
from components.format import angka, tanggal_panjang
from components.grafik import grafik_sekitar_acuan
from components.kartu import judul_kartu
from components.tabel_evaluasi import (tabel_importance, tabel_metrik, tabel_optimasi, tabel_prediksi_vs_aktual,
                                       tabel_skenario)
from components.tema import judul, label
from core.config import HORIZONS, N_EVALUASI_OPTIMASI, STASIUN, kategori_ispu

JENDELA_HARI = 7  # rentang grafik: acuan - 7 hari s.d. acuan + 7 hari
KUNCI_TANGGAL = "eval_tanggal"
daftar_stasiun = list(STASIUN)


def _geser(daftar: list, langkah: int) -> None:
    i = daftar.index(st.session_state[KUNCI_TANGGAL])
    st.session_state[KUNCI_TANGGAL] = daftar[min(max(i + langkah, 0), len(daftar) - 1)]


def pilih_tanggal(daftar: list[pd.Timestamp]):
    """Stepper tanggal acuan (tombol ‹ › + daftar tanggal uji). Mengembalikan (tanggal, kolom keterangan)."""
    if st.session_state.get(KUNCI_TANGGAL) not in daftar:
        st.session_state[KUNCI_TANGGAL] = daftar[-1]
    i = daftar.index(st.session_state[KUNCI_TANGGAL])
    c1, c2, c3, c4 = st.columns([0.35, 2.2, 0.35, 5], vertical_alignment="center", gap="small")
    c1.button("‹", key="eval_geser_mundur", on_click=_geser, args=(daftar, -1), disabled=i == 0,
              help="Tanggal sebelumnya")
    c2.selectbox("Tanggal acuan", daftar, key=KUNCI_TANGGAL, format_func=tanggal_panjang,
                 label_visibility="collapsed")
    c3.button("›", key="eval_geser_maju", on_click=_geser, args=(daftar, 1), disabled=i == len(daftar) - 1,
              help="Tanggal berikutnya")
    return st.session_state[KUNCI_TANGGAL], c4


def bagian_prediksi() -> None:
    label("Pilih Stasiun")
    pilihan = st.pills("Pilih Stasiun", daftar_stasiun, default=daftar_stasiun[0],
                       key="eval_stasiun", label_visibility="collapsed")
    stasiun = pilihan or st.session_state.get("eval_stasiun_terakhir", daftar_stasiun[0])
    st.session_state["eval_stasiun_terakhir"] = stasiun

    uji = sd.prediksi_uji()
    uji_st = uji[uji["stasiun"] == stasiun].set_index("tanggal", drop=False)
    label("Tanggal Acuan")
    acuan, kolom_hint = pilih_tanggal(list(uji_st.index))
    baris = uji_st.loc[acuan]

    k = kategori_ispu(baris["pm25"])
    diisi = "" if baris["pm25_asli"] else " (data diisi)"
    kolom_hint.html(f'<div class="stepHint">PM2.5 aktual hari acuan: <b>{k["nilai"]} ISPU</b>{diisi} · '
                    f'{k["kategori"]}</div>')

    with st.container(key="card_eval_tabel"):
        st.html(judul_kartu("Prediksi vs Aktual — 7 Horizon"))
        tabel_prediksi_vs_aktual(baris)
        if not all(baris[f"target_h{h}_asli"] for h in HORIZONS):
            st.html('<div class="note">Nilai bertanda <i>data diisi</i> berasal dari pengisian data kosong '
                    '(forward fill), sehingga tidak dihitung kesalahannya, sama seperti perhitungan metrik saat '
                    'pelatihan yang hanya memakai nilai asli.</div>')

    label("Grafik PM2.5 di Sekitar Tanggal Acuan")
    data = sd.dataset()
    sekitar = data[(data["stasiun"] == stasiun)
                   & data["tanggal"].between(acuan - pd.Timedelta(days=JENDELA_HARI),
                                             acuan + pd.Timedelta(days=JENDELA_HARI))].dropna(subset=["pm25"])
    prediksi = pd.DataFrame({"tanggal": [acuan + pd.Timedelta(days=h) for h in HORIZONS],
                             "pm25": [baris[f"pred_h{h}"] for h in HORIZONS]})
    with st.container(key="card_eval_grafik"):
        grafik_sekitar_acuan(sekitar, acuan, prediksi, key="grafik_eval")
        legend = ['<span><i style="background:#1c1c1c"></i>Nilai aktual</span>',
                  '<span><i style="background:#8c8c8c"></i>Nilai prediksi (t+1 … t+7)</span>']
        if not sekitar["pm25_asli"].all():
            legend.append('<span><i style="background:#fff;border:1.5px solid #1c1c1c;border-radius:50%"></i>'
                          'Titik berongga: data diisi</span>')
        st.html(f'<div class="legend">{"".join(legend)}</div>')


def bagian_metrik() -> None:
    ev = sd.hasil_evaluasi()
    st.html('<div class="secHead"><h2 class="title">Kinerja Model</h2><div class="subt">Kinerja model pada '
            'seluruh data uji dan kontribusi variabel masukan</div></div>')

    label("Metrik Evaluasi Seluruh Data Uji")
    with st.container(key="card_eval_metrik"):
        catatan = tabel_metrik(ev)
        st.html(f'<div class="note">{catatan}</div>')

    label("Perbandingan Metode Optimasi (RMSE Data Uji)")
    with st.container(key="card_eval_optimasi"):
        tabel_optimasi(ev)
        st.html('<div class="note">Random Search dan PSO menggunakan ruang pencarian dan jumlah evaluasi yang sama, '
                f'yaitu {angka(N_EVALUASI_OPTIMASI)} evaluasi. Nilai tebal menunjukkan RMSE terkecil pada setiap '
                'horizon.</div>')

    label("Kontribusi Variabel (10 Teratas, Horizon t+1)")
    with st.container(key="card_eval_importance"):
        catatan = tabel_importance(sd.feature_importance(1))
        st.html(f'<div class="note">{catatan} Nilai kontribusi adalah <i>feature importance</i> tipe '
                '<i>gain</i> dari model t+1.</div>')

    label("Pengaruh Variabel Spasial (RMSE Data Uji)")
    with st.container(key="card_eval_skenario"):
        catatan = tabel_skenario(sd.hasil_skenario())
        st.html(f'<div class="note">{catatan} Sumber: keluaran Google Colab <code>train/training.py</code> '
                '(bagian 10).</div>')


judul("Evaluasi Model", "Perbandingan nilai prediksi dan nilai aktual pada data historis")
bagian_prediksi()
bagian_metrik()
