"""Halaman Profil Akun — info akun (Supabase Auth), ubah nama, ganti password, riwayat unggahan sesi ini."""
from html import escape

import streamlit as st

from auth.supabase import AuthError, validasi_ganti_password, validasi_nama
from components import akun, riwayat
from components.bahasa import t
from components.format import tanggal_pendek, waktu_jakarta
from components.kartu import judul_kartu
from components.tema import judul, label

KUNCI_PROFIL = "profil_data"          # (access token, Profil) — dimuat ulang jika token berganti
KUNCI_PESAN_NAMA = "profil_pesan_nama"
KUNCI_PESAN_PW = "profil_pesan_pw"


def _muat_profil(sesi):
    simpan = st.session_state.get(KUNCI_PROFIL)
    if simpan and simpan[0] == sesi.access_token:
        return simpan[1], None
    try:
        p = akun.klien().profil(sesi.access_token)
    except AuthError as e:
        return None, e.pesan
    st.session_state[KUNCI_PROFIL] = (sesi.access_token, p)
    return p, None


def proses_nama() -> None:
    ss = st.session_state
    nama = ss.get("profil_nama", "")
    if error := validasi_nama(nama):
        ss[KUNCI_PESAN_NAMA] = ("err", error)
        return
    sesi = akun.pengguna_aktif()
    try:
        p = akun.klien().ubah_nama(sesi.access_token, nama)
    except AuthError as e:
        ss[KUNCI_PESAN_NAMA] = ("err", [e.pesan])
        return
    akun.perbarui_nama(p.nama)
    ss[KUNCI_PROFIL] = (akun.pengguna_aktif().access_token, p)
    ss[KUNCI_PESAN_NAMA] = ("ok", [t("Nama tampilan berhasil diperbarui.", "Display name updated.")])


def proses_password() -> None:
    ss = st.session_state
    lama, baru, konfirmasi = (ss.get(k, "") for k in ("pw_lama", "pw_baru", "pw_konfirmasi"))
    for k in ("pw_lama", "pw_baru", "pw_konfirmasi"):  # password tidak dibiarkan tertinggal di form
        ss[k] = ""
    if error := validasi_ganti_password(lama, baru, konfirmasi):
        ss[KUNCI_PESAN_PW] = ("err", error)
        return
    sesi, k = akun.pengguna_aktif(), akun.klien()
    try:
        sesi_baru = k.masuk(sesi.email, lama)  # verifikasi password lama + token segar
    except AuthError as e:
        pesan = t("Password lama salah.", "Incorrect old password.") if e.kode == "invalid_credentials" else e.pesan
        ss[KUNCI_PESAN_PW] = ("err", [pesan])
        return
    try:
        k.ganti_password(sesi_baru.access_token, baru)
    except AuthError as e:
        ss[KUNCI_PESAN_PW] = ("err", [e.pesan])
        return
    akun.simpan_sesi(sesi_baru)
    ss[KUNCI_PESAN_PW] = ("ok", [t("Password berhasil diganti. Gunakan password baru saat masuk berikutnya.",
                                   "Password changed. Use the new password the next time you sign in.")])


def _pesan(kunci: str) -> None:
    if (isi := st.session_state.pop(kunci, None)) is None:
        return
    jenis, daftar = isi
    kelas = "okBox" if jenis == "ok" else "errBox"
    st.html(f'<div class="{kelas}">' + "".join(f"<div>{escape(p)}</div>" for p in daftar) + "</div>")


def kartu_profil(sesi, profil) -> None:
    nama = profil.nama if profil else sesi.nama
    email = profil.email if profil else sesi.email
    inisial = escape((nama.strip()[:1] or "?").upper())
    peran = "Admin" if profil and profil.peran == "admin" else t("Pengguna", "User")
    n = len(riwayat.daftar())
    info = [("calendar_month", t("Terdaftar", "Registered"), waktu_jakarta(profil.dibuat, wib=True) if profil else "–"),
            ("login", t("Masuk terakhir", "Last sign-in"), waktu_jakarta(profil.masuk_terakhir, wib=True) if profil else "–"),
            ("upload_file", t("Unggahan sesi ini", "Uploads this session"), t(f"{n} berkas", f"{n} files"))]
    baris = "".join(f'<div class="pkBaris"><span class="material-symbols-rounded">{ikon}</span><div><span>{k}</span>'
                    f'<b>{escape(v)}</b></div></div>' for ikon, k, v in info)
    with st.container(key="card_profil_info"):
        st.html(f'<div class="pkAtas"><div class="avatarBesar">{inisial}</div><div class="pkNama">{escape(nama)}</div>'
                f'<div class="pkEmail">{escape(email)}</div><span class="pkPeran">{peran}</span></div>'
                f'<div class="pkInfo">{baris}</div>')


def form_nama(nama_sekarang: str) -> None:
    st.session_state.setdefault("profil_nama", nama_sekarang)
    st.html('<div class="pfKet">' + t("Nama ini tampil di sidebar dan di halaman Masuk.",
                                      "This name appears in the sidebar and on the sign-in page.") + '</div>')
    _pesan(KUNCI_PESAN_NAMA)
    with st.form("form_nama", border=False):
        st.text_input(t("Nama", "Name"), key="profil_nama", max_chars=60, autocomplete="name")
        st.form_submit_button(t("Simpan nama", "Save name"), type="primary", on_click=proses_nama, width="stretch",
                              icon=":material/check:")


def form_password() -> None:
    st.html('<div class="pfKet">' + t("Masukkan password lama untuk memastikan ini memang Anda.",
                                      "Enter your old password to confirm it is you.") + '</div>')
    _pesan(KUNCI_PESAN_PW)
    with st.form("form_password", border=False):
        st.text_input(t("Password lama", "Old password"), key="pw_lama", type="password", autocomplete="current-password")
        a, b = st.columns(2, gap="small")
        a.text_input(t("Password baru", "New password"), key="pw_baru", type="password", autocomplete="new-password",
                     help=t("Minimal 6 karakter dan berbeda dari password lama.",
                            "At least 6 characters and different from the old password."))
        b.text_input(t("Konfirmasi password baru", "Confirm new password"), key="pw_konfirmasi", type="password", autocomplete="new-password")
        st.form_submit_button(t("Ganti password", "Change password"), type="primary", on_click=proses_password, width="stretch",
                              icon=":material/lock_reset:")


def pengaturan(nama_sekarang: str) -> None:
    with st.container(key="card_profil_atur"):
        st.html(judul_kartu(t("Pengaturan Akun", "Account Settings"), t("nama &amp; password", "name &amp; password")))
        tab_nama, tab_pw = st.tabs([":material/badge: " + t("Nama tampilan", "Display name"), ":material/lock: Password"])
        with tab_nama:
            form_nama(nama_sekarang)
        with tab_pw:
            form_password()


def tabel_riwayat() -> None:
    data = riwayat.daftar()
    with st.container(key="card_profil_riwayat"):
        st.html(judul_kartu(t("Riwayat Unggahan", "Upload History"),
                            t(f"{len(data)} berkas · hanya sesi ini", f"{len(data)} files · this session only")))
        if not data:
            st.html('<div class="rwKosong"><span class="material-symbols-rounded">history</span><div><b>'
                    + t("Belum ada unggahan pada sesi ini", "No uploads in this session yet") + '</b><span>'
                    + t("Berkas yang berhasil diproses di halaman Unggah Data akan tercatat di sini.",
                        "Files processed on the Upload Data page will be listed here.") + '</span></div></div>')
            with st.container(key="rw_buka"):
                st.page_link("views/unggah.py", label=t("Buka Unggah Data", "Open Upload Data"), icon=":material/upload_file:")
            return
        baris = []
        for r in data:
            ringkas = "".join(
                f'<div class="rwSt"><b>{s["stasiun"].split()[0]}</b> · {s["hari"]} {t("hari s.d.", "days to")} '
                f'{tanggal_pendek(s["tanggal_terakhir"], tahun=True)} · t+1 <b>{s["t1"]}</b> · t+7 <b>{s["t7"]}</b></div>'
                for s in r["stasiun"])
            val = f'{r["n_validasi"]} {t("tanggal", "dates")}' if r["n_validasi"] else "–"
            baris.append(f'<tr><td>{r["waktu"]:%H.%M}</td><td><b>{escape(r["nama_file"])}</b>'
                         f'<div class="diisi">{r["ukuran"] / 1024:.1f} KB</div></td><td>{ringkas}</td>'
                         f'<td class="num">{val}</td></tr>')
        st.html(f'<table class="tbl"><tr><th>{t("Waktu", "Time")}</th><th>{t("Berkas", "File")}</th>'
                f'<th>{t("Stasiun &amp; hasil prediksi (ISPU)", "Stations &amp; forecast (ISPU)")}</th>'
                f'<th class="num">{t("Validasi", "Validation")}</th></tr>{"".join(baris)}</table>')
        st.html('<div class="note">' + t(
            "Riwayat hanya disimpan di memori sesi ini: tidak dikirim ke server dan hilang saat halaman dimuat ulang "
            "atau saat keluar. Isi berkas tidak disimpan.",
            "History is only kept in this session's memory: it is not sent to the server and is cleared on reload or "
            "sign-out. File contents are not stored.") + '</div>')
        st.button(t("Hapus riwayat", "Clear history"), key="hapus_riwayat", on_click=riwayat.hapus)


judul(t("Profil Akun", "Account Profile"), t("Informasi akun, keamanan, dan riwayat unggahan selama sesi ini",
                                             "Account details, security, and upload history for this session"))
sesi = akun.wajib_masuk("views/profil.py", t("Profil Akun", "Account Profile"))
profil, galat = _muat_profil(sesi)
if galat:
    st.html(f'<div class="errBox"><b class="h">{t("Data akun belum dapat dimuat", "Account data could not be loaded")}</b>{escape(galat)}</div>')
with st.container(key="baris_profil"):
    kiri, kanan = st.columns([1, 1.7], gap="medium")
    with kiri:
        kartu_profil(sesi, profil)
    with kanan:
        pengaturan(profil.nama if profil else sesi.nama)

label(t("Aktivitas", "Activity"))
tabel_riwayat()
