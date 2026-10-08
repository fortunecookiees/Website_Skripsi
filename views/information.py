"""Halaman Information (L10.5) — penjelasan model, variabel, kategori ISPU, panduan, penyusun."""
import streamlit as st

from components import sumber_data as sd
from components.format import angka, tanggal_panjang
from components.tema import judul
from core.config import (EARLY_STOPPING, FITUR, FITUR_METEOROLOGI, FITUR_POLUTAN, FITUR_SPASIAL, FITUR_TURUNAN,
                         HORIZONS, KATEGORI_ISPU, LABEL_FITUR, N_ESTIMATORS_MAKS, N_EVALUASI_OPTIMASI, N_ITERASI,
                         N_PARTIKEL, RENTANG_PSO, SARAN_ISPU_PM25, STASIUN)

TAG_SPASIAL = "background:#e4e4e4;color:#1c1c1c"
TAG_NETRAL = "background:#f0f0f0;color:var(--sub)"
KELOMPOK = [("Spasial", FITUR_SPASIAL, TAG_SPASIAL), ("Meteorologi", FITUR_METEOROLOGI, TAG_NETRAL),
            ("Polutan", FITUR_POLUTAN, TAG_NETRAL), ("Turunan", FITUR_TURUNAN, "background:#edf1f3;color:var(--sub)")]
KET_HYPERPARAM = {
    "max_depth": "Kedalaman maksimum tiap pohon",
    "learning_rate": "Besar langkah pembaruan tiap pohon",
    "subsample": "Proporsi baris data per pohon",
    "colsample_bytree": "Proporsi fitur per pohon",
    "min_child_weight": "Bobot minimum pada simpul anak",
    "reg_alpha": "Regularisasi L1",
    "reg_lambda": "Regularisasi L2",
}
BILANGAN_BULAT = {"max_depth", "min_child_weight"}


def _bagian(judul_bagian: str, isi: str) -> None:
    st.html(f'<div class="section"><h3>{judul_bagian}</h3>{isi}</div>')


def _tag(teks: str, gaya: str) -> str:
    return f'<span class="tag" style="{gaya}">{teks}</span>'


def _nilai_param(nama: str, v: float) -> str:
    return angka(v) if nama in BILANGAN_BULAT else angka(v, 4).rstrip("0").rstrip(",")


def tentang() -> None:
    mulai, akhir = sd.rentang_tanggal()
    _bagian("Tentang Aplikasi", "<p>Aplikasi menampilkan prediksi indeks ISPU PM2.5 satu sampai tujuh hari ke depan "
            f"pada {len(STASIUN)} stasiun pemantauan kualitas udara DKI Jakarta. Prediksi dihasilkan oleh model XGBoost "
            "yang <i>hyperparameter</i>-nya dioptimasi menggunakan Particle Swarm Optimization, lalu dibandingkan "
            "dengan <i>hyperparameter</i> bawaan dan <i>hyperparameter</i> hasil Random Search.</p>")
    _bagian("Cara Kerja Sistem", "<p>Model dilatih terlebih dahulu di luar aplikasi menggunakan data "
            f"{tanggal_panjang(mulai)} sampai {tanggal_panjang(akhir)}. Hasil pelatihan disimpan sebagai "
            f"{len(HORIZONS)} berkas model, satu untuk setiap horizon: model t+h memprediksi PM2.5 hari ke-h "
            "berdasarkan kondisi hari ini. Aplikasi hanya memuat berkas tersebut dan melakukan inferensi, sehingga "
            "tidak ada proses pelatihan ulang saat aplikasi digunakan.</p>")


def spesifikasi() -> None:
    models = sd.model()
    pohon = " · ".join(f"t+{h}: {models[h]['model'].best_iteration + 1}" for h in HORIZONS)
    _bagian("Spesifikasi Model", f"""<div class="kv">
        <span>Algoritma</span><span><b>XGBoost</b> (regresi)</span>
        <span>Optimasi</span><span><b>PSO</b> — {N_PARTIKEL} partikel, {N_ITERASI} iterasi</span>
        <span>Pembanding</span><span><i>Hyperparameter</i> bawaan dan <b>Random Search</b>
            ({angka(N_EVALUASI_OPTIMASI)} evaluasi)</span>
        <span>Jumlah fitur masukan</span><span><b>{len(FITUR)} fitur</b></span>
        <span>Horizon prediksi</span><span><b>t+1 sampai t+{len(HORIZONS)}</b> ({len(HORIZONS)} model terpisah)</span>
        <span>Pembagian data</span><span>Kronologis <b>70 : 15 : 15</b> (latih : validasi : uji)</span>
        <span>Jumlah pohon</span><span>Maksimum {N_ESTIMATORS_MAKS}, <i>early stopping</i> {EARLY_STOPPING} putaran
            → terpakai {pohon}</span>
        <span>Satuan keluaran</span><span>Indeks <b>ISPU</b> (PermenLHK 14/2020)</span></div>""")

    best = sd.hasil_evaluasi()["best_pso"]
    baris = "".join(
        f'<tr><td><code>{p}</code></td><td>{KET_HYPERPARAM[p]}</td><td class="num"><b>{_nilai_param(p, best[p])}</b></td>'
        f'<td class="num">{_nilai_param(p, lo)} – {_nilai_param(p, hi)}</td></tr>'
        for p, (lo, hi) in RENTANG_PSO.items())
    _bagian("Hyperparameter Hasil PSO", '<table class="tbl"><tr><th>Parameter</th><th>Keterangan</th>'
            f'<th class="num">Nilai Terbaik</th><th class="num">Rentang Pencarian</th></tr>{baris}</table>'
            '<div class="note">Hyperparameter yang sama dipakai oleh ketujuh model horizon. Nilai diambil dari '
            '<code>best_pso</code> pada <code>hasil_evaluasi.json</code>.</div>')


def rincian_fitur() -> None:
    ringkas = "".join(
        f'<tr><td>{_tag(nama, gaya)}</td><td class="num">{len(daftar)}</td>'
        f'<td>{", ".join(LABEL_FITUR[f][0] for f in daftar)}</td></tr>' for nama, daftar, gaya in KELOMPOK)
    _bagian(f"Rincian {len(FITUR)} Fitur Masukan", '<table class="tbl"><tr><th>Kelompok</th><th class="num">Jumlah</th>'
            f'<th>Variabel</th></tr>{ringkas}</table><div class="note">Variabel spasial hanya memiliki satu nilai '
            'untuk setiap stasiun per tahun, sehingga berperan sebagai pembeda antarwilayah, bukan sebagai penyebab '
            'fluktuasi harian. Fitur turunan dihitung otomatis dari data historis dan tidak dapat diubah pengguna.</div>')

    kelompok_dari = {f: (nama, gaya) for nama, daftar, gaya in KELOMPOK for f in daftar}
    detail = "".join(
        f'<tr><td class="num">{i}</td><td>{LABEL_FITUR[f][0]}</td><td><code>{f}</code></td>'
        f'<td>{LABEL_FITUR[f][1]}</td><td>{_tag(*kelompok_dari[f])}</td></tr>' for i, f in enumerate(FITUR, 1))
    with st.expander("Lihat rincian per variabel (urutan masukan model)"):
        st.html('<table class="tbl"><tr><th class="num">#</th><th>Variabel</th><th>Kolom</th><th>Satuan</th>'
                f'<th>Kelompok</th></tr>{detail}</table>')


def variabel_spasial() -> None:
    ns = sd.nilai_spasial()
    tahun = sorted(ns["tahun"].unique())
    kepala = "".join(f'<th class="num">Kepadatan {t}</th>' for t in tahun) + \
        "".join(f'<th class="num">RTH {t}</th>' for t in tahun)
    baris = []
    for stasiun, info in STASIUN.items():
        d = ns[ns["stasiun"] == stasiun].set_index("tahun")
        sel = "".join(f'<td class="num">{angka(d.loc[t, "kepadatan_penduduk_jiwa_km2"])}</td>' for t in tahun) + \
            "".join(f'<td class="num">{angka(d.loc[t, "luas_rth_km2"], 3)}</td>' for t in tahun)
        baris.append(f"<tr><td>{stasiun.split()[0]}</td><td>{info['kecamatan']}</td>{sel}</tr>")
    _bagian("Penjelasan Variabel Spasial", '<div class="two">'
            '<div class="infoCard sp"><div class="cardTitle">Luas RTH</div><p>Total luas ruang terbuka hijau pada '
            'kecamatan tempat stasiun berada, bersumber dari Satu Data Jakarta. Nilainya berbeda antarstasiun dan '
            'diperbarui setiap tahun.</p></div>'
            '<div class="infoCard sp"><div class="cardTitle">Kepadatan Penduduk</div><p>Jumlah penduduk per '
            'kilometer persegi pada kecamatan tempat stasiun berada, bersumber dari BPS. Sama seperti RTH, nilainya '
            'diperbarui setiap tahun.</p></div></div>'
            '<div style="margin-top:14px"><table class="tbl"><tr><th>Stasiun</th><th>Kecamatan</th>'
            f'{kepala}</tr>{"".join(baris)}</table><div class="note">Kepadatan dalam jiwa/km², luas RTH dalam km². '
            'Nilai diambil dari dataset yang dipakai model.</div></div>')


def kategori_ispu() -> None:
    baris = []
    for batas, nama, rentang, warna, bg, teks in KATEGORI_ISPU:
        sensitif, umum = SARAN_ISPU_PM25[nama]
        baris.append(f'<tr><td><span class="tag" style="background:{bg};color:{teks}">{nama}</span></td>'
                     f'<td class="num">{rentang}</td><td><i style="display:inline-block;width:9px;height:9px;'
                     f'border-radius:3px;background:{warna}"></i></td><td>{sensitif or "–"}</td><td>{umum}</td></tr>')
    _bagian("Kategori ISPU", '<table class="tbl"><tr><th>Kategori</th><th class="num">Rentang</th><th>Warna</th>'
            f'<th>Kelompok Sensitif</th><th>Setiap Orang</th></tr>{"".join(baris)}</table>'
            '<div class="note">Rentang dan rekomendasi tindakan untuk PM2.5 mengacu pada PermenLHK No. P.14/2020 '
            'tentang Indeks Standar Pencemar Udara.</div>')


def panduan() -> None:
    _bagian("Panduan Penggunaan", """<ol>
        <li>Buka halaman <b>Dashboard</b> dan pilih stasiun. <b>Mode Aktual</b> menampilkan prediksi 7 hari ke depan
            dari kondisi terakhir dataset, ringkasan kelima stasiun, dan peta lokasi.</li>
        <li>Pilih <b>Mode Simulasi</b> untuk menggeser nilai variabel spasial, meteorologi, dan polutan, lalu
            bandingkan hasilnya dengan mode aktual. Hasil simulasi bukan prediksi kondisi sebenarnya. Tombol
            <i>Kembalikan ke nilai aktual</i> mengembalikan semua nilai.</li>
        <li>Buka halaman <b>Evaluation</b>, pilih stasiun dan tanggal acuan pada periode uji untuk membandingkan
            prediksi dengan nilai aktual. Bagian bawah halaman menampilkan metrik seluruh data uji, perbandingan
            metode optimasi, kontribusi variabel, dan pengaruh variabel spasial.</li>
    </ol>""")


def penyusun() -> None:
    _bagian("Penyusun", """<div class="kv">
        <span>Nama</span><span><b>Fortuna</b> — 535230144</span>
        <span>Program Studi</span><span>Teknik Informatika, Universitas Tarumanagara</span>
        <span>Pembimbing</span><span>Pak Tony · Pak Manatap</span></div>""")


judul("Informasi Sistem", "Penjelasan model, variabel, dan panduan penggunaan aplikasi")
tentang()
spesifikasi()
rincian_fitur()
variabel_spasial()
kategori_ispu()
panduan()
penyusun()
