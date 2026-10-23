"""Sesi akun di st.session_state: klien dari secrets, perpanjangan token, gerbang halaman, blok sidebar."""
import time
from dataclasses import replace
from html import escape

import streamlit as st

from auth.supabase import AuthError, KlienAuth, Sesi, cek_key

from core.teks import terjemah

from .bahasa import t

KUNCI_SESI = "sesi_akun"
KUNCI_TUJUAN = "akun_setelah_masuk"   # halaman tujuan setelah berhasil masuk
KUNCI_MODE = "akun_mode"              # "Masuk" / "Daftar"
KUNCI_PESAN = "akun_pesan"            # pesan sekali tampil (mis. setelah keluar)
HALAMAN_AKUN = "views/akun.py"


def _klien() -> tuple[KlienAuth | None, str | None]:
    """(klien, pesan_error) dari .streamlit/secrets.toml bagian [supabase].

    Tidak di-cache: objeknya ringan, dan secrets yang baru diisi langsung terbaca tanpa restart server.
    """
    try:
        cfg = st.secrets["supabase"]
        url, key = str(cfg["url"]).strip(), str(cfg["key"]).strip()
    except Exception:  # noqa: BLE001 — file/bagian/kunci tidak ada
        return None, t("Fitur akun belum dikonfigurasi (secrets Supabase belum diisi).",
                       "Accounts are not configured yet (Supabase secrets are empty).")
    if not url.startswith("https://"):
        return None, t("URL Supabase pada secrets tidak valid.", "The Supabase URL in secrets is invalid.")
    if (masalah := cek_key(key)) is not None:
        return None, terjemah(masalah)
    return KlienAuth(url, key), None


def klien() -> KlienAuth | None:
    return _klien()[0]


def masalah_konfigurasi() -> str | None:
    return _klien()[1]


def simpan_sesi(sesi: Sesi) -> None:
    st.session_state[KUNCI_SESI] = sesi


def pengguna_aktif() -> Sesi | None:
    """Sesi aktif; diperpanjang otomatis bila access token hampir kedaluwarsa."""
    sesi: Sesi | None = st.session_state.get(KUNCI_SESI)
    if sesi is None or not sesi.kedaluwarsa():
        return sesi
    k = klien()
    try:
        if k is None:
            raise AuthError("Fitur akun belum dikonfigurasi.")
        sesi = k.perpanjang(sesi.refresh_token)
        simpan_sesi(sesi)
        return sesi
    except AuthError:
        st.session_state.pop(KUNCI_SESI, None)
        st.session_state[KUNCI_PESAN] = t("Sesi Anda telah berakhir. Silakan masuk kembali.",
                                          "Your session has ended. Please sign in again.")
        return None


def keluar() -> None:
    """Callback tombol Keluar: cabut sesi di server lalu hapus dari session_state."""
    sesi: Sesi | None = st.session_state.pop(KUNCI_SESI, None)
    if sesi is not None and (k := klien()) is not None:
        k.keluar(sesi.access_token)
    st.session_state.pop("riwayat_unggah", None)  # riwayat milik sesi akun ini
    st.session_state.pop("akun_menu_admin", None)
    st.session_state[KUNCI_PESAN] = t("Anda telah keluar.", "You have signed out.")


def _ke_akun(mode: str, tujuan: str) -> None:
    st.session_state[KUNCI_MODE] = mode
    st.session_state[KUNCI_TUJUAN] = tujuan


def wajib_masuk(tujuan: str, nama_fitur: str, manfaat: list[str] | None = None) -> Sesi:
    """Gerbang halaman: jika belum masuk tampilkan ajakan masuk/daftar lalu hentikan halaman."""
    sesi = pengguna_aktif()
    if sesi is not None:
        return sesi
    masalah = masalah_konfigurasi()
    daftar = "".join(f"<li>{m}</li>" for m in manfaat or [])
    _, tengah, _ = st.columns([1, 1.6, 1])  # kartu di tengah, seperti halaman Masuk / Daftar
    with tengah, st.container(key="card_ajakan_masuk"):
        sub = t("Setelah masuk, Anda dapat:", "After signing in, you can:")
        st.html('<div class="ajakan"><div class="ajIkon"><span class="material-symbols-rounded">lock</span></div>'
                f'<div class="ajJudul">{t("Perlu masuk", "Sign-in required")}</div><p class="ajTeks">'
                + t(f"Fitur <b>{nama_fitur}</b> hanya tersedia untuk pengguna yang sudah masuk. Dashboard, Data "
                    "Historis, Evaluation, dan Information tetap dapat dibuka tanpa akun.",
                    f"<b>{nama_fitur}</b> is only available to signed-in users. Dashboard, Historical Data, "
                    "Evaluation, and Information remain open without an account.") + '</p>'
                + (f'<div class="ajSub">{sub}</div><ol class="ajList">{daftar}</ol>' if daftar else "")
                + '</div>')
        if masalah:
            st.html(f'<div class="note">{masalah}</div>')
        else:
            c1, c2 = st.columns(2, gap="small")
            if c1.button(t("Masuk", "Sign in"), key="ajakan_masuk", type="primary", icon=":material/login:", width="stretch"):
                _ke_akun("Masuk", tujuan)
                st.switch_page(HALAMAN_AKUN)
            if c2.button(t("Daftar akun baru", "Create account"), key="ajakan_daftar", icon=":material/person_add:", width="stretch"):
                _ke_akun("Daftar", tujuan)
                st.switch_page(HALAMAN_AKUN)
            st.html('<div class="ajCatatan">' + t("Daftar cukup dengan nama, email, dan password",
                                                  "Registration only needs a name, email, and password")
                    + '</div>')
    st.stop()


def blok_sidebar() -> None:
    """Nama + email + tombol Keluar jika sudah masuk."""
    sesi = pengguna_aktif()
    if sesi is None:
        return
    inisial = escape((sesi.nama.strip()[:1] or "?").upper())
    st.html(f'<div class="akunBox"><div class="avatar">{inisial}</div><div class="akunTeks">'
            f'<span>{t("Masuk sebagai", "Signed in as")}</span>'
            f'<b>{escape(sesi.nama)}</b><span>{escape(sesi.email)}</span></div></div>')
    st.button(t("Keluar", "Sign out"), key="tombol_keluar", on_click=keluar, icon=":material/logout:", width="stretch")


KUNCI_MENU_ADMIN = "akun_menu_admin"   # (waktu cek, token, admin?) — HANYA untuk tampilan menu
JEDA_MENU_ADMIN = 120                   # detik


def klien_admin():
    """(KlienAdmin, bucket) dari secrets, atau (None, pesan). Pesan tidak pernah memuat nilai key."""
    from auth.admin import KlienAdmin, cek_service_key
    try:
        cfg = st.secrets["supabase"]
        url, key = str(cfg["url"]).strip(), str(cfg.get("service_key", "")).strip()
        bucket = str(cfg.get("bucket", "data-dashboard")).strip() or "data-dashboard"
    except Exception:  # noqa: BLE001
        return None, t("Secrets Supabase belum diisi.", "Supabase secrets are empty.")
    if (masalah := cek_service_key(key)) is not None:
        return None, terjemah(masalah)
    return (KlienAdmin(url, key), bucket), None


def verifikasi_admin():
    """Profil admin hasil pengecekan SERVER (GET /auth/v1/user), atau None. Dipanggil setiap halaman/aksi admin."""
    sesi = pengguna_aktif()
    k = klien()
    if sesi is None or k is None:
        return None
    try:
        p = k.profil(sesi.access_token)
    except AuthError:
        return None
    st.session_state[KUNCI_MENU_ADMIN] = (time.time(), sesi.access_token, p.admin)
    return p if p.admin else None


def admin_untuk_menu() -> bool:
    """Apakah menu Admin ditampilkan. Di-cache singkat; halaman Admin tetap memeriksa ulang di server."""
    sesi = pengguna_aktif()
    if sesi is None:
        return False
    simpan = st.session_state.get(KUNCI_MENU_ADMIN)
    if simpan and simpan[1] == sesi.access_token and time.time() - simpan[0] < JEDA_MENU_ADMIN:
        return simpan[2]
    return verifikasi_admin() is not None


def wajib_admin(tujuan: str):
    """Gerbang halaman Admin: harus masuk DAN role admin terverifikasi server; selain itu halaman berhenti."""
    wajib_masuk(tujuan, "Admin")
    profil = verifikasi_admin()
    if profil is None:
        st.html(f'<div class="errBox"><b class="h">{t("Akses ditolak", "Access denied")}</b>' + t(
            "Halaman ini hanya untuk akun dengan peran admin. Peran diatur oleh pengelola melalui dashboard Supabase.",
            "This page is only for accounts with the admin role. Roles are set by the maintainer in the Supabase "
            "dashboard.") + '</div>')
        st.stop()
    return profil


def perbarui_nama(nama: str) -> None:
    """Ganti nama di sesi lokal setelah berhasil diubah di server."""
    sesi = st.session_state.get(KUNCI_SESI)
    if sesi is not None:
        st.session_state[KUNCI_SESI] = replace(sesi, nama=nama)
