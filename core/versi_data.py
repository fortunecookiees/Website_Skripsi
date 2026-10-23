"""Versi data Dashboard (Mode Aktual) yang diunggah admin, disimpan di Supabase Storage.

- Isi bucket: `manifest.json` (daftar versi + id versi aktif) dan `versi/<id>.csv` (data lolos validasi, belum diolah).
- Dashboard memakai versi aktif; jika tidak ada atau gagal dimuat, kembali ke dataset penelitian.
- Evaluation, Data Historis, metrik, dan model TIDAK memakai modul ini.

Modul ini tanpa Streamlit: akses Storage diberikan sebagai fungsi `unduh(path) -> bytes | None`.
"""
import io
import json
import secrets
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Callable

import pandas as pd

from .config import STASIUN
from .teks import tr
from .preprocessing import preprocess
from .unggah import KOLOM_WAJIB, nilai_spasial_terakhir, validasi

PATH_MANIFEST = "manifest.json"
SUMBER_PENELITIAN, SUMBER_ADMIN = "penelitian", "admin"


@dataclass
class Versi:
    id: str
    diunggah: str            # ISO 8601 UTC
    pengunggah: str          # email admin
    nama_file: str
    mulai: str               # YYYY-MM-DD
    akhir: str
    n_baris: int
    stasiun: list[str]

    @property
    def path(self) -> str:
        return f"versi/{self.id}.csv"


@dataclass
class Manifest:
    aktif: str | None = None
    versi: list[Versi] = field(default_factory=list)

    def cari(self, id_versi: str) -> Versi | None:
        return next((v for v in self.versi if v.id == id_versi), None)

    @property
    def versi_aktif(self) -> Versi | None:
        return self.cari(self.aktif) if self.aktif else None

    def ke_json(self) -> bytes:
        return json.dumps({"aktif": self.aktif, "versi": [asdict(v) for v in self.versi]},
                          ensure_ascii=False, indent=2).encode("utf-8")

    @classmethod
    def dari_json(cls, isi: bytes | None) -> "Manifest":
        if not isi:
            return cls()
        d = json.loads(isi.decode("utf-8"))
        return cls(d.get("aktif"), [Versi(**v) for v in d.get("versi", [])])


# ---------------------------------------------------------------------
# Operasi manifest (mengembalikan objek baru; penyimpanan dilakukan pemanggil)
# ---------------------------------------------------------------------
def tambah_versi(m: Manifest, v: Versi, aktifkan: bool = True) -> Manifest:
    return Manifest(v.id if aktifkan else m.aktif, [v] + [x for x in m.versi if x.id != v.id])


def pilih_aktif(m: Manifest, id_versi: str | None) -> Manifest:
    """id_versi=None berarti kembali ke dataset penelitian."""
    if id_versi is not None and m.cari(id_versi) is None:
        raise ValueError("Versi data tidak ditemukan.")
    return Manifest(id_versi, list(m.versi))


# ---------------------------------------------------------------------
# Validasi & persiapan data
# ---------------------------------------------------------------------
def validasi_admin(mentah: pd.DataFrame) -> tuple[pd.DataFrame | None, list[str], list[str]]:
    """Validasi yang sama dengan Unggah Data + kelima stasiun wajib ada."""
    data, error, info = validasi(mentah)
    if data is None:
        return None, error, info
    kurang = [s for s in STASIUN if s not in set(data["stasiun"])]
    if kurang:
        return None, [tr(f"Data Dashboard wajib berisi kelima stasiun. Belum ada: {', '.join(kurang)}.",
                         f"Dashboard data must include all five stations. Missing: {', '.join(kurang)}.")], info
    return data, error, info


def buat_versi(data: pd.DataFrame, nama_file: str, pengunggah: str, sekarang: datetime | None = None) -> Versi:
    sekarang = sekarang or datetime.now(timezone.utc)
    return Versi(id=f"{sekarang:%Y%m%d-%H%M%S}-{secrets.token_hex(3)}", diunggah=sekarang.isoformat(timespec="seconds"),
                 pengunggah=pengunggah, nama_file=nama_file, mulai=f"{data['tanggal'].min():%Y-%m-%d}",
                 akhir=f"{data['tanggal'].max():%Y-%m-%d}", n_baris=len(data),
                 stasiun=[s for s in STASIUN if s in set(data["stasiun"])])


def ke_csv(data: pd.DataFrame) -> bytes:
    out = data[KOLOM_WAJIB].copy()
    out["tanggal"] = pd.to_datetime(out["tanggal"]).dt.strftime("%Y-%m-%d")
    return out.to_csv(index=False).encode("utf-8")


def siapkan_dashboard(data: pd.DataFrame, dataset: pd.DataFrame) -> pd.DataFrame:
    """Data valid -> + kepadatan & RTH tahun terakhir dataset -> preprocessing identik training."""
    return preprocess(data.join(nilai_spasial_terakhir(dataset), on="stasiun"))


# ---------------------------------------------------------------------
# Sumber data Dashboard
# ---------------------------------------------------------------------
@dataclass
class SumberDashboard:
    jenis: str                       # "penelitian" | "admin"
    versi: Versi | None = None
    tahun_spasial: int | None = None
    peringatan: str | None = None    # mis. data admin gagal dimuat -> kembali ke dataset penelitian


def muat_data_dashboard(unduh: Callable[[str], bytes | None] | None,
                        dataset: pd.DataFrame) -> tuple[pd.DataFrame, SumberDashboard]:
    """Data untuk Mode Aktual. `unduh=None` (Storage belum dikonfigurasi) -> dataset penelitian."""
    tahun = int(dataset["tanggal"].dt.year.max())
    if unduh is None:
        return dataset, SumberDashboard(SUMBER_PENELITIAN)
    try:
        manifest = Manifest.dari_json(unduh(PATH_MANIFEST))
        v = manifest.versi_aktif
        if v is None:
            return dataset, SumberDashboard(SUMBER_PENELITIAN)
        isi = unduh(v.path)
        if not isi:
            raise ValueError("berkas versi aktif tidak ditemukan")
        data, error, _ = validasi_admin(pd.read_csv(io.BytesIO(isi), dtype=str))
        if data is None:
            raise ValueError("berkas versi aktif tidak lolos validasi")
        return siapkan_dashboard(data, dataset), SumberDashboard(SUMBER_ADMIN, v, tahun)
    except Exception:  # noqa: BLE001 — apa pun penyebabnya Dashboard tetap jalan dengan dataset penelitian
        return dataset, SumberDashboard(SUMBER_PENELITIAN,
                                        peringatan="Data terbaru dari admin gagal dimuat; menampilkan dataset penelitian.")
    # (hasil fungsi ini di-cache; peringatan diterjemahkan saat ditampilkan, lihat core.teks.terjemah)


def label_sumber(s: SumberDashboard, akhir_penelitian: pd.Timestamp, en: bool = False) -> str:
    """Teks label sumber data untuk Dashboard (en=True: bahasa Inggris)."""
    tgl = lambda t: pd.Timestamp(t).strftime("%d-%m-%Y")  # noqa: E731
    if s.jenis != SUMBER_ADMIN or s.versi is None:
        return (f"Research dataset · data up to {tgl(akhir_penelitian)}" if en
                else f"Dataset penelitian · data s.d. {tgl(akhir_penelitian)}")
    v = s.versi
    diunggah, akhir = tgl(pd.Timestamp(v.diunggah).tz_convert("Asia/Jakarta")), tgl(v.akhir)
    teks = (f"Data updated by admin, last on {diunggah} · data up to {akhir}" if en
            else f"Data diperbarui admin, terakhir {diunggah} · data s.d. {akhir}")
    tahun_data = {pd.Timestamp(v.mulai).year, pd.Timestamp(v.akhir).year}
    if s.tahun_spasial and tahun_data != {s.tahun_spasial}:
        teks += (f" · population density & green open space keep the {s.tahun_spasial} values" if en
                 else f" · kepadatan penduduk & luas RTH tetap memakai nilai {s.tahun_spasial}")
    return teks
