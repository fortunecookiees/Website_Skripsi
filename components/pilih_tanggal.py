"""Stepper tanggal acuan (tombol ‹ › + daftar tanggal), dipakai halaman Evaluation & tab Validasi."""
import pandas as pd
import streamlit as st

from .format import tanggal_panjang


def _geser(kunci: str, daftar: list, langkah: int) -> None:
    i = daftar.index(st.session_state[kunci])
    st.session_state[kunci] = daftar[min(max(i + langkah, 0), len(daftar) - 1)]


def pilih_tanggal(daftar: list[pd.Timestamp], prefix: str):
    """Widget ber-key `{prefix}_tanggal`, `{prefix}_geser_mundur/maju`. Mengembalikan (tanggal, kolom keterangan)."""
    kunci = f"{prefix}_tanggal"
    if st.session_state.get(kunci) not in daftar:
        st.session_state[kunci] = daftar[-1]
    i = daftar.index(st.session_state[kunci])
    c1, c2, c3, c4 = st.columns([0.35, 2.2, 0.35, 5], vertical_alignment="center", gap="small")
    c1.button("‹", key=f"{prefix}_geser_mundur", on_click=_geser, args=(kunci, daftar, -1), disabled=i == 0,
              help="Tanggal sebelumnya")
    c2.selectbox("Tanggal acuan", daftar, key=kunci, format_func=tanggal_panjang,
                 label_visibility="collapsed")
    c3.button("›", key=f"{prefix}_geser_maju", on_click=_geser, args=(kunci, daftar, 1),
              disabled=i == len(daftar) - 1, help="Tanggal berikutnya")
    return st.session_state[kunci], c4
