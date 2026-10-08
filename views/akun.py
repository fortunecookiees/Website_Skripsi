"""Halaman Masuk / Daftar (Supabase Auth). Diproses lewat callback agar field password bisa dikosongkan."""
from html import escape

import streamlit as st

from auth.supabase import AuthError, validasi_daftar, validasi_masuk
from components import akun
from components.kartu import judul_kartu
from components.tema import judul

MASUK, DAFTAR = "Masuk", "Daftar"
KUNCI_ERROR = "akun_error"
KUNCI_INFO = "akun_info"
KUNCI_ARAHKAN = "akun_arahkan"


def _gagal(pesan: list[str], *kunci_password: str) -> None:
    st.session_state[KUNCI_ERROR] = pesan
    for k in kunci_password:  # jangan biarkan password tertinggal di form
        st.session_state[k] = ""


def _berhasil(sesi, sambutan: str) -> None:
    akun.simpan_sesi(sesi)
    st.session_state.pop(KUNCI_ERROR, None)
    st.session_state[akun.KUNCI_PESAN] = sambutan
    st.session_state[KUNCI_ARAHKAN] = st.session_state.pop(akun.KUNCI_TUJUAN, None)


def proses_masuk() -> None:
    ss = st.session_state
    email, pw = ss.get("masuk_email", ""), ss.get("masuk_password", "")
    if error := validasi_masuk(email, pw):
        return _gagal(error, "masuk_password")
    try:
        sesi = akun.klien().masuk(email, pw)
    except AuthError as e:
        return _gagal([e.pesan], "masuk_password")
    ss["masuk_password"] = ""
    _berhasil(sesi, f"Selamat datang kembali, {sesi.nama}.")


def proses_daftar() -> None:
    ss = st.session_state
    nama, email = ss.get("daftar_nama", ""), ss.get("daftar_email", "")
    pw, konfirmasi = ss.get("daftar_password", ""), ss.get("daftar_konfirmasi", "")
    if error := validasi_daftar(nama, email, pw, konfirmasi):
        return _gagal(error, "daftar_password", "daftar_konfirmasi")
    try:
        sesi = akun.klien().daftar(nama, email, pw)
    except AuthError as e:
        return _gagal([e.pesan], "daftar_password", "daftar_konfirmasi")
    ss["daftar_password"] = ss["daftar_konfirmasi"] = ""
    if sesi is None:  # konfirmasi email masih aktif di Supabase
        ss[KUNCI_INFO] = "Akun dibuat. Periksa email Anda untuk konfirmasi, lalu masuk."
        ss[akun.KUNCI_MODE] = MASUK
        return
    _berhasil(sesi, f"Akun berhasil dibuat. Selamat datang, {sesi.nama}.")


def tampil_pesan() -> None:
    if info := st.session_state.pop(KUNCI_INFO, None):
        st.html(f'<div class="infoBox"><span class="dot"></span><span>{escape(info)}</span></div>')
    if pesan := st.session_state.pop(KUNCI_ERROR, None):
        daftar = "".join(f"<li>{escape(p)}</li>" for p in pesan)
        st.html(f'<div class="errBox"><b class="h">Belum berhasil</b><ul>{daftar}</ul></div>')


def form_masuk() -> None:
    with st.form("form_masuk", border=False):
        st.text_input("Email", key="masuk_email", placeholder="nama@email.com", autocomplete="email")
        st.text_input("Password", key="masuk_password", type="password", autocomplete="current-password")
        st.form_submit_button("Masuk", type="primary", on_click=proses_masuk, width="stretch")


def form_daftar() -> None:
    with st.form("form_daftar", border=False):
        st.text_input("Nama", key="daftar_nama", placeholder="Nama lengkap", autocomplete="name")
        st.text_input("Email", key="daftar_email", placeholder="nama@email.com", autocomplete="email")
        st.text_input("Password", key="daftar_password", type="password", autocomplete="new-password",
                      help="Minimal 6 karakter.")
        st.text_input("Konfirmasi password", key="daftar_konfirmasi", type="password", autocomplete="new-password")
        st.form_submit_button("Daftar", type="primary", on_click=proses_daftar, width="stretch")


# --- halaman ------------------------------------------------------------
if tujuan := st.session_state.pop(KUNCI_ARAHKAN, None):
    st.switch_page(tujuan)

judul("Akun", "Masuk atau daftar untuk memakai fitur Unggah Data")
kiri, _ = st.columns([1.1, 1])
with kiri:
    if (masalah := akun.masalah_konfigurasi()) is not None:
        st.html(f'<div class="errBox"><b class="h">Fitur akun belum tersedia</b>{escape(masalah)}</div>')
        st.stop()

    sesi = akun.pengguna_aktif()

    if sesi is not None:
        with st.container(key="card_akun_aktif"):
            st.html(judul_kartu("Anda sudah masuk")
                    + f'<div class="kv"><span>Nama</span><b>{escape(sesi.nama)}</b>'
                    f'<span>Email</span><span>{escape(sesi.email)}</span></div>')
            c1, c2 = st.columns(2)
            c1.page_link("views/unggah.py", label="Buka Unggah Data")
            c2.button("Keluar", key="akun_keluar", on_click=akun.keluar)
        st.stop()

    st.session_state.setdefault(akun.KUNCI_MODE, MASUK)
    mode = st.segmented_control("Mode akun", [MASUK, DAFTAR], key=akun.KUNCI_MODE,
                                label_visibility="collapsed") or MASUK
    tampil_pesan()
    with st.container(key="card_akun_form"):
        if mode == MASUK:
            st.html(judul_kartu("Masuk ke akun", "email &amp; password"))
            form_masuk()
        else:
            st.html(judul_kartu("Daftar akun baru", "tanpa konfirmasi email"))
            form_daftar()
    st.html('<div class="note">Akun hanya dipakai untuk membuka fitur Unggah Data. Sesi tersimpan selama tab '
            'browser terbuka; memuat ulang halaman akan mengeluarkan Anda.</div>')
