"""Halaman Evaluation — prediksi vs aktual per tanggal (L10.3) & metrik seluruh data uji (L10.4)."""
import pandas as pd
import streamlit as st

from components import sumber_data as sd
from components.format import angka, tanggal_pendek
from components.grafik import grafik_sekitar_acuan
from components.kartu import judul_kartu, kosong, kpi
from components.pilih_tanggal import pilih_tanggal
from components.tabel_evaluasi import (CATATAN_DIISI, legend_sekitar_acuan, tabel_importance, tabel_metrik,
                                       tabel_optimasi, tabel_prediksi_vs_aktual, tabel_skenario)
from components.tema import judul, label
from core.config import HORIZONS, KATEGORI_ISPU, N_EVALUASI_OPTIMASI, STASIUN, kategori_ispu
from core.metrik import metrik_panjang

JENDELA_HARI = 7  # rentang grafik: acuan - 7 hari s.d. acuan + 7 hari
KUNCI_HASIL = "eval_hasil"  # ((stasiun, tanggal acuan), baris data uji + pred_h1..h7)
daftar_stasiun = list(STASIUN)


def bagian_prediksi() -> None:
    label("Pilih Stasiun")
    pilihan = st.pills("Pilih Stasiun", daftar_stasiun, default=daftar_stasiun[0],
                       key="eval_stasiun", label_visibility="collapsed")
    stasiun = pilihan or st.session_state.get("eval_stasiun_terakhir", daftar_stasiun[0])
    st.session_state["eval_stasiun_terakhir"] = stasiun

    uji = sd.data_uji()
    uji_st = uji[uji["stasiun"] == stasiun].set_index("tanggal", drop=False)
    label("Tanggal Acuan")
    acuan, kolom_hint = pilih_tanggal(list(uji_st.index), prefix="eval")
    baris = uji_st.loc[acuan]

    k = kategori_ispu(baris["pm25"])
    diisi = "" if baris["pm25_asli"] else " (data diisi)"
    kolom_hint.html(f'<div class="stepHint">PM2.5 aktual hari acuan: <b>{k["nilai"]} ISPU</b>{diisi} · '
                    f'{k["kategori"]}</div>')

    # model hanya dijalankan saat tombol Prediksi diklik; hasil berlaku untuk pasangan stasiun + tanggal itu
    pilihan_ini = (stasiun, acuan)
    if st.button("Prediksi", type="primary", key="eval_prediksi"):
        with st.spinner("Menghitung prediksi…"):
            st.session_state[KUNCI_HASIL] = (pilihan_ini, sd.prediksi_baris_uji(baris))
    hasil = st.session_state.get(KUNCI_HASIL)
    if hasil is None or hasil[0] != pilihan_ini:
        with st.container(key="card_eval_tabel"):
            st.html(judul_kartu("Prediksi vs Aktual — 7 Horizon", "belum dihitung")
                    + '<div class="simKosong">Pilih stasiun dan tanggal acuan, lalu klik <b>Prediksi</b> untuk '
                    'membandingkan prediksi model t+1 … t+7 dengan nilai aktualnya.</div>')
        return
    baris = hasil[1]

    with st.container(key="card_eval_tabel"):
        st.html(judul_kartu("Prediksi vs Aktual — 7 Horizon"))
        tabel_prediksi_vs_aktual(baris)
        if not all(baris[f"target_h{h}_asli"] for h in HORIZONS):
            st.html(f'<div class="note">{CATATAN_DIISI}</div>')

    label("Grafik PM2.5 di Sekitar Tanggal Acuan")
    data = sd.dataset()
    sekitar = data[(data["stasiun"] == stasiun)
                   & data["tanggal"].between(acuan - pd.Timedelta(days=JENDELA_HARI),
                                             acuan + pd.Timedelta(days=JENDELA_HARI))].dropna(subset=["pm25"])
    prediksi = pd.DataFrame({"tanggal": [acuan + pd.Timedelta(days=h) for h in HORIZONS],
                             "pm25": [baris[f"pred_h{h}"] for h in HORIZONS]})
    with st.container(key="card_eval_grafik"):
        grafik_sekitar_acuan(sekitar, acuan, prediksi, key="grafik_eval")
        st.html(legend_sekitar_acuan(sekitar["pm25_asli"].all()))


def _saring_uji(p: pd.DataFrame, f: dict) -> pd.DataFrame:
    d = p[p["stasiun"].isin(f["stasiun"]) & p["horizon"].isin(f["horizon"])
          & p["tanggal_acuan"].between(pd.Timestamp(f["mulai"]), pd.Timestamp(f["akhir"]))]
    if f["hanya_asli"]:
        d = d[d["asli"]]
    d = d.assign(kategori_aktual=d["aktual"].map(lambda v: kategori_ispu(v)["kategori"]))
    if f["kategori"]:
        d = d[d["kategori_aktual"].isin(f["kategori"])]
    return d


def bagian_jelajah() -> None:
    """Seluruh prediksi data uji dengan filter; model dijalankan saat tombol Terapkan diklik (sekali, di-cache)."""
    mulai, akhir, _ = sd.periode_uji()
    tgl = sd.data_uji()["tanggal"]
    st.html('<div class="secHead"><h2 class="title">Jelajahi Prediksi Data Uji</h2><div class="subt">Saring seluruh '
            'prediksi periode uji berdasarkan stasiun, horizon, tanggal acuan, dan kategori nilai aktual</div></div>')
    with st.container(key="card_eval_filter"):
        st.html(judul_kartu("Filter", f"{tanggal_pendek(mulai)} – {tanggal_pendek(tgl.max(), tahun=True)}"))
        with st.form("form_jelajah", border=False):
            c1, c2 = st.columns([1.3, 1], gap="medium")
            with c1:
                st.html('<div class="fLbl">Stasiun</div>')
                f_st = st.pills("Stasiun", daftar_stasiun, selection_mode="multi", default=daftar_stasiun,
                                key="jl_stasiun", label_visibility="collapsed")
                st.html('<div class="fLbl">Horizon</div>')
                f_h = st.pills("Horizon", HORIZONS, selection_mode="multi", default=HORIZONS, key="jl_horizon",
                               format_func=lambda h: f"t+{h}", label_visibility="collapsed")
            with c2:
                st.html('<div class="fLbl">Rentang tanggal acuan</div>')
                f_tgl = st.date_input("Rentang tanggal acuan", (mulai.date(), tgl.max().date()), key="jl_tanggal",
                                      min_value=mulai.date(), max_value=tgl.max().date(), format="DD/MM/YYYY",
                                      label_visibility="collapsed")
                st.html('<div class="fLbl">Kategori nilai aktual</div>')
                f_k = st.multiselect("Kategori", hs_kategori(), key="jl_kategori", placeholder="Semua kategori",
                                     label_visibility="collapsed")
                f_asli = st.toggle("Sembunyikan nilai aktual data diisi", value=True, key="jl_asli")
            kirim = st.form_submit_button("Terapkan filter", type="primary", icon=":material/filter_alt:")
    if kirim:
        st.session_state["eval_jelajah"] = {
            "stasiun": f_st or [], "horizon": f_h or [], "kategori": f_k or [], "hanya_asli": f_asli,
            "mulai": f_tgl[0] if len(f_tgl) > 0 else mulai, "akhir": f_tgl[1] if len(f_tgl) > 1 else tgl.max()}
    f = st.session_state.get("eval_jelajah")
    if f is None:
        st.html(kosong("Filter belum diterapkan",
                       "Atur filter lalu klik <b>Terapkan filter</b> untuk menghitung dan menampilkan prediksi."))
        return
    with st.spinner("Menghitung prediksi seluruh data uji…"):
        p = sd.prediksi_uji_panjang()
    d = _saring_uji(p, f)
    if d.empty:
        st.html(kosong("Tidak ada prediksi yang cocok", "Longgarkan filter stasiun, horizon, tanggal, atau kategori."))
        return

    m = metrik_panjang(d)
    st.html(kpi([
        ("Jumlah prediksi", angka(len(d)), f'{d["stasiun"].nunique()} stasiun · {d["horizon"].nunique()} horizon'),
        ("MAE", angka(m["MAE"], 2) if m["n"] else "–", f'dari {angka(m["n"])} nilai aktual asli'),
        ("RMSE", angka(m["RMSE"], 2) if m["n"] else "–", "akar rata-rata kuadrat galat"),
        ("MAPE", f'{angka(m["MAPE"], 1)}%' if m["MAPE"] is not None else "–", "rata-rata galat relatif"),
    ]))
    per_h = []
    for h in sorted(d["horizon"].unique()):
        mh = metrik_panjang(d[d["horizon"] == h])
        per_h.append(f'<tr><td>t+{h}</td><td class="num">{angka(mh["n"])}</td>'
                     f'<td class="num">{angka(mh["MAE"], 2) if mh["n"] else "–"}</td>'
                     f'<td class="num">{angka(mh["RMSE"], 2) if mh["n"] else "–"}</td></tr>')
    kiri, kanan = st.columns([1, 2.2], gap="medium")
    with kiri, st.container(key="card_eval_perh"):
        st.html(judul_kartu("Per Horizon", "hasil filter") + '<table class="tbl"><tr><th>Horizon</th>'
                '<th class="num">n</th><th class="num">MAE</th><th class="num">RMSE</th></tr>'
                f'{"".join(per_h)}</table>')
    with kanan, st.container(key="card_eval_baris"):
        st.html(judul_kartu("Daftar Prediksi", f"{angka(len(d))} baris"))
        tampil = pd.DataFrame({
            "stasiun": d["stasiun"].str.split().str[0], "acuan": d["tanggal_acuan"].dt.date,
            "horizon": "t+" + d["horizon"].astype(str), "target": d["tanggal_target"].dt.date,
            "prediksi": d["prediksi"].map(lambda v: kategori_ispu(v)["nilai"]),
            "aktual": d["aktual"].map(lambda v: kategori_ispu(v)["nilai"]),
            "kategori": d["kategori_aktual"], "ket": d["asli"].map({True: "", False: "data diisi"})})
        tampil["selisih"] = tampil["prediksi"] - tampil["aktual"]
        st.dataframe(tampil[["stasiun", "acuan", "horizon", "target", "prediksi", "aktual", "selisih", "kategori", "ket"]],
                     hide_index=True, width="stretch", height=330, column_config={
                         "stasiun": "Stasiun", "acuan": st.column_config.DateColumn("Tanggal acuan", format="DD/MM/YYYY"),
                         "horizon": "Horizon", "target": st.column_config.DateColumn("Tanggal target", format="DD/MM/YYYY"),
                         "prediksi": st.column_config.NumberColumn("Prediksi", format="%d"),
                         "aktual": st.column_config.NumberColumn("Aktual", format="%d"),
                         "selisih": st.column_config.NumberColumn("Selisih", format="%+d"),
                         "kategori": "Kategori aktual", "ket": "Keterangan"})
        st.download_button("Unduh hasil filter (.csv)", tampil.to_csv(index=False).encode("utf-8-sig"),
                           file_name="prediksi_data_uji_terfilter.csv", mime="text/csv", key="unduh_jelajah",
                           icon=":material/download:")
    st.html('<div class="note">Metrik dihitung dari nilai prediksi sebelum dibulatkan dan hanya memakai nilai aktual '
            'asli, sama seperti metrik seluruh data uji di bawah. Tabel menampilkan nilai ISPU yang sudah dibulatkan.'
            '</div>')


def hs_kategori() -> list[str]:
    return [nama for _, nama, *_ in KATEGORI_ISPU]


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
bagian_jelajah()
bagian_metrik()
