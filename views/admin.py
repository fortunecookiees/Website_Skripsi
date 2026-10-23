"""Halaman Admin — kelola pengguna (Supabase Admin API) & perbarui data Dashboard (Supabase Storage).

Akses: role `app_metadata.role == "admin"` diverifikasi di SERVER saat halaman dibuka DAN sebelum setiap aksi.
Service key hanya dipakai lewat auth.admin.KlienAdmin; tidak pernah ditampilkan.
"""
from html import escape

import pandas as pd
import streamlit as st

from auth.admin import AdminError, boleh_diubah
from components import akun
from components import sumber_data as sd
from components.bahasa import t
from components.format import angka, waktu_jakarta
from components.kartu import judul_kartu, kosong, kpi
from components.tema import judul, label
from core.config import STASIUN
from core.teks import terjemah
from core.unggah import baca_file
from core.versi_data import (PATH_MANIFEST, Manifest, buat_versi, ke_csv, label_sumber, muat_data_dashboard,
                             pilih_aktif, tambah_versi, validasi_admin)

KUNCI_PESAN = "admin_pesan"
KUNCI_PENGGUNA = "admin_pengguna"
KUNCI_DATA = "admin_data_valid"   # (file_id, nama file, DataFrame lolos validasi)


def _waktu(iso: str | None, jam: bool = True) -> str:
    """Format ringkas untuk tabel admin: '8 Nov 2025, 13.05' (tanpa jam bila jam=False)."""
    return waktu_jakarta(iso, bulan_pendek=True, jam=jam)


STATUS_EN = {"Aktif": "Active", "Nonaktif": "Inactive", "Belum konfirmasi": "Unconfirmed"}


def _status(s: str) -> str:
    return t(s, STATUS_EN.get(s, s))


def _pesan(jenis: str, teks: str) -> None:
    st.session_state[KUNCI_PESAN] = (jenis, teks)


def _tampil_pesan() -> None:
    if (isi := st.session_state.pop(KUNCI_PESAN, None)) is None:
        return
    jenis, teks = isi
    st.html(f'<div class="{"okBox" if jenis == "ok" else "errBox"}">{escape(teks)}</div>')


def _admin_atau_tolak():
    """Verifikasi ulang role di server sebelum aksi. None = ditolak (pesan sudah diset)."""
    admin = akun.verifikasi_admin()
    if admin is None:
        _pesan("err", t("Akses ditolak: sesi bukan admin atau sudah berakhir.",
                        "Access denied: the session is not an admin or has ended."))
    return admin


# ---------------------------------------------------------------------
# Kelola Pengguna
# ---------------------------------------------------------------------
def _aksi_pengguna(klien, jenis: str, id_pengguna: str) -> None:
    admin = _admin_atau_tolak()
    if admin is None:
        return
    try:
        target = klien.ambil_pengguna(id_pengguna)  # status terbaru dari server, bukan dari tabel di layar
        if (alasan := boleh_diubah(admin.id, target)) is not None:
            _pesan("err", alasan)
            return
        if jenis == "nonaktifkan":
            klien.nonaktifkan(target.id)
            _pesan("ok", t(f"Akun {target.email} dinonaktifkan.", f"Account {target.email} deactivated."))
        elif jenis == "aktifkan":
            klien.aktifkan(target.id)
            _pesan("ok", t(f"Akun {target.email} diaktifkan kembali.", f"Account {target.email} reactivated."))
        elif jenis == "hapus":
            klien.hapus(target.id)
            _pesan("ok", t(f"Akun {target.email} dihapus permanen.", f"Account {target.email} permanently deleted."))
    except AdminError as e:
        _pesan("err", e.pesan)
    st.session_state.pop(KUNCI_PENGGUNA, None)


@st.dialog(t("Hapus akun", "Delete account"))
def dialog_hapus(klien, pengguna) -> None:
    email = escape(pengguna.email)
    st.html('<div class="langkah">' + t(
        f"Akun <b>{email}</b> akan dihapus <b>permanen</b> dari Supabase dan tidak dapat dikembalikan. Ketik ulang "
        "email akun untuk konfirmasi.",
        f"Account <b>{email}</b> will be <b>permanently</b> deleted from Supabase and cannot be restored. Type the "
        "account email to confirm.") + '</div>')
    ketik = st.text_input(t("Email akun", "Account email"), key=f"konfirmasi_hapus_{pengguna.id}", placeholder=pengguna.email)
    c1, c2 = st.columns(2)
    if c1.button(t("Hapus permanen", "Delete permanently"), type="primary", disabled=ketik.strip().lower() != pengguna.email.lower(),
                 key=f"ya_hapus_{pengguna.id}", width="stretch"):
        _aksi_pengguna(klien, "hapus", pengguna.id)
        st.rerun()
    if c2.button(t("Batal", "Cancel"), key=f"batal_hapus_{pengguna.id}", width="stretch"):
        st.rerun()


def tab_pengguna(klien, admin) -> None:
    _tampil_pesan()
    if KUNCI_PENGGUNA not in st.session_state:
        try:
            st.session_state[KUNCI_PENGGUNA] = klien.daftar_pengguna()
        except AdminError as e:
            st.html(f'<div class="errBox"><b class="h">{t("Daftar pengguna gagal dimuat", "Failed to load users")}</b>{escape(e.pesan)}</div>')
            return
    semua = st.session_state[KUNCI_PENGGUNA]
    st.html(kpi([
        (t("Total akun", "Total accounts"), angka(len(semua)), t("terdaftar di Supabase", "registered in Supabase")),
        (t("Aktif", "Active"), angka(sum(p.status == "Aktif" for p in semua)), t("dapat masuk", "can sign in")),
        (t("Nonaktif", "Inactive"), angka(sum(p.nonaktif for p in semua)), t("diblokir admin", "blocked by admin")),
        ("Admin", angka(sum(p.peran == "admin" for p in semua)), t("diatur di Supabase", "set in Supabase")),
    ]))
    c1, c2 = st.columns([3, 1], vertical_alignment="bottom")
    cari = c1.text_input("Cari", placeholder=t("Cari nama atau email…", "Search name or email…"), key="admin_cari", label_visibility="collapsed")
    c2.button(t("Muat ulang", "Reload"), icon=":material/refresh:", key="admin_muat_ulang", width="stretch",
              on_click=lambda: st.session_state.pop(KUNCI_PENGGUNA, None))
    q = cari.strip().lower()
    daftar = [p for p in semua if not q or q in p.email.lower() or q in p.nama.lower()]

    with st.container(key="card_admin_pengguna"):
        st.html(judul_kartu(t("Daftar Pengguna", "Users"),
                            t(f"{len(daftar)} dari {len(semua)} akun", f"{len(daftar)} of {len(semua)} accounts")))
        if not daftar:
            st.html(kosong(t("Tidak ada akun yang cocok", "No matching accounts"),
                           t("Ubah kata kunci pencarian.", "Change the search keyword.")))
            return
        kepala = st.columns([2.6, 1.3, 1.5, 1.1, 2], vertical_alignment="center")
        for kol, teks in zip(kepala, [t("Pengguna", "User"), t("Terdaftar", "Registered"),
                                      t("Masuk terakhir", "Last sign-in"), "Status", t("Aksi", "Actions")]):
            kol.html(f'<div class="uHead">{teks}</div>')
        for p in daftar:
            with st.container(key=f"usr_{p.id}"):
                c = st.columns([2.6, 1.3, 1.5, 1.1, 2], vertical_alignment="center")
                tanda = ""
                if p.id == admin.id:
                    tanda = f'<span class="uTag">{t("Anda", "You")}</span>'
                elif p.peran == "admin":
                    tanda = '<span class="uTag">Admin</span>'
                c[0].html(f'<div class="uNama">{escape(p.nama)}{tanda}</div><div class="uEmail">{escape(p.email)}</div>')
                c[1].html(f'<div class="uTeks">{_waktu(p.dibuat, jam=False)}</div>')
                c[2].html(f'<div class="uTeks">{_waktu(p.masuk_terakhir)}</div>')
                kelas = {"Aktif": "stOn", "Nonaktif": "stOff"}.get(p.status, "stWait")
                c[3].html(f'<span class="uStatus {kelas}">{_status(p.status)}</span>')
                if boleh_diubah(admin.id, p) is not None:
                    c[4].html(f'<div class="uTeks muted">{t("dikelola di Supabase", "managed in Supabase")}</div>'
                              if p.id != admin.id else f'<div class="uTeks muted">{t("akun Anda", "your account")}</div>')
                    continue
                a, b = c[4].columns(2)
                if p.nonaktif:
                    a.button(t("Aktifkan", "Activate"), key=f"on_{p.id}", width="stretch",
                             on_click=_aksi_pengguna, args=(klien, "aktifkan", p.id))
                else:
                    a.button(t("Nonaktifkan", "Deactivate"), key=f"off_{p.id}", width="stretch",
                             on_click=_aksi_pengguna, args=(klien, "nonaktifkan", p.id))
                if b.button(t("Hapus", "Delete"), key=f"del_{p.id}", width="stretch"):
                    dialog_hapus(klien, p)
        st.html('<div class="note">' + t(
            "Akun Anda sendiri dan akun ber-peran admin tidak dapat dinonaktifkan atau dihapus dari aplikasi. Peran "
            "admin diatur melalui dashboard Supabase.",
            "Your own account and admin accounts cannot be deactivated or deleted from the app. The admin role is "
            "set in the Supabase dashboard.") + '</div>')


# ---------------------------------------------------------------------
# Perbarui Data Dashboard
# ---------------------------------------------------------------------
def _manifest(klien, bucket: str) -> Manifest:
    return Manifest.dari_json(klien.unduh(bucket, PATH_MANIFEST))   # selalu baca terbaru (tanpa cache)


def _simpan(klien, bucket: str, aktifkan: bool) -> None:
    admin = _admin_atau_tolak()
    simpan = st.session_state.get(KUNCI_DATA)
    if admin is None or simpan is None:
        return
    _, nama_file, data = simpan
    try:
        v = buat_versi(data, nama_file, admin.email)
        klien.unggah(bucket, v.path, ke_csv(data), "text/csv")
        m = tambah_versi(_manifest(klien, bucket), v, aktifkan=aktifkan)
        klien.unggah(bucket, PATH_MANIFEST, m.ke_json(), "application/json", timpa=True)
    except AdminError as e:
        _pesan("err", e.pesan)
        return
    sd.segarkan_dashboard()
    st.session_state.pop(KUNCI_DATA, None)
    st.session_state["admin_berkas_ver"] = st.session_state.get("admin_berkas_ver", 0) + 1  # kosongkan uploader
    _pesan("ok", t(f"Versi {v.id} tersimpan" + (" dan dipakai Dashboard untuk semua pengguna." if aktifkan else "."),
                   f"Version {v.id} saved" + (" and now used by the Dashboard for all users." if aktifkan else ".")))


def _ganti_aktif(klien, bucket: str, id_versi: str | None) -> None:
    if _admin_atau_tolak() is None:
        return
    try:
        m = pilih_aktif(_manifest(klien, bucket), id_versi)
        klien.unggah(bucket, PATH_MANIFEST, m.ke_json(), "application/json", timpa=True)
    except (AdminError, ValueError) as e:
        _pesan("err", getattr(e, "pesan", terjemah(str(e))))
        return
    sd.segarkan_dashboard()
    _pesan("ok", t("Dashboard kembali memakai dataset penelitian.", "The Dashboard is back on the research dataset.")
           if id_versi is None else t(f"Versi {id_versi} sekarang dipakai Dashboard.",
                                      f"Version {id_versi} is now used by the Dashboard."))


def _ringkasan_unggahan(data: pd.DataFrame, tahun_spasial: int) -> str:
    per = data.groupby("stasiun")["tanggal"].agg(["min", "max", "size"])
    baris = "".join(f'<tr><td>{s.split()[0]}</td><td>{_waktu(per.loc[s, "min"].isoformat(), False)}</td>'
                    f'<td>{_waktu(per.loc[s, "max"].isoformat(), False)}</td><td class="num">{per.loc[s, "size"]}</td></tr>'
                    for s in STASIUN if s in per.index)
    catatan = ""
    if {data["tanggal"].min().year, data["tanggal"].max().year} != {tahun_spasial}:
        catatan = '<div class="note">' + t(
            f"Data berada di luar tahun {tahun_spasial}; kepadatan penduduk &amp; luas RTH tetap memakai nilai "
            f"{tahun_spasial} dari dataset penelitian.",
            f"The data falls outside {tahun_spasial}; population density &amp; green open space keep the "
            f"{tahun_spasial} values from the research dataset.") + '</div>'
    return (f'<table class="tbl"><tr><th>{t("Stasiun", "Station")}</th><th>{t("Mulai", "Start")}</th>'
            f'<th>{t("Akhir", "End")}</th><th class="num">{t("Hari", "Days")}</th></tr>{baris}</table>{catatan}')


def tab_data(klien, bucket: str) -> None:
    _tampil_pesan()
    try:
        m = _manifest(klien, bucket)
    except AdminError as e:
        st.html(f'<div class="errBox"><b class="h">{t("Storage belum dapat diakses", "Storage is not accessible")}</b>{escape(e.pesan)}</div>')
        return
    tahun_spasial = int(sd.dataset()["tanggal"].dt.year.max())

    # status & unggah berdampingan; riwayat versi tetap selebar halaman
    with st.container(key="baris_admin_data"):
        kiri, kanan = st.columns([1, 1.45], gap="medium")
        with kiri:
            # status sumber data saat ini (dibaca langsung dari Storage, bukan cache Dashboard)
            _, sumber = muat_data_dashboard(lambda path: klien.unduh(bucket, path), sd.dataset())
            with st.container(key="card_admin_status"):
                st.html(judul_kartu(t("Sumber Data Dashboard Saat Ini", "Current Dashboard Data Source"),
                                    t("Mode Aktual · semua pengguna", "Actual Mode · all users"))
                        + f'<div class="sumberData {"srcAdmin" if sumber.versi else "srcRiset"}"><span class="dot"></span>'
                        f'{escape(label_sumber(sumber, sd.tanggal_terakhir(), en=t(False, True)))}</div>'
                        + (f'<div class="errBox">{escape(terjemah(sumber.peringatan))}</div>' if sumber.peringatan else "")
                        + '<div class="note">' + t(
                            "Evaluation, Data Historis, metrik, dan model tetap memakai dataset penelitian. Rentang "
                            "slider simulasi juga tetap dari dataset penelitian.",
                            "Evaluation, Historical Data, metrics, and the model keep using the research dataset. "
                            "Simulation slider ranges also stay based on the research dataset.") + '</div>')
                st.button(t("Kembali ke dataset penelitian", "Back to the research dataset"), key="admin_ke_riset", disabled=m.aktif is None,
                          icon=":material/restart_alt:", on_click=_ganti_aktif, args=(klien, bucket, None))
        with kanan:
            with st.container(key="card_admin_unggah"):
                st.html(judul_kartu(t("Data Harian Terbaru", "Latest Daily Data"), ".xlsx / .csv")
                        + '<div class="langkah">' + t(
                            "Format sama dengan template Unggah Data. Syarat tambahan: <b>kelima stasiun wajib ada</b>, "
                            "minimal 4 hari berturut-turut per stasiun, PM2.5 terisi di 4 hari terakhir, dan "
                            "meteorologi terisi di hari terakhir.",
                            "Same format as the Upload Data template. Extra requirements: <b>all five stations must be "
                            "present</b>, at least 4 consecutive days per station, PM2.5 filled for the last 4 days, "
                            "and weather filled for the last day.") + '</div>')
                st.download_button(t("Unduh template (.xlsx)", "Download template (.xlsx)"), sd.template_unggah(), file_name="template_data_dashboard.xlsx",
                                   mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                   key="admin_template", icon=":material/download:")
                berkas = st.file_uploader("Berkas data", type=["xlsx", "csv"], label_visibility="collapsed",
                                          key=f"admin_berkas_{st.session_state.get('admin_berkas_ver', 0)}")
                if berkas is not None:
                    try:
                        data, error, info = validasi_admin(baca_file(berkas.getvalue(), berkas.name))
                    except ValueError as e:
                        data, error, info = None, [str(e)], []
                    if data is None:
                        st.session_state.pop(KUNCI_DATA, None)
                        st.html(f'<div class="errBox"><b class="h">{t("Data belum dapat disimpan", "The data cannot be saved yet")}</b><ul>'
                                + "".join(f"<li>{p}</li>" for p in error) + "</ul></div>")
                    else:
                        st.session_state[KUNCI_DATA] = (berkas.file_id, berkas.name, data)
                        a_, b_ = f'{data["tanggal"].min():%d-%m-%Y}', f'{data["tanggal"].max():%d-%m-%Y}'
                        st.html('<div class="okBox">' + t(f"Data lolos validasi: {len(data)} baris, {a_} s.d. {b_}.",
                                                          f"Data passed validation: {len(data)} rows, {a_} to {b_}.")
                                + '</div>'
                                + _ringkasan_unggahan(data, tahun_spasial)
                                + (f'<div class="note">{" ".join(info)}</div>' if info else ""))
                        a, b = st.columns(2)
                        a.button(t("Simpan & jadikan aktif", "Save & activate"), type="primary", key="admin_simpan_aktif", width="stretch",
                                 on_click=_simpan, args=(klien, bucket, True))
                        b.button(t("Simpan saja", "Save only"), key="admin_simpan", width="stretch", on_click=_simpan, args=(klien, bucket, False))

    label(t("Riwayat Versi", "Version History"))
    with st.container(key="card_admin_versi"):
        st.html(judul_kartu(t("Versi Data Dashboard", "Dashboard Data Versions"),
                            t(f"{len(m.versi)} versi", f"{len(m.versi)} versions")))
        if not m.versi:
            st.html(kosong(t("Belum ada versi", "No versions yet"),
                           t("Dashboard memakai dataset penelitian sampai admin mengunggah data.",
                             "The Dashboard uses the research dataset until an admin uploads data.")))
            return
        kepala = st.columns([1.6, 1.8, 1.9, 0.8, 1.3], vertical_alignment="center")
        for kol, teks in zip(kepala, [t("Diunggah", "Uploaded"), t("Pengunggah · berkas", "Uploader · file"),
                                      t("Rentang data", "Data range"), t("Baris", "Rows"), ""]):
            kol.html(f'<div class="uHead">{teks}</div>')
        for v in m.versi:
            with st.container(key=f"ver_{v.id}"):
                c = st.columns([1.6, 1.8, 1.9, 0.8, 1.3], vertical_alignment="center")
                c[0].html(f'<div class="uNama">{_waktu(v.diunggah)}</div><div class="uEmail">{escape(v.id)}</div>')
                c[1].html(f'<div class="uTeks">{escape(v.pengunggah)}</div><div class="uEmail">{escape(v.nama_file)}</div>')
                c[2].html(f'<div class="uTeks">{_waktu(v.mulai, False)} – {_waktu(v.akhir, False)}</div>')
                c[3].html(f'<div class="uTeks">{angka(v.n_baris)}</div>')
                if v.id == m.aktif:
                    c[4].html(f'<span class="uStatus stOn">{t("Aktif", "Active")}</span>')
                else:
                    c[4].button(t("Jadikan aktif", "Activate"), key=f"aktif_{v.id}", width="stretch",
                                on_click=_ganti_aktif, args=(klien, bucket, v.id))


# --- halaman ------------------------------------------------------------
judul("Admin", t("Kelola pengguna dan data Dashboard", "Manage users and Dashboard data"))
admin = akun.wajib_admin("views/admin.py")
konfigurasi, masalah = akun.klien_admin()
if konfigurasi is None:
    st.html(f'<div class="errBox"><b class="h">{t("Fitur admin belum dikonfigurasi", "Admin is not configured")}'
            f'</b>{escape(masalah)} ' + t("Isi <code>service_key</code> dan <code>bucket</code> pada",
                                          "Fill in <code>service_key</code> and <code>bucket</code> in")
            + ' <code>.streamlit/secrets.toml</code> ' + t("(lihat", "(see") + ' <code>secrets.example.toml</code>).</div>')
    st.stop()
klien, bucket = konfigurasi

tab1, tab2 = st.tabs([t("Kelola Pengguna", "Manage Users"), t("Perbarui Data Dashboard", "Update Dashboard Data")])
with tab1:
    tab_pengguna(klien, admin)
with tab2:
    tab_data(klien, bucket)
