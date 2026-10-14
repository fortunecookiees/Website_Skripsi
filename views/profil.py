"""Halaman Profil Akun — info akun (Supabase Auth), ubah nama, ganti password, riwayat unggahan sesi ini."""
from html import escape

import pandas as pd
import streamlit as st

from auth.supabase import AuthError, validasi_ganti_password, validasi_nama
from components import akun, riwayat
from components.format import BULAN, tanggal_pendek
from components.kartu import judul_kartu, kosong
from components.tema import judul, label

KUNCI_PROFIL = "profil_data"          # (access token, Profil) — dimuat ulang jika token berganti
KUNCI_PESAN_NAMA = "profil_pesan_nama"
KUNCI_PESAN_PW = "profil_pesan_pw"


def _waktu(iso: str | None) -> str:
    if not iso:
        return "–"
    t = pd.Timestamp(iso)
    t = (t.tz_convert("Asia/Jakarta") if t.tzinfo else t.tz_localize("UTC").tz_convert("Asia/Jakarta"))
    return f"{t.day} {BULAN[t.month - 1]} {t.year}, {t:%H.%M} WIB"


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
    ss[KUNCI_PESAN_NAMA] = ("ok", ["Nama tampilan berhasil diperbarui."])


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
        pesan = "Password lama salah." if e.kode == "invalid_credentials" else e.pesan
        ss[KUNCI_PESAN_PW] = ("err", [pesan])
        return
    try:
        k.ganti_password(sesi_baru.access_token, baru)
    except AuthError as e:
        ss[KUNCI_PESAN_PW] = ("err", [e.pesan])
        return
    akun.simpan_sesi(sesi_baru)
    ss[KUNCI_PESAN_PW] = ("ok", ["Password berhasil diganti. Gunakan password baru saat masuk berikutnya."])


def _pesan(kunci: str) -> None:
    if (isi := st.session_state.pop(kunci, None)) is None:
        return
    jenis, daftar = isi
    kelas = "okBox" if jenis == "ok" else "errBox"
    st.html(f'<div class="{kelas}">' + "".join(f"<div>{escape(p)}</div>" for p in daftar) + "</div>")


def kepala(sesi, profil) -> None:
    nama = profil.nama if profil else sesi.nama
    email = profil.email if profil else sesi.email
    inisial = escape((nama.strip()[:1] or "?").upper())
    chip = ""
    if profil:
        chip = (f'<span class="pChip">Terdaftar {escape(_waktu(profil.dibuat))}</span>'
                f'<span class="pChip">Masuk terakhir {escape(_waktu(profil.masuk_terakhir))}</span>')
    st.html(f'<div class="profilHero"><div class="avatarBesar">{inisial}</div><div class="phTeks">'
            f'<div class="phNama">{escape(nama)}</div><div class="phEmail">{escape(email)}</div>'
            f'<div class="phChips">{chip}</div></div></div>')


def form_nama(nama_sekarang: str) -> None:
    st.session_state.setdefault("profil_nama", nama_sekarang)
    with st.container(key="card_profil_nama"):
        st.html(judul_kartu("Ubah Nama Tampilan", "user_metadata"))
        _pesan(KUNCI_PESAN_NAMA)
        with st.form("form_nama", border=False):
            st.text_input("Nama", key="profil_nama", max_chars=60, autocomplete="name")
            st.form_submit_button("Simpan nama", type="primary", on_click=proses_nama, width="stretch")


def form_password() -> None:
    with st.container(key="card_profil_password"):
        st.html(judul_kartu("Ganti Password", "keamanan"))
        _pesan(KUNCI_PESAN_PW)
        with st.form("form_password", border=False):
            st.text_input("Password lama", key="pw_lama", type="password", autocomplete="current-password")
            st.text_input("Password baru", key="pw_baru", type="password", autocomplete="new-password",
                          help="Minimal 6 karakter dan berbeda dari password lama.")
            st.text_input("Konfirmasi password baru", key="pw_konfirmasi", type="password",
                          autocomplete="new-password")
            st.form_submit_button("Ganti password", type="primary", on_click=proses_password, width="stretch")


def tabel_riwayat() -> None:
    data = riwayat.daftar()
    with st.container(key="card_profil_riwayat"):
        st.html(judul_kartu("Riwayat Unggahan", f"{len(data)} berkas · hanya sesi ini"))
        if not data:
            st.html(kosong("Belum ada unggahan pada sesi ini",
                           "Berkas yang berhasil diproses di halaman Unggah Data akan tercatat di sini."))
            st.page_link("views/unggah.py", label="Buka Unggah Data", icon=":material/upload_file:")
            return
        baris = []
        for r in data:
            ringkas = "".join(
                f'<div class="rwSt"><b>{s["stasiun"].split()[0]}</b> · {s["hari"]} hari s.d. '
                f'{tanggal_pendek(s["tanggal_terakhir"], tahun=True)} · t+1 <b>{s["t1"]}</b> · t+7 <b>{s["t7"]}</b></div>'
                for s in r["stasiun"])
            val = f'{r["n_validasi"]} tanggal' if r["n_validasi"] else "–"
            baris.append(f'<tr><td>{r["waktu"]:%H.%M}</td><td><b>{escape(r["nama_file"])}</b>'
                         f'<div class="diisi">{r["ukuran"] / 1024:.1f} KB</div></td><td>{ringkas}</td>'
                         f'<td class="num">{val}</td></tr>')
        st.html('<table class="tbl"><tr><th>Waktu</th><th>Berkas</th><th>Stasiun &amp; hasil prediksi (ISPU)</th>'
                f'<th class="num">Validasi</th></tr>{"".join(baris)}</table>')
        st.html('<div class="note">Riwayat hanya disimpan di memori sesi ini: tidak dikirim ke server dan hilang '
                'saat halaman dimuat ulang atau saat keluar. Isi berkas tidak disimpan.</div>')
        st.button("Hapus riwayat", key="hapus_riwayat", on_click=riwayat.hapus)


judul("Profil Akun", "Informasi akun, keamanan, dan riwayat unggahan selama sesi ini")
sesi = akun.wajib_masuk("views/profil.py", "Profil Akun")
profil, galat = _muat_profil(sesi)
if galat:
    st.html(f'<div class="errBox"><b class="h">Data akun belum dapat dimuat</b>{escape(galat)}</div>')
kepala(sesi, profil)

kiri, kanan = st.columns(2, gap="medium")
with kiri:
    form_nama(profil.nama if profil else sesi.nama)
with kanan:
    form_password()

label("Aktivitas")
tabel_riwayat()
