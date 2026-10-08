"""Tes klien Supabase Auth (auth/supabase.py) dengan HTTP tiruan — tidak menghubungi Supabase.

Pemakaian:  python tes_auth.py
"""
import time

import requests

from auth.supabase import (PESAN_JARINGAN, AuthError, KlienAuth, cek_key, validasi_daftar, validasi_masuk)

lulus = gagal = 0


def cek(nama: str, kondisi: bool, detail: str = "") -> None:
    global lulus, gagal
    lulus, gagal = lulus + kondisi, gagal + (not kondisi)
    print(f"[{'OK ' if kondisi else 'GAGAL'}] {nama}" + (f"\n        {detail}" if detail else ""))


class Respons:
    def __init__(self, status: int, data: dict | None = None):
        self.status_code, self._data = status, data
        self.content = b"" if data is None else b"x"

    def json(self):
        if self._data is None:
            raise ValueError
        return self._data


class HttpTiruan:
    """Mencatat permintaan terakhir dan mengembalikan respons yang disiapkan."""

    def __init__(self, respons=None, galat: Exception | None = None):
        self.respons, self.galat, self.permintaan = respons, galat, None

    def post(self, url, json=None, headers=None, timeout=None):
        self.permintaan = {"url": url, "json": json, "headers": headers}
        if self.galat:
            raise self.galat
        return self.respons


TOKEN = {"access_token": "akses", "refresh_token": "segar", "expires_in": 3600, "expires_at": time.time() + 3600,
         "user": {"id": "u1", "email": "budi@contoh.com", "user_metadata": {"nama": "Budi"}}}
KEY = "sb_publishable_abc123"


def klien(respons=None, galat=None):
    http = HttpTiruan(respons, galat)
    return KlienAuth("https://proyek.supabase.co/", KEY, http=http), http


def pesan_error(k: KlienAuth, aksi) -> str:
    try:
        aksi(k)
    except AuthError as e:
        return e.pesan
    return "(tidak ada error)"


# --- validasi form -------------------------------------------------------
cek("daftar valid", validasi_daftar("Budi", "budi@contoh.com", "rahasia", "rahasia") == [])
e = validasi_daftar("", "budi@", "12345", "123456")
cek("daftar: nama kosong, email salah, password < 6, konfirmasi beda", len(e) == 4, " | ".join(e))
cek("daftar: konfirmasi tidak cocok", validasi_daftar("Budi", "b@c.id", "rahasia", "rahasiA")
    == ["Konfirmasi password tidak cocok."])
cek("masuk: password kosong", validasi_masuk("b@c.id", "") == ["Password wajib diisi."])
cek("key publishable diterima", cek_key(KEY) is None)
cek("secret key ditolak", "secret key" in (cek_key("sb_secret_xyz") or ""))
cek("anon key lama ditolak", cek_key("eyJhbGciOi...") is not None)

# --- permintaan & header -------------------------------------------------
k, http = klien(Respons(200, TOKEN))
sesi = k.daftar(" Budi ", "budi@contoh.com", "rahasia")
h = http.permintaan["headers"]
cek("daftar: endpoint /auth/v1/signup", http.permintaan["url"] == "https://proyek.supabase.co/auth/v1/signup")
cek("daftar: nama disimpan di user_metadata", http.permintaan["json"]["data"] == {"nama": "Budi"})
cek("header apikey = publishable key, tanpa Bearer", h["apikey"] == KEY and "Authorization" not in h)
cek("daftar: sesi langsung aktif + nama dari metadata", sesi is not None and sesi.nama == "Budi"
    and sesi.access_token == "akses")

http2 = HttpTiruan(Respons(200, TOKEN))
KlienAuth("https://proyek.supabase.co/rest/v1/", KEY, http=http2).masuk("budi@contoh.com", "rahasia")
cek("URL berakhiran /rest/v1/ dinormalkan", http2.permintaan["url"]
    == "https://proyek.supabase.co/auth/v1/token?grant_type=password", http2.permintaan["url"])

k, http = klien(Respons(200, {"id": "u1", "email": "budi@contoh.com"}))
cek("daftar: konfirmasi email aktif -> None", k.daftar("Budi", "budi@contoh.com", "rahasia") is None)

k, http = klien(Respons(200, TOKEN))
sesi = k.masuk("budi@contoh.com", "rahasia")
cek("masuk: grant_type=password", http.permintaan["url"].endswith("/token?grant_type=password") and sesi.email
    == "budi@contoh.com")
k.perpanjang("segar")
cek("perpanjang: grant_type=refresh_token", http.permintaan["url"].endswith("grant_type=refresh_token")
    and http.permintaan["json"] == {"refresh_token": "segar"})

k, http = klien(Respons(204))
k.keluar("akses")
cek("keluar: Bearer access token pengguna", http.permintaan["headers"].get("Authorization") == "Bearer akses")
k, _ = klien(Respons(500, {}))
try:
    k.keluar("akses")
    cek("keluar: error server diabaikan", True)
except AuthError:
    cek("keluar: error server diabaikan", False)

nama_kosong = dict(TOKEN, user={"id": "u2", "email": "sari@contoh.com", "user_metadata": {}})
k, _ = klien(Respons(200, nama_kosong))
cek("nama kosong -> bagian depan email", k.masuk("sari@contoh.com", "x").nama == "sari")

# --- pemetaan error ke bahasa Indonesia ---------------------------------
kasus = [
    ("email sudah terdaftar (error_code)", Respons(422, {"code": 422, "error_code": "user_already_exists",
                                                          "msg": "User already registered"}),
     lambda k: k.daftar("B", "b@c.id", "rahasia"), "Email sudah terdaftar"),
    ("email sudah terdaftar (pesan lama)", Respons(400, {"msg": "User already registered"}),
     lambda k: k.daftar("B", "b@c.id", "rahasia"), "Email sudah terdaftar"),
    ("password salah (error_code)", Respons(400, {"error_code": "invalid_credentials", "msg": "Invalid login credentials"}),
     lambda k: k.masuk("b@c.id", "salah"), "Email atau password salah"),
    ("password salah (format lama)", Respons(400, {"error": "invalid_grant", "error_description": "Invalid login credentials"}),
     lambda k: k.masuk("b@c.id", "salah"), "Email atau password salah"),
    ("password lemah", Respons(422, {"error_code": "weak_password", "msg": "Password should be at least 6 characters."}),
     lambda k: k.daftar("B", "b@c.id", "12345"), "minimal 6"),
    ("terlalu banyak percobaan", Respons(429, {"msg": "rate limited"}),
     lambda k: k.masuk("b@c.id", "x"), "Terlalu banyak"),
    ("refresh token kedaluwarsa", Respons(400, {"error_code": "refresh_token_not_found"}),
     lambda k: k.perpanjang("lama"), "Sesi berakhir"),
    ("API key ditolak", Respons(401, {"message": "Invalid API key"}),
     lambda k: k.masuk("b@c.id", "x"), "API key"),
    ("error server tak dikenal", Respons(500, None),
     lambda k: k.masuk("b@c.id", "x"), "Terjadi kesalahan"),
]
for nama, respons, aksi, kata in kasus:
    k, _ = klien(respons)
    p = pesan_error(k, aksi)
    cek(f"error: {nama}", kata in p, p)

k, _ = klien(galat=requests.ConnectionError("tidak ada jaringan"))
cek("error: jaringan putus", pesan_error(k, lambda k: k.masuk("b@c.id", "x")) == PESAN_JARINGAN)

print(f"\n{lulus} lulus, {gagal} gagal")
