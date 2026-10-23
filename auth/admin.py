"""Klien Supabase Admin API (kelola pengguna) & Storage memakai service key — HANYA dipakai di server.

Keamanan:
- Service key (sb_secret_... atau JWT service_role lama) hanya dikirim di header permintaan ke Supabase.
  Key tidak pernah dimasukkan ke pesan error, objek yang dikembalikan, atau log.
- Semua aksi admin wajib didahului pengecekan role pengguna di server (lihat components/akun.verifikasi_admin).
"""
import base64
import json
import time
from dataclasses import dataclass
from datetime import datetime
from urllib.parse import quote, urlparse

import requests

from core.teks import terjemah

from .supabase import PERAN_ADMIN, peran_dari

BAN_PERMANEN = "876000h"   # ±100 tahun
PER_HALAMAN = 100
MAKS_HALAMAN = 50

PESAN_UMUM = "Permintaan ke server admin gagal. Coba lagi nanti."
PESAN_JARINGAN = "Tidak dapat terhubung ke server Supabase. Periksa koneksi internet lalu coba lagi."
PESAN_KEY_DITOLAK = "Service key ditolak oleh Supabase. Periksa nilai service_key di secrets."


class AdminError(Exception):
    """Kesalahan aksi admin dengan pesan aman untuk ditampilkan (tanpa key/URL internal)."""

    def __init__(self, pesan: str, status: int | None = None):
        pesan = terjemah(pesan)
        super().__init__(pesan)
        self.pesan, self.status = pesan, status


def _payload_jwt(token: str) -> dict:
    try:
        bagian = token.split(".")[1]
        return json.loads(base64.urlsafe_b64decode(bagian + "=" * (-len(bagian) % 4)))
    except (IndexError, ValueError):
        return {}


def cek_service_key(key: str) -> str | None:
    """Pesan error jika key bukan service key yang sah. Pesan tidak pernah memuat nilai key."""
    key = (key or "").strip()
    if not key:
        return "Service key belum diisi di secrets (supabase.service_key)."
    if key.startswith("sb_secret_"):
        return None
    if key.startswith("sb_publishable_"):
        return "service_key berisi publishable key. Gunakan secret key (sb_secret_...)."
    if key.count(".") == 2 and _payload_jwt(key).get("role") == "service_role":
        return None
    return "service_key tidak dikenali. Gunakan secret key (sb_secret_...) atau service_role key."


def boleh_diubah(id_admin: str, target: "Pengguna") -> str | None:
    """Alasan penolakan jika target tidak boleh dinonaktifkan/dihapus dari aplikasi, None jika boleh."""
    if target.id == id_admin:
        return terjemah("Anda tidak dapat menonaktifkan atau menghapus akun Anda sendiri.")
    if target.peran == PERAN_ADMIN:
        return terjemah("Akun admin hanya dapat diubah melalui dashboard Supabase.")
    return None


@dataclass
class Pengguna:
    id: str
    email: str
    nama: str
    dibuat: str | None
    masuk_terakhir: str | None
    peran: str | None
    nonaktif_sampai: str | None
    terkonfirmasi: bool

    @property
    def nonaktif(self) -> bool:
        if not self.nonaktif_sampai:
            return False
        try:
            t = datetime.fromisoformat(self.nonaktif_sampai.replace("Z", "+00:00"))
            return t.timestamp() > time.time()
        except ValueError:
            return True

    @property
    def status(self) -> str:
        if self.nonaktif:
            return "Nonaktif"
        return "Aktif" if self.terkonfirmasi else "Belum konfirmasi"


def _pengguna_dari(u: dict) -> Pengguna:
    email = u.get("email", "") or ""
    nama = (u.get("user_metadata") or {}).get("nama") or email.split("@")[0]
    return Pengguna(u.get("id", ""), email, nama, u.get("created_at"), u.get("last_sign_in_at"), peran_dari(u),
                    u.get("banned_until"), bool(u.get("email_confirmed_at") or u.get("confirmed_at")))


class KlienAdmin:
    def __init__(self, url: str, service_key: str, timeout: float = 15, http=requests):
        u = urlparse(url.strip())
        self._dasar = f"{u.scheme}://{u.netloc}"
        self.__key = service_key.strip()   # atribut privat; tidak pernah dikembalikan ke pemanggil
        self.timeout = timeout
        self.http = http

    def __repr__(self) -> str:  # cegah key ikut tercetak jika objek di-print/log
        return f"KlienAdmin({self._dasar!r})"

    def _header(self, tambahan: dict | None = None) -> dict:
        h = {"apikey": self.__key}
        if not self.__key.startswith("sb_"):  # JWT service_role lama juga dikirim sebagai Bearer
            h["Authorization"] = f"Bearer {self.__key}"
        return {**h, **(tambahan or {})}

    def _minta(self, metode: str, jalur: str, *, json_data=None, data: bytes | None = None,
               header: dict | None = None, boleh_404: bool = False):
        opsi = {"headers": self._header(header), "timeout": self.timeout}
        if json_data is not None:
            opsi["json"] = json_data
        if data is not None:
            opsi["data"] = data
        try:
            r = getattr(self.http, metode)(f"{self._dasar}{jalur}", **opsi)
        except requests.RequestException:
            raise AdminError(PESAN_JARINGAN) from None   # tanpa rantai: pesan asli bisa memuat detail permintaan
        if boleh_404 and r.status_code in (400, 404):
            teks = (r.text or "").lower() if hasattr(r, "text") else ""
            if "bucket" in teks and "not found" in teks:
                raise AdminError("Bucket Storage tidak ditemukan. Periksa nama bucket di secrets.", 404)
            return None
        if r.status_code in (401, 403):
            raise AdminError(PESAN_KEY_DITOLAK, r.status_code)
        if r.status_code == 404:
            raise AdminError("Data tidak ditemukan di server.", 404)
        if r.status_code >= 400:
            raise AdminError(PESAN_UMUM, r.status_code)
        return r

    # ---------------- Pengguna (Auth Admin API) ----------------
    def daftar_pengguna(self) -> list[Pengguna]:
        semua = []
        for halaman in range(1, MAKS_HALAMAN + 1):
            r = self._minta("get", f"/auth/v1/admin/users?page={halaman}&per_page={PER_HALAMAN}")
            users = (r.json() or {}).get("users", [])
            semua += [_pengguna_dari(u) for u in users]
            if len(users) < PER_HALAMAN:
                break
        return semua

    def ambil_pengguna(self, id_pengguna: str) -> Pengguna:
        r = self._minta("get", f"/auth/v1/admin/users/{quote(id_pengguna)}")
        return _pengguna_dari(r.json())

    def nonaktifkan(self, id_pengguna: str) -> None:
        self._minta("put", f"/auth/v1/admin/users/{quote(id_pengguna)}", json_data={"ban_duration": BAN_PERMANEN})

    def aktifkan(self, id_pengguna: str) -> None:
        self._minta("put", f"/auth/v1/admin/users/{quote(id_pengguna)}", json_data={"ban_duration": "none"})

    def hapus(self, id_pengguna: str) -> None:
        self._minta("delete", f"/auth/v1/admin/users/{quote(id_pengguna)}")

    # ---------------- Storage (bucket privat) ----------------
    def unduh(self, bucket: str, path: str) -> bytes | None:
        """Isi objek, atau None jika belum ada."""
        r = self._minta("get", f"/storage/v1/object/{quote(bucket)}/{quote(path)}", boleh_404=True)
        return None if r is None else r.content

    def unggah(self, bucket: str, path: str, isi: bytes, tipe: str, timpa: bool = False) -> None:
        self._minta("post", f"/storage/v1/object/{quote(bucket)}/{quote(path)}", data=isi,
                    header={"Content-Type": tipe, "x-upsert": "true" if timpa else "false"})
