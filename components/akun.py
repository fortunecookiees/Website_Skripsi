"""Sesi akun di st.session_state: klien dari secrets, perpanjangan token, gerbang halaman, blok sidebar."""
from html import escape

import streamlit as st

from auth.supabase import AuthError, KlienAuth, Sesi, cek_key

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
        return None, "Fitur akun belum dikonfigurasi (secrets Supabase belum diisi)."
    if not url.startswith("https://"):
        return None, "URL Supabase pada secrets tidak valid."
    if (masalah := cek_key(key)) is not None:
        return None, masalah
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
        st.session_state[KUNCI_PESAN] = "Sesi Anda telah berakhir. Silakan masuk kembali."
        return None


def keluar() -> None:
    """Callback tombol Keluar: cabut sesi di server lalu hapus dari session_state."""
    sesi: Sesi | None = st.session_state.pop(KUNCI_SESI, None)
    if sesi is not None and (k := klien()) is not None:
        k.keluar(sesi.access_token)
    st.session_state[KUNCI_PESAN] = "Anda telah keluar."


def _ke_akun(mode: str, tujuan: str) -> None:
    st.session_state[KUNCI_MODE] = mode
    st.session_state[KUNCI_TUJUAN] = tujuan


def wajib_masuk(tujuan: str, nama_fitur: str) -> Sesi:
    """Gerbang halaman: jika belum masuk tampilkan ajakan masuk/daftar lalu hentikan halaman."""
    sesi = pengguna_aktif()
    if sesi is not None:
        return sesi
    masalah = masalah_konfigurasi()
    with st.container(key="card_ajakan_masuk"):
        st.html('<div class="cardTitle">Perlu masuk <em>akun</em></div>'
                f'<div class="langkah">Fitur <b>{nama_fitur}</b> hanya tersedia untuk pengguna yang sudah masuk. '
                'Halaman Dashboard, Evaluation, dan Information tetap dapat dibuka tanpa akun.</div>')
        if masalah:
            st.html(f'<div class="note">{masalah}</div>')
        else:
            c1, c2, _ = st.columns([1, 1, 3])
            if c1.button("Masuk", key="ajakan_masuk", type="primary"):
                _ke_akun("Masuk", tujuan)
                st.switch_page(HALAMAN_AKUN)
            if c2.button("Daftar akun baru", key="ajakan_daftar"):
                _ke_akun("Daftar", tujuan)
                st.switch_page(HALAMAN_AKUN)
    st.stop()


def blok_sidebar() -> None:
    """Nama + email + tombol Keluar jika sudah masuk."""
    sesi = pengguna_aktif()
    if sesi is None:
        return
    st.html(f'<div class="akunBox"><span>Masuk sebagai</span><b>{escape(sesi.nama)}</b><span>{escape(sesi.email)}</span></div>')
    st.button("Keluar", key="tombol_keluar", on_click=keluar)
