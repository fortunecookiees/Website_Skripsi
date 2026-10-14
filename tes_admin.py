"""Tes fitur Admin dengan HTTP & Storage tiruan — tidak menghubungi Supabase.

Mencakup: pengecekan role, penolakan non-admin, larangan aksi ke akun sendiri/admin, service key tidak bocor,
alur versi data Dashboard (unggah -> aktif -> pilih versi -> kembali ke dataset penelitian), dan fallback.

Pemakaian:  python tes_admin.py
"""
import base64
import json
import time

import numpy as np
import pandas as pd
import requests

from auth.admin import AdminError, KlienAdmin, Pengguna, boleh_diubah, cek_service_key
from auth.supabase import KlienAuth, Sesi
from core.inference import muat_model, prediksi_7_hari
from core.preprocessing import kondisi_terakhir, muat_dataset, preprocess
from core.unggah import KOLOM_WAJIB
from core.versi_data import (PATH_MANIFEST, SUMBER_ADMIN, SUMBER_PENELITIAN, Manifest, buat_versi, ke_csv,
                             label_sumber, muat_data_dashboard, pilih_aktif, tambah_versi, validasi_admin)

lulus = gagal = 0
KUNCI_RAHASIA = "sb_secret_JANGAN_BOCOR_123"


def cek(nama: str, kondisi: bool, detail: str = "") -> None:
    global lulus, gagal
    lulus, gagal = lulus + bool(kondisi), gagal + (not kondisi)
    print(f"[{'OK ' if kondisi else 'GAGAL'}] {nama}" + (f"\n        {detail}" if detail else ""))


class Respons:
    def __init__(self, status: int, data=None, isi: bytes | None = None):
        self.status_code, self._data = status, data
        self.content = isi if isi is not None else (b"" if data is None else json.dumps(data).encode())
        self.text = self.content.decode("utf-8", "ignore")

    def json(self):
        if self._data is None:
            raise ValueError
        return self._data


class HttpTiruan:
    """Router sederhana: fungsi(metode, url, opsi) -> Respons. Mencatat semua permintaan."""

    def __init__(self, router=None, galat: Exception | None = None):
        self.router, self.galat, self.log = router, galat, []

    def _kirim(self, metode, url, **opsi):
        self.log.append({"metode": metode, "url": url, **opsi})
        if self.galat:
            raise self.galat
        return self.router(metode, url, opsi)

    def get(self, url, **o): return self._kirim("get", url, **o)
    def post(self, url, **o): return self._kirim("post", url, **o)
    def put(self, url, **o): return self._kirim("put", url, **o)
    def delete(self, url, **o): return self._kirim("delete", url, **o)


def jwt(payload: dict) -> str:
    b = lambda d: base64.urlsafe_b64encode(json.dumps(d).encode()).decode().rstrip("=")  # noqa: E731
    return f"{b({'alg': 'HS256'})}.{b(payload)}.tanda"


def user(i, peran=None, ban=None):
    return {"id": f"u{i}", "email": f"user{i}@contoh.id", "user_metadata": {"nama": f"User {i}"},
            "app_metadata": {"role": peran} if peran else {}, "created_at": "2026-10-01T00:00:00Z",
            "last_sign_in_at": None, "banned_until": ban, "email_confirmed_at": "2026-10-01T00:00:00Z"}


# ---------------------------------------------------------------------
print("== Service key ==")
cek("publishable ditolak sebagai service key", cek_service_key("sb_publishable_abc") is not None)
cek("sb_secret diterima", cek_service_key("sb_secret_abc") is None)
cek("JWT service_role lama diterima", cek_service_key(jwt({"role": "service_role"})) is None)
cek("JWT anon ditolak", cek_service_key(jwt({"role": "anon"})) is not None)
cek("key kosong ditolak", cek_service_key("") is not None)
cek("pesan cek tidak memuat nilai key", all(KUNCI_RAHASIA not in (cek_service_key(k) or "")
                                            for k in [KUNCI_RAHASIA, "sb_publishable_" + KUNCI_RAHASIA]))

print("\n== Pengecekan role (GET /auth/v1/user) ==")
for peran, harap in [("admin", True), (None, False), ("editor", False)]:
    http = HttpTiruan(lambda m, u, o, p=peran: Respons(200, user(1, p)))
    p = KlienAuth("https://x.supabase.co", "sb_publishable_k", http=http).profil("token-user")
    cek(f"role {peran!r} -> admin={harap}", p.admin is harap and http.log[0]["headers"]["Authorization"] == "Bearer token-user")
http = HttpTiruan(lambda m, u, o: Respons(401, {"error_code": "bad_jwt", "msg": "invalid JWT"}))
try:
    KlienAuth("https://x.supabase.co", "sb_publishable_k", http=http).profil("token-palsu")
    cek("token tidak sah -> ditolak", False)
except Exception:  # noqa: BLE001
    cek("token tidak sah -> ditolak (AuthError)", True)

print("\n== Klien Admin API ==")
http = HttpTiruan(lambda m, u, o: Respons(200, {"users": []}))
KlienAdmin("https://x.supabase.co/rest/v1/", KUNCI_RAHASIA, http=http).daftar_pengguna()
h = http.log[0]
cek("sb_secret: hanya header apikey (tanpa Bearer)", h["headers"].get("apikey") == KUNCI_RAHASIA
    and "Authorization" not in h["headers"] and h["url"].startswith("https://x.supabase.co/auth/v1/admin/users"))
kunci_jwt = jwt({"role": "service_role"})
http = HttpTiruan(lambda m, u, o: Respons(200, {"users": []}))
KlienAdmin("https://x.supabase.co", kunci_jwt, http=http).daftar_pengguna()
cek("JWT service_role: dikirim juga sebagai Bearer", http.log[0]["headers"].get("Authorization") == f"Bearer {kunci_jwt}")

halaman = {1: [user(i) for i in range(100)], 2: [user(i) for i in range(100, 103)]}
http = HttpTiruan(lambda m, u, o: Respons(200, {"users": halaman[int(u.split("page=")[1].split("&")[0])]}))
cek("daftar pengguna berhalaman (103 akun)", len(KlienAdmin("https://x.supabase.co", KUNCI_RAHASIA, http=http)
                                                .daftar_pengguna()) == 103 and len(http.log) == 2)

http = HttpTiruan(lambda m, u, o: Respons(200, {}))
k = KlienAdmin("https://x.supabase.co", KUNCI_RAHASIA, http=http)
k.nonaktifkan("u7"); k.aktifkan("u7"); k.hapus("u7")
cek("nonaktifkan = PUT ban_duration panjang", http.log[0]["metode"] == "put" and http.log[0]["json"]["ban_duration"] == "876000h")
cek("aktifkan = PUT ban_duration none", http.log[1]["json"] == {"ban_duration": "none"})
cek("hapus = DELETE /admin/users/u7", http.log[2]["metode"] == "delete" and http.log[2]["url"].endswith("/admin/users/u7"))

pesan = []
for respons in [Respons(401, {"msg": f"bad key {KUNCI_RAHASIA}"}), Respons(500, {"msg": KUNCI_RAHASIA})]:
    try:
        KlienAdmin("https://x.supabase.co", KUNCI_RAHASIA, http=HttpTiruan(lambda m, u, o, r=respons: r)).daftar_pengguna()
    except AdminError as e:
        pesan.append(e.pesan + str(e) + repr(e))
try:
    KlienAdmin("https://x.supabase.co", KUNCI_RAHASIA,
               http=HttpTiruan(galat=requests.ConnectionError(f"gagal apikey={KUNCI_RAHASIA}"))).daftar_pengguna()
except AdminError as e:
    pesan.append(e.pesan + str(e) + repr(e) + repr(e.__cause__) + repr(e.__context__ if e.__suppress_context__ is False else None))
cek("service key tidak pernah muncul di pesan error (401/500/jaringan)",
    len(pesan) == 3 and all(KUNCI_RAHASIA not in p for p in pesan), " | ".join(p[:60] for p in pesan))
cek("repr klien tidak memuat key", KUNCI_RAHASIA not in repr(KlienAdmin("https://x.supabase.co", KUNCI_RAHASIA))
    and KUNCI_RAHASIA not in str(vars(KlienAdmin("https://x.supabase.co", KUNCI_RAHASIA)).get("timeout")))

print("\n== Larangan aksi ke akun sendiri / admin ==")
p_biasa = Pengguna("u2", "b@c.id", "B", None, None, None, None, True)
p_admin = Pengguna("u3", "a@c.id", "A", None, None, "admin", None, True)
cek("akun sendiri ditolak", boleh_diubah("u2", p_biasa) is not None)
cek("akun admin lain ditolak", boleh_diubah("u1", p_admin) is not None)
cek("akun biasa boleh", boleh_diubah("u1", p_biasa) is None)
cek("status Nonaktif dari banned_until masa depan",
    Pengguna("u", "e", "n", None, None, None, "2999-01-01T00:00:00Z", True).status == "Nonaktif"
    and Pengguna("u", "e", "n", None, None, None, "2000-01-01T00:00:00Z", True).status == "Aktif")

# ---------------------------------------------------------------------
print("\n== Alur versi data Dashboard ==")
mentah = muat_dataset()
dataset = preprocess(mentah)
models = muat_model()


def contoh(n=6, geser_tahun=0, stasiun=None):
    d = mentah.sort_values("tanggal").groupby("stasiun").tail(n)
    if stasiun:
        d = d[d["stasiun"].isin(stasiun)]
    d = d[KOLOM_WAJIB].copy()
    d["tanggal"] = (d["tanggal"] + pd.DateOffset(years=geser_tahun)).dt.strftime("%Y-%m-%d")
    return d.reset_index(drop=True)


data4, err, _ = validasi_admin(contoh(stasiun=["DKI1 Bundaran HI", "DKI2 Kelapa Gading", "DKI3 Jagakarsa",
                                               "DKI4 Lubang Buaya"]))
cek("unggahan tanpa 5 stasiun ditolak", data4 is None and "kelima stasiun" in " ".join(err), " ".join(err))
data_a, err, _ = validasi_admin(contoh(n=6))
data_b, _, _ = validasi_admin(contoh(n=8, geser_tahun=1))   # data 2026 (di luar tahun nilai spasial)
cek("unggahan 5 stasiun lolos", data_a is not None and data_b is not None, " ".join(err))


class StorageTiruan:
    def __init__(self):
        self.isi, self.rusak = {}, False

    def unduh(self, path):
        if self.rusak:
            raise AdminError("Tidak dapat terhubung ke server Supabase.")
        return self.isi.get(path)

    def simpan_versi(self, data, nama, aktifkan=True, waktu=None):
        v = buat_versi(data, nama, "admin@contoh.id", waktu)
        self.isi[v.path] = ke_csv(data)
        m = tambah_versi(Manifest.dari_json(self.isi.get(PATH_MANIFEST)), v, aktifkan)
        self.isi[PATH_MANIFEST] = m.ke_json()
        return v

    def pilih(self, id_versi):
        self.isi[PATH_MANIFEST] = pilih_aktif(Manifest.dari_json(self.isi[PATH_MANIFEST]), id_versi).ke_json()


sto = StorageTiruan()
df, s = muat_data_dashboard(sto.unduh, dataset)
cek("belum ada manifest -> dataset penelitian", s.jenis == SUMBER_PENELITIAN and df is dataset)
df, s = muat_data_dashboard(None, dataset)
cek("Storage belum dikonfigurasi -> dataset penelitian", s.jenis == SUMBER_PENELITIAN and s.peringatan is None)

from datetime import datetime, timezone  # noqa: E402
va = sto.simpan_versi(data_a, "a.csv", waktu=datetime(2026, 10, 10, 3, 0, tzinfo=timezone.utc))
df, s = muat_data_dashboard(sto.unduh, dataset)
pred_admin = prediksi_7_hari(models, kondisi_terakhir(df, "DKI3 Jagakarsa"))
pred_riset = prediksi_7_hari(models, kondisi_terakhir(dataset, "DKI3 Jagakarsa"))
cek("versi A aktif -> Dashboard memakai data admin", s.jenis == SUMBER_ADMIN and s.versi.id == va.id
    and df["tanggal"].max() == pd.Timestamp(va.akhir))
cek("  prediksi dari versi A = prediksi dari kondisi yang sama (data A = ekor dataset)",
    np.allclose(pred_admin["pm25"], pred_riset["pm25"]))

vb = sto.simpan_versi(data_b, "b.csv", aktifkan=False, waktu=datetime(2026, 10, 12, 3, 0, tzinfo=timezone.utc))
_, s = muat_data_dashboard(sto.unduh, dataset)
cek("simpan versi B tanpa aktifkan -> A tetap aktif", s.versi.id == va.id
    and [v.id for v in Manifest.dari_json(sto.isi[PATH_MANIFEST]).versi] == [vb.id, va.id])
sto.pilih(vb.id)
df, s = muat_data_dashboard(sto.unduh, dataset)
cek("admin pilih versi B -> Dashboard memakai B", s.versi.id == vb.id and df["tanggal"].max() == pd.Timestamp(vb.akhir))
cek("  label: data 2026 -> keterangan nilai spasial 2025",
    "tetap memakai nilai 2025" in label_sumber(s, dataset["tanggal"].max()), label_sumber(s, dataset["tanggal"].max()))
_, s_a = muat_data_dashboard(lambda p: sto.isi.get(p) if p != PATH_MANIFEST else
                             pilih_aktif(Manifest.dari_json(sto.isi[PATH_MANIFEST]), va.id).ke_json(), dataset)
cek("  label: data 2025 -> tanpa keterangan spasial",
    "tetap memakai" not in label_sumber(s_a, dataset["tanggal"].max())
    and "Data diperbarui admin, terakhir 10-10-2026" in label_sumber(s_a, dataset["tanggal"].max()))
sto.pilih(None)
df, s = muat_data_dashboard(sto.unduh, dataset)
cek("kembali ke dataset penelitian", s.jenis == SUMBER_PENELITIAN and df is dataset
    and label_sumber(s, dataset["tanggal"].max()).startswith("Dataset penelitian"))
try:
    pilih_aktif(Manifest.dari_json(sto.isi[PATH_MANIFEST]), "tidak-ada")
    cek("pilih versi yang tidak ada ditolak", False)
except ValueError:
    cek("pilih versi yang tidak ada ditolak", True)

sto.pilih(va.id); sto.rusak = True
df, s = muat_data_dashboard(sto.unduh, dataset)
cek("Storage gagal -> fallback dataset penelitian + peringatan", df is dataset and s.peringatan is not None)
sto.rusak = False; sto.isi[va.path] = b"bukan,csv,yang\nbenar"
df, s = muat_data_dashboard(sto.unduh, dataset)
cek("berkas versi rusak -> fallback dataset penelitian", df is dataset and s.peringatan is not None)

# ---------------------------------------------------------------------
print("\n== Halaman Admin (AppTest, sesi & server tiruan) ==")
from streamlit.testing.v1 import AppTest  # noqa: E402

import auth.admin as modul_admin  # noqa: E402
import auth.supabase as modul_auth  # noqa: E402

PERAN = {"peran": None}
modul_auth.KlienAuth.profil = lambda self, token: modul_auth.Profil(
    "u1", "saya@contoh.id", "Saya", None, None, PERAN["peran"])
modul_admin.KlienAdmin.unduh = lambda self, bucket, path: None
modul_admin.KlienAdmin.daftar_pengguna = lambda self: [
    modul_admin._pengguna_dari(user(1, "admin") | {"id": "u1", "email": "saya@contoh.id"}), modul_admin._pengguna_dari(user(2))]
RAHASIA = {"supabase": {"url": "https://x.supabase.co", "key": "sb_publishable_k", "service_key": KUNCI_RAHASIA,
                        "bucket": "data-dashboard"}}


def buka(peran, masuk=True, rahasia=RAHASIA):
    PERAN["peran"] = peran
    at = AppTest.from_file("app.py", default_timeout=240)
    for k, v in rahasia.items():
        at.secrets[k] = v
    if masuk:
        at.session_state["sesi_akun"] = Sesi("tok", "seg", time.time() + 1e6, "u1", "saya@contoh.id", "Saya")
    at.run()
    at.switch_page("views/admin.py").run()
    return at


def teks(at):
    import re
    return " ".join(re.sub("<[^>]+>", " ", h.proto.body) for h in at.get("html"))


at = buka(None, masuk=False)
cek("belum masuk -> gerbang masuk", "Perlu masuk" in teks(at) and "Kelola Pengguna" not in teks(at))
at = buka(None)
cek("user biasa membuka /admin -> Akses ditolak", "Akses ditolak" in teks(at) and "Daftar Pengguna" not in teks(at))
menu = lambda at: [e.proto.label for e in at.sidebar.get("page_link")]  # noqa: E731
cek("  menu Admin tidak tampil untuk user biasa", "Admin" not in menu(at) and "Profil" in menu(at), str(menu(at)))
at = buka("admin")
t = teks(at)
at_dash = buka("admin"); at_dash.switch_page("views/dashboard.py").run()
cek("  menu Admin tampil untuk admin", "Admin" in menu(at_dash), str(menu(at_dash)))
cek("admin -> halaman tampil (daftar pengguna)", "Daftar Pengguna" in t and not at.exception, str(at.exception))
cek("  service key tidak muncul di halaman", KUNCI_RAHASIA not in t
    and all(KUNCI_RAHASIA not in str(getattr(e, "value", "")) for e in at.get("text_input")))
cek("  akun sendiri tanpa tombol aksi, akun lain punya tombol",
    not any(b.key == "off_u1" for b in at.button) and any(b.key == "off_u2" for b in at.button))
dipanggil = []
modul_admin.KlienAdmin.ambil_pengguna = lambda self, uid: modul_admin._pengguna_dari(user(int(uid[1:])) | {"id": uid})
modul_admin.KlienAdmin.nonaktifkan = lambda self, uid: dipanggil.append(uid)
PERAN["peran"] = None   # role dicabut setelah halaman terbuka
next(b for b in at.button if b.key == "off_u2").click().run()
cek("aksi setelah role dicabut -> ditolak server, tidak ada ban", dipanggil == [] and "Akses ditolak" in teks(at))
at = buka("admin")
next(b for b in at.button if b.key == "off_u2").click().run()
cek("aksi admin sah -> ban dikirim untuk u2", dipanggil == ["u2"] and "dinonaktifkan" in teks(at))
at = buka("admin", rahasia={"supabase": {"url": "https://x.supabase.co", "key": "sb_publishable_k"}})
cek("admin tanpa service key -> pesan konfigurasi", "belum dikonfigurasi" in teks(at))

print(f"\n{lulus} lulus, {gagal} gagal")
