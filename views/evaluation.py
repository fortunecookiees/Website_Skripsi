"""Halaman Evaluation — prediksi vs aktual per tanggal (L10.3) & metrik seluruh data uji (L10.4)."""
import pandas as pd
import streamlit as st

from components import sumber_data as sd
from components.bahasa import kategori, t
from components.format import angka, tanggal_pendek
from components.grafik import grafik_optimasi, grafik_sekitar_acuan
from components.kartu import judul_kartu, kosong, kpi
from components.pilih_tanggal import pilih_tanggal
from components.tabel_evaluasi import (catatan_diisi, legend_sekitar_acuan, tabel_importance, tabel_metrik,
                                       tabel_optimasi, tabel_prediksi_vs_aktual, tabel_skenario)
from components.tema import judul, label
from core.config import HORIZONS, KATEGORI_ISPU, N_EVALUASI_OPTIMASI, STASIUN, kategori_ispu
from core.metrik import metrik_panjang

JENDELA_HARI = 7  # rentang grafik: acuan - 7 hari s.d. acuan + 7 hari
KUNCI_HASIL = "eval_hasil"  # ((stasiun, tanggal acuan), baris data uji + pred_h1..h7)
daftar_stasiun = list(STASIUN)


def bagian_prediksi() -> None:
    label(t("Pilih Stasiun", "Choose Station"))
    pilihan = st.pills("Pilih Stasiun", daftar_stasiun, default=daftar_stasiun[0],
                       key="eval_stasiun", label_visibility="collapsed")
    stasiun = pilihan or st.session_state.get("eval_stasiun_terakhir", daftar_stasiun[0])
    st.session_state["eval_stasiun_terakhir"] = stasiun

    uji = sd.data_uji()
    uji_st = uji[uji["stasiun"] == stasiun].set_index("tanggal", drop=False)
    label(t("Tanggal Acuan", "Reference Date"))
    acuan, kolom_hint = pilih_tanggal(list(uji_st.index), prefix="eval")
    baris = uji_st.loc[acuan]

    k = kategori_ispu(baris["pm25"])
    diisi = "" if baris["pm25_asli"] else t(" (data diisi)", " (filled data)")
    kolom_hint.html(f'<div class="stepHint">{t("PM2.5 aktual hari acuan", "Actual PM2.5 on the reference date")}: '
                    f'<b>{k["nilai"]} ISPU</b>{diisi} · {kategori(k["kategori"])}</div>')

    # model hanya dijalankan saat tombol Prediksi diklik; hasil berlaku untuk pasangan stasiun + tanggal itu
    pilihan_ini = (stasiun, acuan)
    if st.button(t("Prediksi", "Predict"), type="primary", key="eval_prediksi"):
        with st.spinner(t("Menghitung prediksi…", "Computing forecast…")):
            st.session_state[KUNCI_HASIL] = (pilihan_ini, sd.prediksi_baris_uji(baris))
    hasil = st.session_state.get(KUNCI_HASIL)
    if hasil is None or hasil[0] != pilihan_ini:
        with st.container(key="card_eval_tabel"):
            st.html(judul_kartu(t("Prediksi vs Aktual — 7 Horizon", "Predicted vs Actual — 7 Horizons"),
                                t("belum dihitung", "not computed yet"))
                    + '<div class="simKosong">' + t(
                        "Pilih stasiun dan tanggal acuan, lalu klik <b>Prediksi</b> untuk membandingkan prediksi "
                        "model t+1 … t+7 dengan nilai aktualnya.",
                        "Choose a station and reference date, then click <b>Predict</b> to compare the t+1 … t+7 "
                        "predictions with their actual values.") + '</div>')
        return
    baris = hasil[1]

    data = sd.dataset()
    sekitar = data[(data["stasiun"] == stasiun)
                   & data["tanggal"].between(acuan - pd.Timedelta(days=JENDELA_HARI),
                                             acuan + pd.Timedelta(days=JENDELA_HARI))].dropna(subset=["pm25"])
    prediksi = pd.DataFrame({"tanggal": [acuan + pd.Timedelta(days=h) for h in HORIZONS],
                             "pm25": [baris[f"pred_h{h}"] for h in HORIZONS]})

    # tabel & grafik berdampingan, sama tinggi (CSS st-key-baris_*)
    with st.container(key="baris_eval_acuan"):
        kiri, kanan = st.columns([1.1, 1], gap="medium")
        with kiri, st.container(key="card_eval_tabel"):
            st.html(judul_kartu(t("Prediksi vs Aktual — 7 Horizon", "Predicted vs Actual — 7 Horizons")))
            tabel_prediksi_vs_aktual(baris)
            if not all(baris[f"target_h{h}_asli"] for h in HORIZONS):
                st.html(f'<div class="note">{catatan_diisi()}</div>')
        with kanan, st.container(key="card_eval_grafik"):
            st.html(judul_kartu(t("Grafik PM2.5 di Sekitar Tanggal Acuan", "PM2.5 Around the Reference Date"),
                                t(f"±{JENDELA_HARI} hari", f"±{JENDELA_HARI} days")))
            grafik_sekitar_acuan(sekitar, acuan, prediksi, key="grafik_eval", tinggi=300)
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
    st.html(f'<div class="secHead"><h2 class="title">{t("Jelajahi Prediksi Data Uji", "Explore Test Predictions")}'
            '</h2><div class="subt">' + t("Saring seluruh prediksi periode uji berdasarkan stasiun, horizon, tanggal "
                                          "acuan, dan kategori nilai aktual",
                                          "Filter all test-period predictions by station, horizon, reference date, "
                                          "and actual-value category") + '</div></div>')
    with st.container(key="card_eval_filter"):
        st.html(judul_kartu("Filter", f"{tanggal_pendek(mulai)} – {tanggal_pendek(tgl.max(), tahun=True)}"))
        with st.form("form_jelajah", border=False):
            c1, c2 = st.columns([1.3, 1], gap="medium")
            with c1:
                st.html(f'<div class="fLbl">{t("Stasiun", "Station")}</div>')
                f_st = st.pills("Stasiun", daftar_stasiun, selection_mode="multi", default=daftar_stasiun,
                                key="jl_stasiun", label_visibility="collapsed")
                st.html('<div class="fLbl">Horizon</div>')
                f_h = st.pills("Horizon", HORIZONS, selection_mode="multi", default=HORIZONS, key="jl_horizon",
                               format_func=lambda h: f"t+{h}", label_visibility="collapsed")
            with c2:
                st.html(f'<div class="fLbl">{t("Rentang tanggal acuan", "Reference date range")}</div>')
                f_tgl = st.date_input("Rentang tanggal acuan", (mulai.date(), tgl.max().date()), key="jl_tanggal",
                                      min_value=mulai.date(), max_value=tgl.max().date(), format="DD/MM/YYYY",
                                      label_visibility="collapsed")
                st.html(f'<div class="fLbl">{t("Kategori nilai aktual", "Actual-value category")}</div>')
                f_k = st.multiselect("Kategori", hs_kategori(), key="jl_kategori", format_func=kategori,
                                     placeholder=t("Semua kategori", "All categories"), label_visibility="collapsed")
                f_asli = st.toggle(t("Sembunyikan nilai aktual data diisi", "Hide filled actual values"), value=True,
                                   key="jl_asli")
            kirim = st.form_submit_button(t("Terapkan filter", "Apply filter"), type="primary",
                                          icon=":material/filter_alt:")
    if kirim:
        st.session_state["eval_jelajah"] = {
            "stasiun": f_st or [], "horizon": f_h or [], "kategori": f_k or [], "hanya_asli": f_asli,
            "mulai": f_tgl[0] if len(f_tgl) > 0 else mulai, "akhir": f_tgl[1] if len(f_tgl) > 1 else tgl.max()}
    f = st.session_state.get("eval_jelajah")
    if f is None:
        st.html(kosong(t("Filter belum diterapkan", "No filter applied yet"),
                       t("Atur filter lalu klik <b>Terapkan filter</b> untuk menghitung dan menampilkan prediksi.",
                         "Set the filters, then click <b>Apply filter</b> to compute and show predictions.")))
        return
    with st.spinner(t("Menghitung prediksi seluruh data uji…", "Computing predictions for all test data…")):
        p = sd.prediksi_uji_panjang()
    d = _saring_uji(p, f)
    if d.empty:
        st.html(kosong(t("Tidak ada prediksi yang cocok", "No matching predictions"),
                       t("Longgarkan filter stasiun, horizon, tanggal, atau kategori.",
                         "Loosen the station, horizon, date, or category filters.")))
        return

    m = metrik_panjang(d)
    st.html(kpi([
        (t("Jumlah prediksi", "Predictions"), angka(len(d)),
         t(f'{d["stasiun"].nunique()} stasiun · {d["horizon"].nunique()} horizon',
           f'{d["stasiun"].nunique()} stations · {d["horizon"].nunique()} horizons')),
        ("MAE", angka(m["MAE"], 2) if m["n"] else "–", t(f'dari {angka(m["n"])} nilai aktual asli',
                                                        f'from {angka(m["n"])} original actual values')),
        ("RMSE", angka(m["RMSE"], 2) if m["n"] else "–", t("akar rata-rata kuadrat galat", "root mean squared error")),
        ("MAPE", f'{angka(m["MAPE"], 1)}%' if m["MAPE"] is not None else "–",
         t("rata-rata galat relatif", "mean relative error")),
    ]))
    per_h = []
    for h in sorted(d["horizon"].unique()):
        mh = metrik_panjang(d[d["horizon"] == h])
        per_h.append(f'<tr><td>t+{h}</td><td class="num">{angka(mh["n"])}</td>'
                     f'<td class="num">{angka(mh["MAE"], 2) if mh["n"] else "–"}</td>'
                     f'<td class="num">{angka(mh["RMSE"], 2) if mh["n"] else "–"}</td></tr>')
    kiri, kanan = st.columns([1, 2.2], gap="medium")
    with kiri, st.container(key="card_eval_perh"):
        st.html(judul_kartu(t("Per Horizon", "By Horizon"), t("hasil filter", "filtered")) + '<table class="tbl"><tr><th>Horizon</th>'
                '<th class="num">n</th><th class="num">MAE</th><th class="num">RMSE</th></tr>'
                f'{"".join(per_h)}</table>')
    with kanan, st.container(key="card_eval_baris"):
        st.html(judul_kartu(t("Daftar Prediksi", "Prediction List"), t(f"{angka(len(d))} baris", f"{angka(len(d))} rows")))
        tampil = pd.DataFrame({
            "stasiun": d["stasiun"].str.split().str[0], "acuan": d["tanggal_acuan"].dt.date,
            "horizon": "t+" + d["horizon"].astype(str), "target": d["tanggal_target"].dt.date,
            "prediksi": d["prediksi"].map(lambda v: kategori_ispu(v)["nilai"]),
            "aktual": d["aktual"].map(lambda v: kategori_ispu(v)["nilai"]),
            "kategori": d["kategori_aktual"].map(kategori),
            "ket": d["asli"].map({True: "", False: t("data diisi", "filled data")})})
        tampil["selisih"] = tampil["prediksi"] - tampil["aktual"]
        st.dataframe(tampil[["stasiun", "acuan", "horizon", "target", "prediksi", "aktual", "selisih", "kategori", "ket"]],
                     hide_index=True, width="stretch", height=330, column_config={
                         "stasiun": t("Stasiun", "Station"),
                         "acuan": st.column_config.DateColumn(t("Tanggal acuan", "Reference date"), format="DD/MM/YYYY"),
                         "horizon": "Horizon",
                         "target": st.column_config.DateColumn(t("Tanggal target", "Target date"), format="DD/MM/YYYY"),
                         "prediksi": st.column_config.NumberColumn(t("Prediksi", "Predicted"), format="%d"),
                         "aktual": st.column_config.NumberColumn(t("Aktual", "Actual"), format="%d"),
                         "selisih": st.column_config.NumberColumn(t("Selisih", "Difference"), format="%+d"),
                         "kategori": t("Kategori aktual", "Actual category"), "ket": t("Keterangan", "Note")})
        st.download_button(t("Unduh hasil filter (.csv)", "Download filtered results (.csv)"), tampil.to_csv(index=False).encode("utf-8-sig"),
                           file_name="prediksi_data_uji_terfilter.csv", mime="text/csv", key="unduh_jelajah",
                           icon=":material/download:")
    st.html('<div class="note">' + t(
        "Metrik dihitung dari nilai prediksi sebelum dibulatkan dan hanya memakai nilai aktual asli, sama seperti "
        "metrik seluruh data uji di bawah. Tabel menampilkan nilai ISPU yang sudah dibulatkan.",
        "Metrics use predictions before rounding and only original actual values, like the full test-set metrics "
        "below. The table shows rounded ISPU values.") + '</div>')


def hs_kategori() -> list[str]:
    return [nama for _, nama, *_ in KATEGORI_ISPU]


def bagian_metrik() -> None:
    ev = sd.hasil_evaluasi()
    st.html(f'<div class="secHead"><h2 class="title">{t("Kinerja Model", "Model Performance")}</h2>'
            '<div class="subt">' + t("Kinerja model pada seluruh data uji dan kontribusi variabel masukan",
                                     "Model performance on the full test set and input variable contributions")
            + '</div></div>')

    # 2 baris x 2 kolom; pasangan dipilih yang tingginya mirip, lalu kartu disamakan tingginya lewat CSS
    with st.container(key="baris_kinerja_1"):
        kiri, kanan = st.columns(2, gap="medium")
        with kiri:
            label(t("Metrik Evaluasi Seluruh Data Uji", "Evaluation Metrics on All Test Data"))
            with st.container(key="card_eval_metrik"):
                catatan = tabel_metrik(ev)
                st.html(f'<div class="note">{catatan}</div>')
        with kanan:
            label(t("Pengaruh Variabel Spasial (RMSE Data Uji)", "Effect of Spatial Variables (Test RMSE)"))
            with st.container(key="card_eval_skenario"):
                catatan = tabel_skenario(sd.hasil_skenario())
                st.html(f'<div class="note">{catatan} ' + t("Sumber: keluaran Google Colab",
                                                            "Source: Google Colab output of")
                        + ' <code>train/training.py</code> ' + t("(bagian 10).", "(section 10).") + '</div>')

    with st.container(key="baris_kinerja_2"):
        kiri, kanan = st.columns(2, gap="medium")
        with kiri:
            label(t("Perbandingan Metode Optimasi (RMSE Data Uji)", "Optimization Method Comparison (Test RMSE)"))
            with st.container(key="card_eval_optimasi"):
                grafik_optimasi(ev, key="grafik_optimasi")
                tabel_optimasi(ev)
                n_ev = angka(N_EVALUASI_OPTIMASI)
                st.html('<div class="note">' + t(
                    f"Random Search dan PSO menggunakan ruang pencarian dan jumlah evaluasi yang sama, yaitu {n_ev} "
                    "evaluasi. Makin rendah garis, makin kecil error-nya; nilai tebal menunjukkan RMSE terkecil pada "
                    "setiap horizon.",
                    f"Random Search and PSO use the same search space and the same number of evaluations ({n_ev}). "
                    "Lower lines mean smaller errors; bold values mark the lowest RMSE at each horizon.") + '</div>')
        with kanan:
            label(t("Kontribusi Variabel (10 Teratas, Horizon t+1)", "Variable Contribution (Top 10, Horizon t+1)"))
            with st.container(key="card_eval_importance"):
                catatan = tabel_importance(sd.feature_importance(1))
                st.html(f'<div class="note">{catatan} ' + t(
                    "Nilai kontribusi adalah <i>feature importance</i> tipe <i>gain</i> dari model t+1.",
                    "Contribution is the <i>gain</i>-type <i>feature importance</i> of the t+1 model.") + '</div>')


judul(t("Evaluasi Model", "Model Evaluation"),
      t("Perbandingan nilai prediksi dan nilai aktual pada data historis",
        "Comparing predicted and actual values on historical data"))
bagian_prediksi()
bagian_jelajah()
bagian_metrik()
