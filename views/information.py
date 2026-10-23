"""Halaman Information (L10.5) — penjelasan model, variabel, kategori ISPU, panduan, penyusun."""
import streamlit as st

from components import sumber_data as sd
from components.bahasa import kategori, label_fitur, saran, t
from components.format import angka, tanggal_panjang
from components.logo import NAMA, judul_skripsi
from components.tema import judul
from core.config import (EARLY_STOPPING, FITUR, FITUR_METEOROLOGI, FITUR_POLUTAN, FITUR_SPASIAL, FITUR_TURUNAN,
                         HORIZONS, KATEGORI_ISPU, N_ESTIMATORS_MAKS, N_EVALUASI_OPTIMASI, N_ITERASI,
                         N_PARTIKEL, RENTANG_PSO, ROOT, STASIUN)

MANUAL_PATH = ROOT / "assets" / "manual_program.pdf"  # ditaruh manual oleh penyusun

TAG_SPASIAL = "background:#ddeaf2;color:#22352c"
TAG_NETRAL = "background:#ecf3f8;color:var(--sub)"
KELOMPOK = [(("Spasial", "Spatial"), FITUR_SPASIAL, TAG_SPASIAL),
            (("Meteorologi", "Meteorological"), FITUR_METEOROLOGI, TAG_NETRAL),
            (("Polutan", "Pollutants"), FITUR_POLUTAN, TAG_NETRAL),
            (("Turunan", "Derived"), FITUR_TURUNAN, "background:#edf1ef;color:var(--sub)")]
KET_HYPERPARAM = {
    "max_depth": ("Kedalaman maksimum tiap pohon", "Maximum depth of each tree"),
    "learning_rate": ("Besar langkah pembaruan tiap pohon", "Step size of each tree update"),
    "subsample": ("Proporsi baris data per pohon", "Share of data rows per tree"),
    "colsample_bytree": ("Proporsi fitur per pohon", "Share of features per tree"),
    "min_child_weight": ("Bobot minimum pada simpul anak", "Minimum weight in a child node"),
    "reg_alpha": ("Regularisasi L1", "L1 regularization"),
    "reg_lambda": ("Regularisasi L2", "L2 regularization"),
}
BILANGAN_BULAT = {"max_depth", "min_child_weight"}


PENYUSUN = ("Fortuna Arleo Sahara", "535230144")
PEMBIMBING = [(("Pembimbing 1", "Supervisor 1"), "Tony, S.Kom., M.Kom., Ph.D."),
              (("Pembimbing 2", "Supervisor 2"), "Manatap Dolok Lauro, S.Kom., M.M.S.I.")]
# (judul ID/EN, ikon material, isi ID/EN) untuk kartu panduan bernomor
LANGKAH = [
    (("Dashboard", "Dashboard"), "space_dashboard",
     ("Pilih stasiun. <b>Mode Aktual</b> menampilkan prediksi 7 hari dari kondisi terakhir dataset, ringkasan "
      "kelima stasiun, dan peta lokasi.",
      "Choose a station. <b>Actual Mode</b> shows the 7-day forecast from the latest dataset condition, a summary "
      "of all five stations, and a location map.")),
    (("Mode Simulasi", "Simulation Mode"), "tune",
     ("Ubah nilai variabel spasial, cuaca, dan polutan, lalu klik <b>Prediksi</b> untuk membandingkannya dengan "
      "mode aktual. Hasil simulasi bukan prediksi kondisi sebenarnya.",
      "Change the spatial, weather, and pollutant values, then click <b>Predict</b> to compare with actual mode. "
      "Simulation results are not forecasts of real conditions.")),
    (("Data Historis", "Historical Data"), "monitoring",
     ("Saring stasiun, rentang tanggal, dan kategori ISPU, ubah tampilan harian, mingguan, atau bulanan, lalu unduh "
      "data yang sudah difilter.",
      "Filter by station, date range, and ISPU category, switch between daily, weekly, or monthly views, then "
      "download the filtered data.")),
    (("Evaluation", "Evaluation"), "fact_check",
     ("Pilih stasiun dan tanggal acuan pada periode uji untuk membandingkan prediksi dengan nilai aktual, lalu lihat "
      "metrik kinerja model.",
      "Choose a station and a reference date in the test period to compare predictions with actual values, then "
      "review the model performance metrics.")),
    (("Unggah Data", "Upload Data"), "upload_file",
     ("Masuk atau daftar, unduh template, isi data harian terbaru, lalu unggah untuk mendapat prediksi 7 hari. "
      "File minimal 11 hari juga membuka tab <i>Validasi</i>.",
      "Sign in or register, download the template, fill in the latest daily data, then upload it to get a 7-day "
      "forecast. Files with at least 11 days also unlock the <i>Validation</i> tab.")),
]


def _bagian(judul_bagian: str, isi: str) -> None:
    st.html(f'<div class="section"><h3>{judul_bagian}</h3>{isi}</div>')


def _baris(kunci: str, *isi) -> None:
    """Beberapa bagian berdampingan dengan tinggi sama (lihat CSS st-key-baris_info)."""
    with st.container(key=f"baris_info_{kunci}"):
        for kol, fungsi in zip(st.columns(len(isi), gap="medium"), isi):
            with kol:
                fungsi()


def _tag(teks: str, gaya: str) -> str:
    return f'<span class="tag" style="{gaya}">{teks}</span>'


def _nilai_param(nama: str, v: float) -> str:
    return angka(v) if nama in BILANGAN_BULAT else angka(v, 4).rstrip("0").rstrip(",.")


def tentang() -> None:
    _bagian(t("Tentang Aplikasi", "About the App"), "<p>" + t(
        f"<b>{NAMA}</b> menampilkan prediksi indeks ISPU PM2.5 satu sampai tujuh hari ke depan pada {len(STASIUN)} "
        "stasiun pemantauan kualitas udara DKI Jakarta. Prediksi dihasilkan oleh model XGBoost yang "
        "<i>hyperparameter</i>-nya dioptimasi menggunakan Particle Swarm Optimization, lalu dibandingkan dengan "
        "<i>hyperparameter</i> bawaan dan <i>hyperparameter</i> hasil Random Search.",
        f"<b>{NAMA}</b> shows the PM2.5 ISPU index forecast one to seven days ahead at {len(STASIUN)} air quality "
        "monitoring stations in DKI Jakarta. Forecasts come from an XGBoost model whose <i>hyperparameters</i> are "
        "optimized with Particle Swarm Optimization, and compared with default <i>hyperparameters</i> and those "
        "found by Random Search.") + "</p>")


def cara_kerja() -> None:
    mulai, akhir = sd.rentang_tanggal()
    n = len(HORIZONS)
    _bagian(t("Cara Kerja Sistem", "How the System Works"), "<p>" + t(
        f"Model dilatih terlebih dahulu di luar aplikasi menggunakan data {tanggal_panjang(mulai)} sampai "
        f"{tanggal_panjang(akhir)}. Hasil pelatihan disimpan sebagai {n} berkas model, satu untuk setiap horizon: "
        "model t+h memprediksi PM2.5 hari ke-h berdasarkan kondisi hari ini. Aplikasi hanya memuat berkas tersebut "
        "dan melakukan inferensi, sehingga tidak ada proses pelatihan ulang saat aplikasi digunakan.",
        f"The models were trained outside the app using data from {tanggal_panjang(mulai)} to "
        f"{tanggal_panjang(akhir)}. Training produced {n} model files, one per horizon: model t+h predicts PM2.5 "
        "on day h from today's conditions. The app only loads these files and runs inference, so no retraining "
        "happens while the app is used.") + "</p>")


def spesifikasi() -> None:
    models = sd.model()
    pohon = " · ".join(f"t+{h}: {models[h]['model'].best_iteration + 1}" for h in HORIZONS)
    n = len(HORIZONS)
    baris = [
        (t("Algoritma", "Algorithm"), t("<b>XGBoost</b> (regresi)", "<b>XGBoost</b> (regression)")),
        (t("Optimasi", "Optimization"), t(f"<b>PSO</b> — {N_PARTIKEL} partikel, {N_ITERASI} iterasi",
                                          f"<b>PSO</b> — {N_PARTIKEL} particles, {N_ITERASI} iterations")),
        (t("Pembanding", "Baselines"), t(f"<i>Hyperparameter</i> bawaan dan <b>Random Search</b> "
                                         f"({angka(N_EVALUASI_OPTIMASI)} evaluasi)",
                                         f"Default <i>hyperparameters</i> and <b>Random Search</b> "
                                         f"({angka(N_EVALUASI_OPTIMASI)} evaluations)")),
        (t("Jumlah fitur masukan", "Input features"), t(f"<b>{len(FITUR)} fitur</b>", f"<b>{len(FITUR)} features</b>")),
        (t("Horizon prediksi", "Forecast horizon"), t(f"<b>t+1 sampai t+{n}</b> ({n} model terpisah)",
                                                      f"<b>t+1 to t+{n}</b> ({n} separate models)")),
        (t("Pembagian data", "Data split"), t("Kronologis <b>70 : 15 : 15</b> (latih : validasi : uji)",
                                              "Chronological <b>70 : 15 : 15</b> (train : validation : test)")),
        (t("Jumlah pohon", "Number of trees"), t(f"Maksimum {N_ESTIMATORS_MAKS}, <i>early stopping</i> "
                                                 f"{EARLY_STOPPING} putaran → terpakai {pohon}",
                                                 f"Maximum {N_ESTIMATORS_MAKS}, <i>early stopping</i> "
                                                 f"{EARLY_STOPPING} rounds → used {pohon}")),
        (t("Satuan keluaran", "Output unit"), t("Indeks <b>ISPU</b> (PermenLHK 14/2020)",
                                                "<b>ISPU</b> index (PermenLHK 14/2020)")),
    ]
    _bagian(t("Spesifikasi Model", "Model Specification"),
            '<div class="kv">' + "".join(f"<span>{k}</span><span>{v}</span>" for k, v in baris) + "</div>")


def hyperparameter() -> None:
    best = sd.hasil_evaluasi()["best_pso"]
    baris = "".join(
        f'<tr><td><code>{p}</code></td><td>{t(*KET_HYPERPARAM[p])}</td>'
        f'<td class="num"><b>{_nilai_param(p, best[p])}</b></td>'
        f'<td class="num">{_nilai_param(p, lo)} – {_nilai_param(p, hi)}</td></tr>'
        for p, (lo, hi) in RENTANG_PSO.items())
    _bagian(t("Hyperparameter Hasil PSO", "PSO Hyperparameters"),
            f'<table class="tbl"><tr><th>Parameter</th><th>{t("Keterangan", "Description")}</th>'
            f'<th class="num">{t("Nilai Terbaik", "Best Value")}</th>'
            f'<th class="num">{t("Rentang Pencarian", "Search Range")}</th></tr>{baris}</table>'
            '<div class="note">' + t("Hyperparameter yang sama dipakai oleh ketujuh model horizon. Nilai diambil dari "
                                     "<code>best_pso</code> pada <code>hasil_evaluasi.json</code>.",
                                     "The same hyperparameters are used by all seven horizon models. Values are "
                                     "taken from <code>best_pso</code> in <code>hasil_evaluasi.json</code>.")
            + "</div>")


def rincian_fitur() -> None:
    ringkas = "".join(
        f'<tr><td>{_tag(t(*nama), gaya)}</td><td class="num">{len(daftar)}</td>'
        f'<td>{", ".join(label_fitur(f)[0] for f in daftar)}</td></tr>' for nama, daftar, gaya in KELOMPOK)
    _bagian(t(f"Rincian {len(FITUR)} Fitur Masukan", f"The {len(FITUR)} Input Features"),
            f'<table class="tbl"><tr><th>{t("Kelompok", "Group")}</th><th class="num">{t("Jumlah", "Count")}</th>'
            f'<th>{t("Variabel", "Variables")}</th></tr>{ringkas}</table><div class="note">'
            + t("Variabel spasial hanya memiliki satu nilai untuk setiap stasiun per tahun, sehingga berperan sebagai "
                "pembeda antarwilayah, bukan sebagai penyebab fluktuasi harian. Fitur turunan dihitung otomatis dari "
                "data historis dan tidak dapat diubah pengguna.",
                "Spatial variables have a single value per station per year, so they distinguish areas rather than "
                "drive daily fluctuations. Derived features are computed automatically from historical data and "
                "cannot be changed by users.") + "</div>")


def rincian_per_variabel() -> None:
    kelompok_dari = {f: (t(*nama), gaya) for nama, daftar, gaya in KELOMPOK for f in daftar}
    detail = "".join(
        f'<tr><td class="num">{i}</td><td>{label_fitur(f)[0]}</td><td><code>{f}</code></td>'
        f'<td>{label_fitur(f)[1]}</td><td>{_tag(*kelompok_dari[f])}</td></tr>' for i, f in enumerate(FITUR, 1))
    with st.expander(t("Lihat rincian per variabel (urutan masukan model)",
                       "See details per variable (model input order)")):
        st.html(f'<table class="tbl"><tr><th class="num">#</th><th>{t("Variabel", "Variable")}</th>'
                f'<th>{t("Kolom", "Column")}</th><th>{t("Satuan", "Unit")}</th><th>{t("Kelompok", "Group")}</th>'
                f'</tr>{detail}</table>')


def variabel_spasial() -> None:
    ns = sd.nilai_spasial()
    tahun = sorted(ns["tahun"].unique())
    kepala = "".join(f'<th class="num">{t("Kepadatan", "Density")} {th}</th>' for th in tahun) + \
        "".join(f'<th class="num">{t("RTH", "GOS")} {th}</th>' for th in tahun)
    baris = []
    for stasiun, info in STASIUN.items():
        d = ns[ns["stasiun"] == stasiun].set_index("tahun")
        sel = "".join(f'<td class="num">{angka(d.loc[th, "kepadatan_penduduk_jiwa_km2"])}</td>' for th in tahun) + \
            "".join(f'<td class="num">{angka(d.loc[th, "luas_rth_km2"], 3)}</td>' for th in tahun)
        baris.append(f"<tr><td>{stasiun.split()[0]}</td><td>{info['kecamatan']}</td>{sel}</tr>")
    _bagian(t("Penjelasan Variabel Spasial", "Spatial Variables"), '<div class="two">'
            f'<div class="infoCard sp"><div class="cardTitle">{t("Luas RTH", "Green Open Space (GOS) Area")}</div><p>'
            + t("Total luas ruang terbuka hijau pada kecamatan tempat stasiun berada, bersumber dari Satu Data "
                "Jakarta. Nilainya berbeda antarstasiun dan diperbarui setiap tahun.",
                "Total green open space area in the district where the station is located, from Satu Data Jakarta. "
                "Values differ between stations and are updated yearly.") + '</p></div>'
            f'<div class="infoCard sp"><div class="cardTitle">{t("Kepadatan Penduduk", "Population Density")}</div><p>'
            + t("Jumlah penduduk per kilometer persegi pada kecamatan tempat stasiun berada, bersumber dari BPS. Sama "
                "seperti RTH, nilainya diperbarui setiap tahun.",
                "Number of residents per square kilometre in the station's district, from BPS (Statistics "
                "Indonesia). Like GOS, values are updated yearly.") + '</p></div></div>'
            f'<div style="margin-top:14px"><table class="tbl"><tr><th>{t("Stasiun", "Station")}</th>'
            f'<th>{t("Kecamatan", "District")}</th>{kepala}</tr>{"".join(baris)}</table><div class="note">'
            + t("Kepadatan dalam jiwa/km², luas RTH dalam km². Nilai diambil dari dataset yang dipakai model.",
                "Density in people/km², GOS area in km². Values are taken from the dataset used by the model.")
            + "</div></div>")


def tabel_kategori_ispu() -> None:
    baris = []
    for batas, nama, rentang, warna, bg, teks in KATEGORI_ISPU:
        sensitif, umum = saran(nama)
        baris.append(f'<tr><td><span class="tag" style="background:{bg};color:{teks}">{kategori(nama)}</span></td>'
                     f'<td class="num">{rentang}</td><td><i style="display:inline-block;width:9px;height:9px;'
                     f'border-radius:3px;background:{warna}"></i></td><td>{sensitif or "–"}</td><td>{umum}</td></tr>')
    _bagian(t("Kategori ISPU", "ISPU Categories"),
            f'<table class="tbl"><tr><th>{t("Kategori", "Category")}</th><th class="num">{t("Rentang", "Range")}</th>'
            f'<th>{t("Warna", "Color")}</th><th>{t("Kelompok Sensitif", "Sensitive Groups")}</th>'
            f'<th>{t("Setiap Orang", "Everyone")}</th></tr>{"".join(baris)}</table><div class="note">'
            + t("Rentang dan rekomendasi tindakan untuk PM2.5 mengacu pada PermenLHK No. P.14/2020 tentang Indeks "
                "Standar Pencemar Udara.",
                "Ranges and recommended actions for PM2.5 follow Indonesian Ministry of Environment and Forestry "
                "Regulation No. P.14/2020 on the Air Pollutant Standard Index (ISPU).") + "</div>")


def panduan() -> None:
    """Kartu langkah bernomor 01-05 + kartu Manual Program, 3 per baris."""
    st.html(f'<div class="secHead"><h2 class="title">{t("Panduan Penggunaan", "User Guide")}</h2><div class="subt">'
            f'{t("Lima langkah utama memakai aplikasi", "Five main steps to use the app")}</div></div>')
    kartu = [(i, *l) for i, l in enumerate(LANGKAH, 1)] + [None]
    for mulai in range(0, len(kartu), 3):
        with st.container(key=f"baris_info_panduan_{mulai}"):
            for kol, item in zip(st.columns(3, gap="medium"), kartu[mulai:mulai + 3]):
                with kol:
                    if item is None:
                        manual_program()
                        continue
                    no, nama, ikon, isi = item
                    with st.container(key=f"pandu_{no}"):
                        st.html(f'<div class="pdNo">{no:02d}</div><div class="pdIkon"><span class="material-symbols-'
                                f'rounded">{ikon}</span></div><div class="pdJudul">{t(*nama)}</div>'
                                f'<p class="pdIsi">{t(*isi)}</p>')


def manual_program() -> None:
    """Tombol unduh assets/manual_program.pdf; jika berkas belum ada, tampilkan info tanpa tombol."""
    with st.container(key="card_manual"):
        st.html('<div class="pdIkon"><span class="material-symbols-rounded">menu_book</span></div>'
                f'<div class="pdJudul">{t("Manual Program", "User Manual")}</div><p class="pdIsi">'
                + t("Panduan lengkap dalam format PDF, berisi langkah penggunaan setiap halaman beserta tampilannya.",
                    "The complete guide in PDF, with usage steps and screenshots for every page.") + "</p>")
        if MANUAL_PATH.is_file():
            st.download_button(t("Unduh Manual Program (PDF)", "Download User Manual (PDF)"), MANUAL_PATH.read_bytes(),
                               file_name="Manual_Program_NafasKota.pdf", mime="application/pdf",
                               icon=":material/download:", key="unduh_manual", width="stretch")
        else:
            st.html('<div class="infoBox"><span class="dot"></span><span>'
                    + t("Manual program belum tersedia.", "The user manual is not available yet.") + "</span></div>")


def penyusun() -> None:
    nama, nim = PENYUSUN
    prodi = t("Teknik Informatika, Universitas Tarumanagara", "Informatics Engineering, Tarumanagara University")
    inisial = "".join(k[0] for k in nama.split()[:2])
    bimbing = "".join(f'<div class="pbKartu"><span class="pbLabel">{t(*label)}</span><b>{n}</b></div>'
                      for label, n in PEMBIMBING)
    st.html(f'<div class="penyusun"><div class="pyKiri"><div class="pyAtas"><div class="pyAvatar">{inisial}</div><div>'
            f'<div class="pyLabel">{t("Penyusun", "Author")}</div><div class="pyNama">{nama}</div>'
            f'<div class="pyMeta">{t("NIM", "Student ID")} {nim} · {prodi}</div></div></div><div class="pyJudul">'
            f'<span>{t("Judul skripsi", "Thesis title")}</span>{judul_skripsi()}</div></div>'
            f'<div class="pyKanan">{bimbing}</div></div>')


judul(t("Informasi Sistem", "System Information"),
      t("Penjelasan model, variabel, dan panduan penggunaan aplikasi",
        "Model, variables, and a guide to using the app"))
penyusun()
_baris("1", tentang, cara_kerja)
panduan()
tabel_kategori_ispu()
_baris("2", spesifikasi, hyperparameter)
_baris("3", rincian_fitur, variabel_spasial)
rincian_per_variabel()
