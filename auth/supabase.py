"""Klien Supabase Auth (GoTrue REST API) untuk daftar, masuk, perpanjang sesi, dan keluar.

Memakai publishable key (sb_publishable_...). Key ini bukan JWT, sehingga hanya dikirim di header
`apikey`; header `Authorization: Bearer` hanya diisi access token milik pengguna.
Tidak ada tabel tambahan: nama pengguna disimpan di `user_metadata`.
"""
import re
import time
from dataclasses import dataclass
from urllib.parse import urlparse

import requests

PASSWORD_MIN = 6
_POLA_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

PESAN_ERROR = {
    "user_already_exists": "Email sudah terdaftar. Silakan masuk atau gunakan email lain.",
    "email_exists": "Email sudah terdaftar. Silakan masuk atau gunakan email lain.",
    "invalid_credentials": "Email atau password salah.",
    "weak_password": f"Password terlalu lemah. Gunakan minimal {PASSWORD_MIN} karakter.",
    "email_address_invalid": "Format email tidak valid.",
    "validation_failed": "Data yang dikirim tidak valid. Periksa kembali email dan password.",
    "email_not_confirmed": "Email belum dikonfirmasi. Periksa kotak masuk email Anda.",
    "signup_disabled": "Pendaftaran akun baru sedang dinonaktifkan.",
    "email_provider_disabled": "Masuk dengan email sedang dinonaktifkan.",
    "over_request_rate_limit": "Terlalu banyak percobaan. Coba lagi beberapa menit lagi.",
    "over_email_send_rate_limit": "Terlalu banyak percobaan. Coba lagi beberapa menit lagi.",
    "refresh_token_not_found": "Sesi berakhir. Silakan masuk kembali.",
    "refresh_token_already_used": "Sesi berakhir. Silakan masuk kembali.",
    "session_not_found": "Sesi berakhir. Silakan masuk kembali.",
    "session_expired": "Sesi berakhir. Silakan masuk kembali.",
}
PESAN_UMUM = "Terjadi kesalahan pada server autentikasi. Coba lagi nanti."
PESAN_JARINGAN = "Tidak dapat terhubung ke server autentikasi. Periksa koneksi internet lalu coba lagi."


class AuthError(Exception):
    """Kesalahan autentikasi dengan pesan bahasa Indonesia yang siap ditampilkan."""

    def __init__(self, pesan: str, kode: str | None = None):
        super().__init__(pesan)
        self.pesan, self.kode = pesan, kode


@dataclass
class Sesi:
    access_token: str
    refresh_token: str
    expires_at: float          # epoch detik
    id: str
    email: str
    nama: str

    def kedaluwarsa(self, jeda: int = 60) -> bool:
        return time.time() >= self.expires_at - jeda


# ---------------------------------------------------------------------
# Validasi form (sebelum menghubungi server)
# ---------------------------------------------------------------------
def validasi_daftar(nama: str, email: str, password: str, konfirmasi: str) -> list[str]:
    error = []
    if not nama.strip():
        error.append("Nama wajib diisi.")
    if not _POLA_EMAIL.match(email.strip()):
        error.append("Format email tidak valid, contoh: nama@email.com.")
    if len(password) < PASSWORD_MIN:
        error.append(f"Password minimal {PASSWORD_MIN} karakter.")
    if password != konfirmasi:
        error.append("Konfirmasi password tidak cocok.")
    return error


def validasi_masuk(email: str, password: str) -> list[str]:
    error = []
    if not _POLA_EMAIL.match(email.strip()):
        error.append("Format email tidak valid, contoh: nama@email.com.")
    if not password:
        error.append("Password wajib diisi.")
    return error


def cek_key(key: str) -> str | None:
    """Pesan error jika key bukan publishable key yang aman untuk aplikasi klien."""
    if key.startswith("sb_secret_"):
        return "Key yang dipakai adalah secret key. Gunakan publishable key (sb_publishable_...)."
    if not key.startswith("sb_publishable_"):
        return "Key Supabase harus berupa publishable key (sb_publishable_...)."
    return None


# ---------------------------------------------------------------------
# Klien REST
# ---------------------------------------------------------------------
class KlienAuth:
    def __init__(self, url: str, key: str, timeout: float = 10, http=requests):
        # cukup https://<ref>.supabase.co; path yang ikut tersalin (mis. /rest/v1/) dibuang
        u = urlparse(url.strip())
        self.url = f"{u.scheme}://{u.netloc}/auth/v1"
        self.key = key
        self.timeout = timeout
        self.http = http

    def _header(self, token: str | None = None) -> dict:
        h = {"apikey": self.key, "Content-Type": "application/json"}
        if token:
            h["Authorization"] = f"Bearer {token}"
        return h

    def _post(self, jalur: str, data: dict | None = None, token: str | None = None) -> dict:
        try:
            r = self.http.post(f"{self.url}{jalur}", json=data or {}, headers=self._header(token), timeout=self.timeout)
        except requests.RequestException as e:
            raise AuthError(PESAN_JARINGAN, "jaringan") from e
        if r.status_code >= 400:
            raise _error_dari(r)
        return r.json() if r.content else {}

    def daftar(self, nama: str, email: str, password: str) -> "Sesi | None":
        """Buat akun. Mengembalikan Sesi jika langsung aktif, None jika perlu konfirmasi email."""
        hasil = self._post("/signup", {"email": email.strip(), "password": password,
                                       "data": {"nama": nama.strip()}})
        if "access_token" not in hasil:
            return None
        return _sesi_dari(hasil)

    def masuk(self, email: str, password: str) -> Sesi:
        return _sesi_dari(self._post("/token?grant_type=password", {"email": email.strip(), "password": password}))

    def perpanjang(self, refresh_token: str) -> Sesi:
        return _sesi_dari(self._post("/token?grant_type=refresh_token", {"refresh_token": refresh_token}))

    def keluar(self, access_token: str) -> None:
        """Cabut sesi di server. Kegagalan diabaikan karena sesi lokal tetap dihapus."""
        try:
            self._post("/logout", token=access_token)
        except AuthError:
            pass


def _sesi_dari(data: dict) -> Sesi:
    user = data.get("user") or {}
    email = user.get("email", "")
    nama = (user.get("user_metadata") or {}).get("nama") or email.split("@")[0]
    expires_at = data.get("expires_at") or time.time() + float(data.get("expires_in", 3600))
    return Sesi(data["access_token"], data["refresh_token"], float(expires_at), user.get("id", ""), email, nama)


def _error_dari(r) -> AuthError:
    try:
        isi = r.json()
    except ValueError:
        isi = {}
    kode = isi.get("error_code") or isi.get("error") or ""
    if kode in PESAN_ERROR:
        return AuthError(PESAN_ERROR[kode], kode)
    teks = str(isi.get("msg") or isi.get("error_description") or isi.get("message") or "").lower()
    if "already registered" in teks or "already exists" in teks:
        return AuthError(PESAN_ERROR["user_already_exists"], "user_already_exists")
    if "invalid login credentials" in teks:
        return AuthError(PESAN_ERROR["invalid_credentials"], "invalid_credentials")
    if "password should be at least" in teks:
        return AuthError(PESAN_ERROR["weak_password"], "weak_password")
    if r.status_code == 429:
        return AuthError(PESAN_ERROR["over_request_rate_limit"], "rate_limit")
    if r.status_code == 404:
        return AuthError("Konfigurasi Supabase tidak valid (URL salah). Hubungi pengelola aplikasi.", "url")
    if r.status_code in (401, 403) and "api key" in teks:
        return AuthError("Konfigurasi Supabase tidak valid (API key ditolak). Hubungi pengelola aplikasi.", "api_key")
    return AuthError(PESAN_UMUM, kode or str(r.status_code))
