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
from components.format import BULAN, angka
from components.kartu import judul_kartu, kosong, kpi
from components.tema import judul, label
from core.config import STASIUN
from core.unggah import baca_file
from core.versi_data import (PATH_MANIFEST, Manifest, buat_versi, ke_csv, label_sumber, muat_data_dashboard,
                             pilih_aktif, tambah_versi, validasi_admin)

KUNCI_PESAN = "admin_pesan"
KUNCI_PENGGUNA = "admin_pengguna"
KUNCI_DATA = "admin_data_valid"   # (file_id, nama file, DataFrame lolos validasi)


def _waktu(iso: str | None, jam: bool = True) -> str:
    if not iso:
        return "–"
    t = pd.Timestamp(iso)
    t = t.tz_convert("Asia/Jakarta") if t.tzinfo else t.tz_localize("UTC").tz_convert("Asia/Jakarta")
    teks = f"{t.day} {BULAN[t.month - 1][:3]} {t.year}"
    return f"{teks}, {t:%H.%M}" if jam else teks


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
        _pesan("err", "Akses ditolak: sesi bukan admin atau sudah berakhir.")
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
            _pesan("ok", f"Akun {target.email} dinonaktifkan.")
        elif jenis == "aktifkan":
            klien.aktifkan(target.id)
            _pesan("ok", f"Akun {target.email} diaktifkan kembali.")
        elif jenis == "hapus":
            klien.hapus(target.id)
            _pesan("ok", f"Akun {target.email} dihapus permanen.")
    except AdminError as e:
        _pesan("err", e.pesan)
    st.session_state.pop(KUNCI_PENGGUNA, None)


@st.dialog("Hapus akun")
def dialog_hapus(klien, pengguna) -> None:
    st.html(f'<div class="langkah">Akun <b>{escape(pengguna.email)}</b> akan dihapus <b>permanen</b> dari Supabase '
            'dan tidak dapat dikembalikan. Ketik ulang email akun untuk konfirmasi.</div>')
    ketik = st.text_input("Email akun", key=f"konfirmasi_hapus_{pengguna.id}", placeholder=pengguna.email)
    c1, c2 = st.columns(2)
    if c1.button("Hapus permanen", type="primary", disabled=ketik.strip().lower() != pengguna.email.lower(),
                 key=f"ya_hapus_{pengguna.id}", width="stretch"):
        _aksi_pengguna(klien, "hapus", pengguna.id)
        st.rerun()
    if c2.button("Batal", key=f"batal_hapus_{pengguna.id}", width="stretch"):
        st.rerun()


def tab_pengguna(klien, admin) -> None:
    _tampil_pesan()
    if KUNCI_PENGGUNA not in st.session_state:
        try:
            st.session_state[KUNCI_PENGGUNA] = klien.daftar_pengguna()
        except AdminError as e:
            st.html(f'<div class="errBox"><b class="h">Daftar pengguna gagal dimuat</b>{escape(e.pesan)}</div>')
            return
    semua = st.session_state[KUNCI_PENGGUNA]
    st.html(kpi([
        ("Total akun", angka(len(semua)), "terdaftar di Supabase"),
        ("Aktif", angka(sum(p.status == "Aktif" for p in semua)), "dapat masuk"),
        ("Nonaktif", angka(sum(p.nonaktif for p in semua)), "diblokir admin"),
        ("Admin", angka(sum(p.peran == "admin" for p in semua)), "diatur di Supabase"),
    ]))
    c1, c2 = st.columns([3, 1], vertical_alignment="bottom")
    cari = c1.text_input("Cari", placeholder="Cari nama atau email…", key="admin_cari", label_visibility="collapsed")
    c2.button("Muat ulang", icon=":material/refresh:", key="admin_muat_ulang", width="stretch",
              on_click=lambda: st.session_state.pop(KUNCI_PENGGUNA, None))
    q = cari.strip().lower()
    daftar = [p for p in semua if not q or q in p.email.lower() or q in p.nama.lower()]

    with st.container(key="card_admin_pengguna"):
        st.html(judul_kartu("Daftar Pengguna", f"{len(daftar)} dari {len(semua)} akun"))
        if not daftar:
            st.html(kosong("Tidak ada akun yang cocok", "Ubah kata kunci pencarian."))
            return
        kepala = st.columns([2.6, 1.3, 1.5, 1.1, 2], vertical_alignment="center")
        for kol, teks in zip(kepala, ["Pengguna", "Terdaftar", "Masuk terakhir", "Status", "Aksi"]):
            kol.html(f'<div class="uHead">{teks}</div>')
        for p in daftar:
            with st.container(key=f"usr_{p.id}"):
                c = st.columns([2.6, 1.3, 1.5, 1.1, 2], vertical_alignment="center")
                tanda = ""
                if p.id == admin.id:
                    tanda = '<span class="uTag">Anda</span>'
                elif p.peran == "admin":
                    tanda = '<span class="uTag">Admin</span>'
                c[0].html(f'<div class="uNama">{escape(p.nama)}{tanda}</div><div class="uEmail">{escape(p.email)}</div>')
                c[1].html(f'<div class="uTeks">{_waktu(p.dibuat, jam=False)}</div>')
                c[2].html(f'<div class="uTeks">{_waktu(p.masuk_terakhir)}</div>')
                kelas = {"Aktif": "stOn", "Nonaktif": "stOff"}.get(p.status, "stWait")
                c[3].html(f'<span class="uStatus {kelas}">{p.status}</span>')
                if boleh_diubah(admin.id, p) is not None:
                    c[4].html('<div class="uTeks muted">dikelola di Supabase</div>' if p.id != admin.id
                              else '<div class="uTeks muted">akun Anda</div>')
                    continue
                a, b = c[4].columns(2)
                if p.nonaktif:
                    a.button("Aktifkan", key=f"on_{p.id}", width="stretch",
                             on_click=_aksi_pengguna, args=(klien, "aktifkan", p.id))
                else:
                    a.button("Nonaktifkan", key=f"off_{p.id}", width="stretch",
                             on_click=_aksi_pengguna, args=(klien, "nonaktifkan", p.id))
                if b.button("Hapus", key=f"del_{p.id}", width="stretch"):
                    dialog_hapus(klien, p)
        st.html('<div class="note">Akun Anda sendiri dan akun ber-peran admin tidak dapat dinonaktifkan atau dihapus '
                'dari aplikasi. Peran admin diatur melalui dashboard Supabase.</div>')


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
    _pesan("ok", f"Versi {v.id} tersimpan" + (" dan dipakai Dashboard untuk semua pengguna." if aktifkan else "."))


def _ganti_aktif(klien, bucket: str, id_versi: str | None) -> None:
    if _admin_atau_tolak() is None:
        return
    try:
        m = pilih_aktif(_manifest(klien, bucket), id_versi)
        klien.unggah(bucket, PATH_MANIFEST, m.ke_json(), "application/json", timpa=True)
    except (AdminError, ValueError) as e:
        _pesan("err", getattr(e, "pesan", str(e)))
        return
    sd.segarkan_dashboard()
    _pesan("ok", "Dashboard kembali memakai dataset penelitian." if id_versi is None
           else f"Versi {id_versi} sekarang dipakai Dashboard.")


def _ringkasan_unggahan(data: pd.DataFrame, tahun_spasial: int) -> str:
    per = data.groupby("stasiun")["tanggal"].agg(["min", "max", "size"])
    baris = "".join(f'<tr><td>{s.split()[0]}</td><td>{_waktu(per.loc[s, "min"].isoformat(), False)}</td>'
                    f'<td>{_waktu(per.loc[s, "max"].isoformat(), False)}</td><td class="num">{per.loc[s, "size"]}</td></tr>'
                    for s in STASIUN if s in per.index)
    catatan = ""
    if {data["tanggal"].min().year, data["tanggal"].max().year} != {tahun_spasial}:
        catatan = (f'<div class="note">Data berada di luar tahun {tahun_spasial}; kepadatan penduduk &amp; luas RTH '
                   f'tetap memakai nilai {tahun_spasial} dari dataset penelitian.</div>')
    return ('<table class="tbl"><tr><th>Stasiun</th><th>Mulai</th><th>Akhir</th><th class="num">Hari</th></tr>'
            f'{baris}</table>{catatan}')


def tab_data(klien, bucket: str) -> None:
    _tampil_pesan()
    try:
        m = _manifest(klien, bucket)
    except AdminError as e:
        st.html(f'<div class="errBox"><b class="h">Storage belum dapat diakses</b>{escape(e.pesan)}</div>')
        return
    tahun_spasial = int(sd.dataset()["tanggal"].dt.year.max())

    # status sumber data saat ini (dibaca langsung dari Storage, bukan cache Dashboard)
    _, sumber = muat_data_dashboard(lambda path: klien.unduh(bucket, path), sd.dataset())
    with st.container(key="card_admin_status"):
        st.html(judul_kartu("Sumber Data Dashboard Saat Ini", "Mode Aktual · semua pengguna")
                + f'<div class="sumberData {"srcAdmin" if sumber.versi else "srcRiset"}"><span class="dot"></span>'
                f'{escape(label_sumber(sumber, sd.tanggal_terakhir()))}</div>'
                + (f'<div class="errBox">{escape(sumber.peringatan)}</div>' if sumber.peringatan else "")
                + '<div class="note">Evaluation, Data Historis, metrik, dan model tetap memakai dataset penelitian. '
                  'Rentang slider simulasi juga tetap dari dataset penelitian.</div>')
        st.button("Kembali ke dataset penelitian", key="admin_ke_riset", disabled=m.aktif is None,
                  icon=":material/restart_alt:", on_click=_ganti_aktif, args=(klien, bucket, None))

    label("Unggah Versi Baru")
    with st.container(key="card_admin_unggah"):
        st.html(judul_kartu("Data Harian Terbaru", ".xlsx / .csv")
                + '<div class="langkah">Format sama dengan template Unggah Data. Syarat tambahan: <b>kelima stasiun '
                  'wajib ada</b>, minimal 4 hari berturut-turut per stasiun, PM2.5 terisi di 4 hari terakhir, dan '
                  'meteorologi terisi di hari terakhir.</div>')
        st.download_button("Unduh template (.xlsx)", sd.template_unggah(), file_name="template_data_dashboard.xlsx",
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
                st.html('<div class="errBox"><b class="h">Data belum dapat disimpan</b><ul>'
                        + "".join(f"<li>{p}</li>" for p in error) + "</ul></div>")
            else:
                st.session_state[KUNCI_DATA] = (berkas.file_id, berkas.name, data)
                st.html('<div class="okBox">Data lolos validasi: '
                        f'{len(data)} baris, {data["tanggal"].min():%d-%m-%Y} s.d. {data["tanggal"].max():%d-%m-%Y}.</div>'
                        + _ringkasan_unggahan(data, tahun_spasial)
                        + (f'<div class="note">{" ".join(info)}</div>' if info else ""))
                a, b = st.columns(2)
                a.button("Simpan & jadikan aktif", type="primary", key="admin_simpan_aktif", width="stretch",
                         on_click=_simpan, args=(klien, bucket, True))
                b.button("Simpan saja", key="admin_simpan", width="stretch", on_click=_simpan, args=(klien, bucket, False))

    label("Riwayat Versi")
    with st.container(key="card_admin_versi"):
        st.html(judul_kartu("Versi Data Dashboard", f"{len(m.versi)} versi"))
        if not m.versi:
            st.html(kosong("Belum ada versi", "Dashboard memakai dataset penelitian sampai admin mengunggah data."))
            return
        kepala = st.columns([1.6, 1.8, 1.9, 0.8, 1.3], vertical_alignment="center")
        for kol, teks in zip(kepala, ["Diunggah", "Pengunggah · berkas", "Rentang data", "Baris", ""]):
            kol.html(f'<div class="uHead">{teks}</div>')
        for v in m.versi:
            with st.container(key=f"ver_{v.id}"):
                c = st.columns([1.6, 1.8, 1.9, 0.8, 1.3], vertical_alignment="center")
                c[0].html(f'<div class="uNama">{_waktu(v.diunggah)}</div><div class="uEmail">{escape(v.id)}</div>')
                c[1].html(f'<div class="uTeks">{escape(v.pengunggah)}</div><div class="uEmail">{escape(v.nama_file)}</div>')
                c[2].html(f'<div class="uTeks">{_waktu(v.mulai, False)} – {_waktu(v.akhir, False)}</div>')
                c[3].html(f'<div class="uTeks">{angka(v.n_baris)}</div>')
                if v.id == m.aktif:
                    c[4].html('<span class="uStatus stOn">Aktif</span>')
                else:
                    c[4].button("Jadikan aktif", key=f"aktif_{v.id}", width="stretch",
                                on_click=_ganti_aktif, args=(klien, bucket, v.id))


# --- halaman ------------------------------------------------------------
judul("Admin", "Kelola pengguna dan data Dashboard")
admin = akun.wajib_admin("views/admin.py")
konfigurasi, masalah = akun.klien_admin()
if konfigurasi is None:
    st.html(f'<div class="errBox"><b class="h">Fitur admin belum dikonfigurasi</b>{escape(masalah)} '
            'Isi <code>service_key</code> dan <code>bucket</code> pada <code>.streamlit/secrets.toml</code> '
            '(lihat <code>secrets.example.toml</code>).</div>')
    st.stop()
klien, bucket = konfigurasi

t1, t2 = st.tabs(["Kelola Pengguna", "Perbarui Data Dashboard"])
with t1:
    tab_pengguna(klien, admin)
with t2:
    tab_data(klien, bucket)
