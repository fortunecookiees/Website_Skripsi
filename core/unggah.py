"""Modul Unggah Data: template, pembacaan, validasi, dan prediksi dari data unggahan pengguna.

Data unggahan berdiri sendiri (tidak disambung ke dataset historis) dan hanya diproses di memori.
Preprocessing memakai core.preprocessing.preprocess() yang sama dengan training.
"""
import csv
import difflib
import io
import re
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from .config import (FITUR, FITUR_METEOROLOGI, FITUR_POLUTAN, FITUR_SPASIAL, HORIZONS, LABEL_FITUR,
                     LABEL_FITUR_EN, STASIUN, kategori_ispu)
from .inference import prediksi_7_hari, prediksi_batch
from .preprocessing import KOLOM_LAG, KOLOM_TARGET, kondisi_terakhir, preprocess
from .teks import tr

KOLOM_WAJIB = ["tanggal", "stasiun"] + FITUR_POLUTAN + FITUR_METEOROLOGI
KOLOM_ANGKA = FITUR_POLUTAN + FITUR_METEOROLOGI
MIN_HARI = 4            # hari t + 3 hari sebelumnya (lag 1–3 & rata-rata 3 hari)
MIN_HARI_VALIDASI = MIN_HARI + len(HORIZONS)  # + 7 hari nilai aktual t+1..t+7 = 11
MAKS_PESAN = 8          # batas pesan sejenis yang ditampilkan
_POLA_TANGGAL = re.compile(r"^\d{4}-\d{2}-\d{2}( 00:00(:00)?)?$")


@dataclass
class HasilUnggah:
    error: list[str] = field(default_factory=list)
    peringatan: list[str] = field(default_factory=list)
    info: list[str] = field(default_factory=list)
    kondisi: dict[str, pd.Series] = field(default_factory=dict)   # stasiun -> baris fitur hari terakhir
    prediksi: pd.DataFrame | None = None                          # stasiun, tanggal_dasar, tanggal, horizon, pm25, kategori
    data: pd.DataFrame | None = None        # data unggahan setelah preprocessing (untuk grafik validasi)
    validasi: pd.DataFrame | None = None    # tanggal acuan valid + pred_h1..h7 (lihat data_validasi)
    hari: dict[str, int] = field(default_factory=dict)              # stasiun -> jumlah hari di file
    dilewati_meteo: dict[str, int] = field(default_factory=dict)    # stasiun -> tanggal acuan dilewati

    @property
    def ok(self) -> bool:
        return not self.error and self.prediksi is not None


# ---------------------------------------------------------------------
# Utilitas
# ---------------------------------------------------------------------
def _ringkas(pesan: list[str]) -> list[str]:
    if len(pesan) <= MAKS_PESAN:
        return pesan
    n = len(pesan) - MAKS_PESAN
    return pesan[:MAKS_PESAN] + [tr(f"… dan {n} masalah sejenis lainnya.", f"… and {n} more similar issues.")]


def _nama(f: str) -> str:
    """Nama fitur untuk pesan, sesuai bahasa aktif."""
    return tr(LABEL_FITUR[f][0], LABEL_FITUR_EN.get(f, LABEL_FITUR[f])[0])


def _baris_excel(idx) -> str:
    return str(int(idx) + 2)  # +1 header, +1 indeks mulai 1


def _daftar_baris(idx_list) -> str:
    b = [_baris_excel(i) for i in idx_list]
    return ", ".join(b[:6]) + (f", … (+{len(b) - 6})" if len(b) > 6 else "")


def _tgl(t) -> str:
    return pd.Timestamp(t).strftime("%Y-%m-%d")


def _peta_stasiun() -> dict[str, str]:
    """Nama lengkap & kode (DKI1…) -> nama baku, tidak peka huruf besar/kecil & spasi."""
    peta = {}
    for nama in STASIUN:
        peta[" ".join(nama.lower().split())] = nama
        peta[nama.split()[0].lower()] = nama
    return peta


_TIDAK_VALID = "__tidak_valid__"


def _g(x: float) -> str:
    """Angka ringkas dengan desimal koma untuk pesan."""
    return f"{x:g}".replace(".", ",")


def _ke_angka(nilai):
    """Ubah sel ke float. Menerima desimal koma ('26,7') dan ribuan titik ('1.009,13'). _TIDAK_VALID jika gagal."""
    if nilai is None or (isinstance(nilai, float) and np.isnan(nilai)):
        return np.nan
    if isinstance(nilai, (int, float, np.number)) and not isinstance(nilai, bool):
        return float(nilai)
    s = str(nilai).strip().replace(" ", "")
    if s == "" or s == "-":
        return np.nan
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".") if s.rfind(",") > s.rfind(".") else s.replace(",", "")
    elif "," in s:
        s = s.replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return _TIDAK_VALID


# ---------------------------------------------------------------------
# Template
# ---------------------------------------------------------------------
def buat_template(dataset_mentah: pd.DataFrame, stasiun: str = "DKI1 Bundaran HI") -> bytes:
    """Excel template: sheet 'Data' berisi contoh 4 hari terakhir 1 stasiun dari dataset, sheet 'Petunjuk'."""
    contoh = (dataset_mentah[dataset_mentah["stasiun"] == stasiun].sort_values("tanggal")
              .tail(MIN_HARI)[KOLOM_WAJIB].copy())
    contoh["tanggal"] = pd.to_datetime(contoh["tanggal"]).dt.date

    petunjuk = pd.DataFrame(
        [{"kolom": "tanggal", "keterangan": "Tanggal pengamatan, format YYYY-MM-DD (berurutan, tanpa bolong)",
          "satuan": "-", "wajib": "Ya"},
         {"kolom": "stasiun", "keterangan": "Nama stasiun atau kode: " + "; ".join(STASIUN),
          "satuan": "-", "wajib": "Ya"}]
        + [{"kolom": f, "keterangan": LABEL_FITUR[f][0], "satuan": LABEL_FITUR[f][1],
            "wajib": "Ya (4 hari terakhir)" if f == "pm25" else
                     ("Ya (hari terakhir)" if f in FITUR_METEOROLOGI else "Boleh kosong")}
           for f in KOLOM_ANGKA])
    aturan = pd.DataFrame({"aturan": [
        f"Minimal {MIN_HARI} hari berturut-turut per stasiun; prediksi dihitung dari tanggal terakhir.",
        f"Untuk tab Validasi (prediksi vs aktual), unggah minimal {MIN_HARI_VALIDASI} hari berturut-turut: "
        f"{MIN_HARI} hari untuk lag + 7 hari nilai aktual.",
        "Boleh berisi sebagian stasiun saja; satu file boleh berisi beberapa stasiun.",
        "Kepadatan penduduk & luas RTH tidak perlu diisi (otomatis memakai nilai tahun terakhir dataset).",
        "Nilai di luar rentang dataset tetap diproses tetapi diberi peringatan.",
        "Data unggahan hanya dipakai selama sesi dan tidak disimpan.",
    ]})

    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        contoh.to_excel(w, sheet_name="Data", index=False)
        petunjuk.to_excel(w, sheet_name="Petunjuk", index=False)
        aturan.to_excel(w, sheet_name="Petunjuk", index=False, startrow=len(petunjuk) + 2)
        lembar = w.sheets["Data"]
        for sel in lembar["A"][1:]:
            sel.number_format = "yyyy-mm-dd"
        for kol in lembar.columns:
            lembar.column_dimensions[kol[0].column_letter].width = max(12, len(str(kol[0].value)) + 2)
        lp = w.sheets["Petunjuk"]
        for huruf, lebar in zip("ABCD", (24, 90, 14, 20)):
            lp.column_dimensions[huruf].width = lebar
    return buf.getvalue()


# ---------------------------------------------------------------------
# Membaca file
# ---------------------------------------------------------------------
def baca_file(isi: bytes, nama_file: str) -> pd.DataFrame:
    """Baca .xlsx/.csv menjadi DataFrame mentah (semua kolom apa adanya). ValueError jika gagal."""
    nama = nama_file.lower()
    if nama.endswith((".xlsx", ".xls")):
        try:
            return pd.read_excel(io.BytesIO(isi), sheet_name=0)
        except Exception as e:  # noqa: BLE001
            raise ValueError(tr(f"File Excel tidak dapat dibaca ({e}). Pastikan file berformat .xlsx.",
                                f"The Excel file could not be read ({e}). Make sure it is an .xlsx file.")) from e
    if nama.endswith(".csv"):
        for enc in ("utf-8-sig", "cp1252"):
            try:
                teks = isi.decode(enc)
                break
            except UnicodeDecodeError:
                continue
        else:
            raise ValueError(tr("File CSV tidak dapat dibaca: encoding tidak dikenali (gunakan UTF-8).",
                                "The CSV file could not be read: unknown encoding (use UTF-8)."))
        baris_awal = teks.splitlines()[0] if teks.strip() else ""
        try:
            pemisah = csv.Sniffer().sniff(baris_awal, delimiters=",;\t").delimiter
        except csv.Error:
            pemisah = ";" if baris_awal.count(";") > baris_awal.count(",") else ","
        # semua dibaca sebagai teks; angka berdesimal koma diubah di validasi()
        return pd.read_csv(io.StringIO(teks), sep=pemisah, dtype=str, keep_default_na=True)
    raise ValueError(tr("Format file tidak didukung. Unggah file .xlsx atau .csv.",
                        "Unsupported file format. Upload an .xlsx or .csv file."))


# ---------------------------------------------------------------------
# Validasi
# ---------------------------------------------------------------------
def validasi(mentah: pd.DataFrame) -> tuple[pd.DataFrame | None, list[str], list[str]]:
    """Periksa struktur & isi. Mengembalikan (data bersih atau None, error, info)."""
    error, info = [], []
    df = mentah.copy()
    df.columns = [str(c).strip().lower() for c in df.columns]
    df = df.dropna(how="all")
    if df.empty:
        return None, [tr("File tidak berisi data.", "The file contains no data.")], info

    # --- kolom ---
    kurang = [k for k in KOLOM_WAJIB if k not in df.columns]
    if kurang:
        lain = [c for c in df.columns if c not in KOLOM_WAJIB]
        saran = []
        for k in kurang:
            mirip = difflib.get_close_matches(k, lain, n=1, cutoff=0.6)
            mungkin = tr(f" (mungkin tertulis <code>{mirip[0]}</code>?)", f" (perhaps written as <code>{mirip[0]}</code>?)")
            saran.append(f"<code>{k}</code>" + (mungkin if mirip else ""))
        error.append(tr(f"Kolom wajib tidak ditemukan: {', '.join(saran)}. Gunakan nama kolom sesuai template.",
                        f"Required columns not found: {', '.join(saran)}. Use the column names from the template."))
        return None, error, info
    ekstra = [c for c in df.columns if c not in KOLOM_WAJIB]
    if ekstra:
        abai_spasial = [c for c in ekstra if c in FITUR_SPASIAL]
        abai_lain = [c for c in ekstra if c not in FITUR_SPASIAL]
        if abai_spasial:
            info.append(tr("Kolom kepadatan penduduk/luas RTH pada file diabaikan; aplikasi memakai nilai tahun "
                           "terakhir dari dataset.",
                           "Population density/green open space columns in the file are ignored; the app uses "
                           "the latest year from the dataset."))
        if abai_lain:
            info.append(tr(f"Kolom tambahan diabaikan: {', '.join(abai_lain)}.",
                           f"Extra columns ignored: {', '.join(abai_lain)}."))
    df = df[KOLOM_WAJIB]

    # --- tanggal ---
    tanggal, salah = [], []
    for idx, v in df["tanggal"].items():
        if isinstance(v, (pd.Timestamp, np.datetime64)) or hasattr(v, "year"):
            tanggal.append(pd.Timestamp(v).normalize())
        elif isinstance(v, str) and _POLA_TANGGAL.match(v.strip()):
            try:
                tanggal.append(pd.Timestamp(v.strip()[:10]))
            except ValueError:
                tanggal.append(pd.NaT)
                salah.append(tr(f"Baris {_baris_excel(idx)}: tanggal '{v}' tidak valid.",
                                f"Row {_baris_excel(idx)}: invalid date '{v}'."))
        else:
            tanggal.append(pd.NaT)
            isi = "" if pd.isna(v) else v
            salah.append(tr(f"Baris {_baris_excel(idx)}: tanggal '{isi}' tidak valid. Gunakan format YYYY-MM-DD, "
                            "contoh 2025-11-08.",
                            f"Row {_baris_excel(idx)}: invalid date '{isi}'. Use the YYYY-MM-DD format, e.g. "
                            "2025-11-08."))
    error += _ringkas(salah)
    df["tanggal"] = tanggal

    # --- stasiun ---
    peta = _peta_stasiun()
    asli = df["stasiun"].copy()
    df["stasiun"] = asli.map(lambda v: peta.get(" ".join(str(v).lower().split())) if pd.notna(v) else None)
    tak_dikenal = df["stasiun"].isna()
    salah_st = asli[tak_dikenal].fillna(tr("(kosong)", "(empty)")).astype(str)
    pilihan = ", ".join(f"{s} / {s.split()[0]}" for s in STASIUN)
    for nilai, grup in salah_st.groupby(salah_st, sort=False):
        baris = _daftar_baris(grup.index)
        error.append(tr(f"Stasiun '{nilai}' tidak dikenal (baris {baris}). Pilihan: {pilihan}.",
                        f"Unknown station '{nilai}' (row {baris}). Options: {pilihan}."))

    # --- angka ---
    salah = []
    for kol in KOLOM_ANGKA:
        hasil = pd.Series([_ke_angka(v) for v in df[kol]], index=df.index, dtype=object)
        tidak_valid = hasil.eq(_TIDAK_VALID)
        for idx in hasil[tidak_valid].index:
            salah.append(tr(f"Baris {_baris_excel(idx)}, kolom <code>{kol}</code>: '{df.at[idx, kol]}' bukan angka.",
                            f"Row {_baris_excel(idx)}, column <code>{kol}</code>: '{df.at[idx, kol]}' is not a "
                            "number."))
        hasil = pd.to_numeric(hasil.mask(tidak_valid), errors="coerce")
        for idx in hasil[hasil < 0].index:
            salah.append(tr(f"Baris {_baris_excel(idx)}, kolom <code>{kol}</code>: nilai negatif "
                            f"({_g(hasil[idx])}) tidak valid.",
                            f"Row {_baris_excel(idx)}, column <code>{kol}</code>: negative value "
                            f"({_g(hasil[idx])}) is not valid."))
        df[kol] = hasil
    error += _ringkas(salah)
    if error:
        return None, error, info

    # --- per stasiun: duplikat, bolong, jumlah hari, pm25 & meteorologi ---
    for st_nama, g in df.groupby("stasiun"):
        g = g.sort_values("tanggal")
        dup = g[g["tanggal"].duplicated(keep=False)]
        if not dup.empty:
            tgl = sorted({_tgl(t) for t in dup["tanggal"]})
            error.append(tr(f"{st_nama}: tanggal duplikat {', '.join(tgl)} (baris {_daftar_baris(dup.index)}).",
                            f"{st_nama}: duplicate dates {', '.join(tgl)} (rows {_daftar_baris(dup.index)})."))
            continue
        selisih = g["tanggal"].diff().dt.days
        for i in selisih[selisih > 1].index:
            sebelum = g["tanggal"].shift(1)[i]
            a, b = _tgl(sebelum), _tgl(g.at[i, "tanggal"])
            error.append(tr(f"{st_nama}: tanggal bolong antara {a} dan {b}. Data harus berurutan setiap hari.",
                            f"{st_nama}: missing dates between {a} and {b}. Data must be consecutive days."))
        if len(g) < MIN_HARI:
            error.append(tr(f"{st_nama}: hanya {len(g)} hari data; minimal {MIN_HARI} hari berturut-turut "
                            "(hari terakhir + 3 hari sebelumnya untuk lag PM2.5).",
                            f"{st_nama}: only {len(g)} days of data; at least {MIN_HARI} consecutive days are "
                            "needed (the last day + 3 previous days for the PM2.5 lags)."))
            continue
        akhir = g.tail(MIN_HARI)
        kosong = akhir[akhir["pm25"].isna()]
        if not kosong.empty:
            tgl_kosong = ", ".join(_tgl(t) for t in kosong["tanggal"])
            error.append(tr(f"{st_nama}: PM2.5 kosong pada {tgl_kosong}. PM2.5 wajib terisi pada {MIN_HARI} hari "
                            "terakhir karena dipakai untuk lag dan rata-rata 3 hari.",
                            f"{st_nama}: PM2.5 is empty on {tgl_kosong}. PM2.5 must be filled for the last "
                            f"{MIN_HARI} days because it is used for the lags and the 3-day average."))
        terakhir = g.iloc[-1]
        meteo_kosong = [k for k in FITUR_METEOROLOGI if pd.isna(terakhir[k])]
        if meteo_kosong:
            kol = ", ".join(f"<code>{k}</code>" for k in meteo_kosong)
            tgl_akhir = _tgl(terakhir["tanggal"])
            error.append(tr(f"{st_nama}: data meteorologi hari terakhir ({tgl_akhir}) kosong pada kolom {kol}. "
                            "Meteorologi hari terakhir wajib diisi.",
                            f"{st_nama}: weather data for the last day ({tgl_akhir}) is empty in columns {kol}. "
                            "Weather for the last day is required."))
    if error:
        return None, error, info
    return df.reset_index(drop=True), error, info


# ---------------------------------------------------------------------
# Proses lengkap: validasi -> preprocessing -> prediksi
# ---------------------------------------------------------------------
def nilai_spasial_terakhir(dataset: pd.DataFrame) -> pd.DataFrame:
    """Kepadatan & luas RTH tahun terakhir per stasiun (indeks = stasiun)."""
    terakhir = dataset[dataset["tanggal"].dt.year == dataset["tanggal"].dt.year.max()]
    return terakhir.sort_values("tanggal").groupby("stasiun")[FITUR_SPASIAL].last()


def proses(mentah: pd.DataFrame, models: dict, dataset: pd.DataFrame, rentang: pd.DataFrame) -> HasilUnggah:
    """`dataset`: dataset historis (untuk nilai spasial); `rentang`: min/max fitur dataset (indeks = fitur)."""
    hasil = HasilUnggah()
    data, hasil.error, hasil.info = validasi(mentah)
    if data is None:
        return hasil

    spasial = nilai_spasial_terakhir(dataset)
    data = data.join(spasial, on="stasiun")
    tahun = int(dataset["tanggal"].dt.year.max())
    hasil.info.append(tr(f"Kepadatan penduduk & luas RTH memakai nilai tahun {tahun} dari dataset.",
                         f"Population density & green open space use the {tahun} values from the dataset."))
    siap = preprocess(data)  # ffill limit=7, lag 1–3, roll3, bulan, hari — identik dengan training

    semua, polutan_kosong, luar = [], [], []
    for st_nama in sorted(siap["stasiun"].unique(), key=list(STASIUN).index):
        baris = kondisi_terakhir(siap, st_nama)
        hasil.kondisi[st_nama] = baris
        pred = prediksi_7_hari(models, baris)
        pred.insert(0, "tanggal_dasar", baris["tanggal"])
        pred.insert(0, "stasiun", st_nama)
        semua.append(pred)

        tgl = _tgl(baris["tanggal"])
        kosong = [_nama(f) for f in FITUR_POLUTAN if pd.isna(baris[f])]
        if kosong:
            polutan_kosong.append(tr(f"{st_nama} ({tgl}): {', '.join(kosong)} kosong — ditampilkan sebagai "
                                     "\"data tidak tersedia\" dan diproses model sebagai nilai kosong.",
                                     f"{st_nama} ({tgl}): {', '.join(kosong)} empty — shown as \"data not "
                                     "available\" and processed by the model as missing values."))
        for f in FITUR:
            if f in FITUR_SPASIAL or f in ("bulan", "hari") or pd.isna(baris[f]):
                continue
            lo, hi = rentang.loc[f, "min"], rentang.loc[f, "max"]
            if not lo <= baris[f] <= hi:
                luar.append(tr(f"{st_nama} ({tgl}): {_nama(f)} = {_g(baris[f])} di luar rentang dataset "
                               f"({_g(lo)}–{_g(hi)}).",
                               f"{st_nama} ({tgl}): {_nama(f)} = {_g(baris[f])} is outside the dataset range "
                               f"({_g(lo)}–{_g(hi)})."))
    hasil.peringatan += polutan_kosong
    if luar:
        hasil.peringatan += _ringkas(luar)
        hasil.peringatan.append(tr("Model berbasis pohon keputusan tidak dapat mengekstrapolasi: nilai di luar "
                                   "rentang diperlakukan seperti nilai di batas rentang, sehingga prediksi perlu "
                                   "dibaca hati-hati.",
                                   "Tree-based models cannot extrapolate: values outside the range are treated like "
                                   "values at the range limit, so read the forecast with care."))

    pred = pd.concat(semua, ignore_index=True)
    pred["kategori"] = pred["pm25"].map(lambda v: kategori_ispu(v)["kategori"])
    hasil.prediksi = pred

    hasil.data = siap
    hasil.hari = siap.groupby("stasiun").size().to_dict()
    hasil.validasi, hasil.dilewati_meteo = data_validasi(siap, models)
    return hasil


def data_validasi(siap: pd.DataFrame, models: dict) -> tuple[pd.DataFrame, dict[str, int]]:
    """Tanggal acuan yang bisa divalidasi + prediksi pred_h1..h7.

    Syarat sama dengan data uji Evaluation (lag 1–3, rata-rata 3 hari, dan target t+1..t+7 terisi),
    ditambah meteorologi hari acuan lengkap (konsisten dengan aturan hari terakhir unggahan).
    Seluruh file dianggap data uji, tanpa split 85%. Mengembalikan (data valid, {stasiun: jumlah dilewati}).
    """
    kandidat = siap.dropna(subset=KOLOM_LAG + KOLOM_TARGET)
    lengkap = kandidat[FITUR_METEOROLOGI].notna().all(axis=1)
    dilewati = {s: int(n) for s, n in (~lengkap).groupby(kandidat["stasiun"]).sum().items() if n}
    valid = kandidat[lengkap].reset_index(drop=True)
    if valid.empty:
        return valid.assign(**{f"pred_h{h}": pd.Series(dtype=float) for h in HORIZONS}), dilewati
    return pd.concat([valid, prediksi_batch(models, valid)], axis=1), dilewati


def hasil_ke_csv(prediksi: pd.DataFrame) -> bytes:
    """CSV unduhan: stasiun, tanggal_dasar, tanggal, horizon, pm25 (ISPU bulat), kategori. UTF-8 BOM untuk Excel."""
    out = prediksi.copy()
    out["pm25"] = out["pm25"].map(lambda v: kategori_ispu(v)["nilai"])
    out["horizon"] = "t+" + out["horizon"].astype(str)
    for k in ("tanggal_dasar", "tanggal"):
        out[k] = pd.to_datetime(out[k]).dt.strftime("%Y-%m-%d")
    return out[["stasiun", "tanggal_dasar", "tanggal", "horizon", "pm25", "kategori"]].to_csv(index=False).encode("utf-8-sig")
