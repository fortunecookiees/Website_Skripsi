"""Halaman Masuk / Daftar (Supabase Auth). Diproses lewat callback agar field password bisa dikosongkan."""
from html import escape

import streamlit as st

from auth.supabase import AuthError, validasi_daftar, validasi_masuk
from components import akun
from components.bahasa import t
from components.kartu import judul_kartu
from components.logo import NAMA, hiasan_uri, logo_svg, tagline
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
    _berhasil(sesi, t(f"Selamat datang kembali, {sesi.nama}.", f"Welcome back, {sesi.nama}."))


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
        ss[KUNCI_INFO] = t("Akun dibuat. Periksa email Anda untuk konfirmasi, lalu masuk.",
                           "Account created. Check your email to confirm it, then sign in.")
        ss[akun.KUNCI_MODE] = MASUK
        return
    _berhasil(sesi, t(f"Akun berhasil dibuat. Selamat datang, {sesi.nama}.",
                      f"Account created. Welcome, {sesi.nama}."))


def tampil_pesan() -> None:
    if info := st.session_state.pop(KUNCI_INFO, None):
        st.html(f'<div class="infoBox"><span class="dot"></span><span>{escape(info)}</span></div>')
    if pesan := st.session_state.pop(KUNCI_ERROR, None):
        daftar = "".join(f"<li>{escape(p)}</li>" for p in pesan)
        st.html(f'<div class="errBox"><b class="h">{t("Belum berhasil", "Not successful")}</b><ul>{daftar}</ul></div>')


def ganti_mode(mode: str) -> None:
    st.session_state[akun.KUNCI_MODE] = mode
    st.session_state.pop(KUNCI_ERROR, None)


# teks panel samping: ((judul), (isi), (label tombol), mode tujuan) — tiap teks (Indonesia, English)
PANEL = {
    MASUK: (("Belum punya akun?", "No account yet?"),
            ("Daftar untuk mengunggah data harian Anda sendiri dan melihat prediksi PM2.5 tujuh hari ke depan.",
             "Register to upload your own daily data and see the seven-day PM2.5 forecast."),
            ("Daftar akun baru", "Create account"), DAFTAR),
    DAFTAR: (("Sudah punya akun?", "Already have an account?"),
             ("Masuk kembali untuk melanjutkan ke fitur Unggah Data.", "Sign in to continue to Upload Data."),
             ("Masuk", "Sign in"), MASUK),
}
FORM = {
    MASUK: (("Masuk ke akun", "Sign in"), ("Gunakan email dan password yang sudah terdaftar.",
                                           "Use your registered email and password.")),
    DAFTAR: (("Buat akun baru", "Create an account"), ("Cukup nama, email, dan password.",
                                                      "Just a name, email, and password.")),
}


def panel_samping(mode: str) -> None:
    judul_p, isi, tombol, tujuan = PANEL[mode]
    judul_p, isi, tombol = t(*judul_p), t(*isi), t(*tombol)
    with st.container(key="auth_panel"):
        st.html(f'<img class="apMotif" src="{hiasan_uri("#FFFFFF")}" alt="">'
                f'<div class="apBrand">{logo_svg(42)}<div><b>{NAMA}</b><span>{tagline()}</span></div></div>'
                f'<div class="apTeks"><div class="apJudul">{judul_p}</div><p>{isi}</p></div>')
        st.button(tombol, key="auth_ganti", on_click=ganti_mode, args=(tujuan,),
                  icon=":material/person_add:" if tujuan == DAFTAR else ":material/login:")


def form_masuk() -> None:
    with st.form("form_masuk", border=False):
        st.text_input("Email", key="masuk_email", placeholder="nama@email.com", autocomplete="email")
        st.text_input("Password", key="masuk_password", type="password", autocomplete="current-password")
        st.form_submit_button(t("Masuk", "Sign in"), type="primary", on_click=proses_masuk, width="stretch")


def form_daftar() -> None:
    with st.form("form_daftar", border=False):
        st.text_input(t("Nama", "Name"), key="daftar_nama", placeholder=t("Nama lengkap", "Full name"),
                      autocomplete="name")
        st.text_input("Email", key="daftar_email", placeholder="nama@email.com", autocomplete="email")
        st.text_input("Password", key="daftar_password", type="password", autocomplete="new-password",
                      help=t("Minimal 6 karakter.", "At least 6 characters."))
        st.text_input(t("Konfirmasi password", "Confirm password"), key="daftar_konfirmasi", type="password",
                      autocomplete="new-password")
        st.form_submit_button(t("Daftar", "Register"), type="primary", on_click=proses_daftar, width="stretch")


# --- halaman ------------------------------------------------------------
if tujuan := st.session_state.pop(KUNCI_ARAHKAN, None):
    st.switch_page(tujuan)

judul(t("Akun", "Account"), t("Masuk atau daftar untuk memakai fitur Unggah Data",
                              "Sign in or register to use Upload Data"))
_, tengah, _ = st.columns([1, 1.6, 1])  # form di tengah halaman
with tengah:
    if (masalah := akun.masalah_konfigurasi()) is not None:
        st.html(f'<div class="errBox"><b class="h">{t("Fitur akun belum tersedia", "Accounts are not available")}</b>{escape(masalah)}</div>')
        st.stop()

    sesi = akun.pengguna_aktif()

    if sesi is not None:
        with st.container(key="card_akun_aktif"):
            inisial = escape((sesi.nama.strip()[:1] or "?").upper())
            st.html(judul_kartu(t("Anda sudah masuk", "You are signed in"), t("akun aktif", "active account"))
                    + f'<div class="akunAktif"><div class="aaAvatar">{inisial}</div><div class="aaTeks">'
                    f'<div class="aaNama">{escape(sesi.nama)}</div><div class="aaEmail">{escape(sesi.email)}</div>'
                    '</div></div>')
            c1, c2, c3 = st.columns([1.35, 1.1, 0.9], gap="small", vertical_alignment="center")
            with c1, st.container(key="aa_unggah"):
                st.page_link("views/unggah.py", label=t("Buka Unggah Data", "Open Upload Data"), icon=":material/upload_file:")
            with c2, st.container(key="aa_profil"):
                st.page_link("views/profil.py", label=t("Lihat Profil", "View Profile"), icon=":material/account_circle:")
            c3.button(t("Keluar", "Sign out"), key="akun_keluar", on_click=akun.keluar, icon=":material/logout:", width="stretch")
        st.stop()

    mode = st.session_state.setdefault(akun.KUNCI_MODE, MASUK)
    if mode not in PANEL:
        mode = st.session_state[akun.KUNCI_MODE] = MASUK

# kartu dua sisi: panel gradasi + form; saat Daftar posisinya bertukar (kunci berbeda -> animasi diputar ulang)
_, tengah, _ = st.columns([0.25, 3, 0.25])
with tengah:
    with st.container(key=f"auth_{mode.lower()}"):
        if mode == MASUK:
            kol_panel, kol_form = st.columns([1, 1.2])
        else:
            kol_form, kol_panel = st.columns([1.2, 1])
        with kol_panel:
            panel_samping(mode)
        with kol_form, st.container(key="auth_form"):
            judul_f, sub = (t(*x) for x in FORM[mode])
            st.html(f'<div class="afJudul">{judul_f}</div><div class="afSub">{sub}</div>')
            tampil_pesan()
            if mode == MASUK:
                form_masuk()
            else:
                form_daftar()
    st.html('<div class="note" style="text-align:center">' + t(
        "Akun hanya dipakai untuk membuka fitur Unggah Data. Sesi tersimpan selama tab browser terbuka; memuat ulang "
        "halaman akan mengeluarkan Anda.",
        "Accounts are only used to unlock Upload Data. Your session lasts while the browser tab is open; reloading "
        "the page signs you out.") + '</div>')
