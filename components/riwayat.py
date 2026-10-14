"""Riwayat unggahan SELAMA SESI (st.session_state). Tidak dikirim ke server dan hilang saat keluar/refresh."""
from datetime import datetime

import streamlit as st

from core.config import kategori_ispu

KUNCI = "riwayat_unggah"


def catat(file_id: str, nama_file: str, ukuran: int, hasil) -> None:
    """Simpan ringkasan satu unggahan yang berhasil diproses (sekali per file)."""
    daftar = st.session_state.setdefault(KUNCI, [])
    if any(r["file_id"] == file_id for r in daftar):
        return
    stasiun = []
    for nama, baris in hasil.kondisi.items():
        p = hasil.prediksi[hasil.prediksi["stasiun"] == nama]["pm25"]
        stasiun.append({"stasiun": nama, "tanggal_terakhir": baris["tanggal"], "hari": hasil.hari.get(nama, 0),
                        "t1": kategori_ispu(p.iloc[0])["nilai"], "t7": kategori_ispu(p.iloc[-1])["nilai"]})
    daftar.insert(0, {"file_id": file_id, "waktu": datetime.now(), "nama_file": nama_file, "ukuran": ukuran,
                      "stasiun": stasiun, "n_validasi": int(hasil.validasi["tanggal"].nunique())
                      if len(hasil.validasi) else 0})


def daftar() -> list[dict]:
    return st.session_state.get(KUNCI, [])


def hapus() -> None:
    st.session_state.pop(KUNCI, None)
