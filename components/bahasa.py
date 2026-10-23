"""Pilihan bahasa antarmuka (Indonesia / English).

Teks ditulis berpasangan di tempat pemakaiannya: t("Teks Indonesia", "English text").
Bahasa disimpan di session_state dan di URL (?lang=en) agar tetap terpilih setelah halaman dimuat ulang.
Hanya lapisan tampilan; core/, model, dan data tidak terpengaruh.
"""
import streamlit as st

from core.teks import atur_inggris

KUNCI = "bahasa"
ID, EN = "id", "en"
PILIHAN = {ID: "ID", EN: "EN"}

# nama kategori ISPU (core/config.py tetap memakai nama Indonesia sebagai kunci)
KATEGORI_EN = {"Baik": "Good", "Sedang": "Moderate", "Tidak Sehat": "Unhealthy",
               "Sangat Tidak Sehat": "Very Unhealthy", "Berbahaya": "Hazardous"}


# saran PermenLHK 14/2020 untuk PM2.5: (kelompok sensitif, setiap orang)
SARAN_EN = {
    "Baik": (None, "Very good for outdoor activities"),
    "Sedang": ("Reduce prolonged or heavy physical activity", "Outdoor activities are still fine"),
    "Tidak Sehat": ("Outdoor activities are allowed, but take breaks more often",
                    "Reduce prolonged physical activity outdoors"),
    "Sangat Tidak Sehat": ("Avoid all outdoor activities. Stay active indoors",
                           "Avoid prolonged physical activity outdoors"),
    "Berbahaya": ("Stay indoors and keep activity light", "Avoid all outdoor activities"),
}


def label_fitur(fitur: str) -> tuple[str, str]:
    """(nama, satuan) fitur dalam bahasa aktif."""
    from core.config import LABEL_FITUR, LABEL_FITUR_EN
    return LABEL_FITUR_EN.get(fitur, LABEL_FITUR[fitur]) if inggris() else LABEL_FITUR[fitur]


def saran(nama_kategori: str) -> tuple[str | None, str]:
    from core.config import SARAN_ISPU_PM25
    return SARAN_EN[nama_kategori] if inggris() else SARAN_ISPU_PM25[nama_kategori]


def bahasa() -> str:
    nilai = st.session_state.get(KUNCI)
    if nilai not in PILIHAN:
        # pertama kali dari URL; atau segmented control dikosongkan (klik ulang) -> kembali ke Indonesia.
        # Aman karena dipanggil app.py sebelum widget pemilih dibuat pada run ini.
        nilai = EN if KUNCI not in st.session_state and st.query_params.get("lang") == EN else ID
        st.session_state[KUNCI] = nilai
    atur_inggris(nilai == EN)  # pesan dari core/ & auth/ ikut bahasa ini
    return nilai


def inggris() -> bool:
    return bahasa() == EN


def t(id_: str, en: str) -> str:
    """Teks sesuai bahasa aktif."""
    return en if inggris() else id_


def kategori(nama: str) -> str:
    """Nama kategori ISPU dalam bahasa aktif."""
    return KATEGORI_EN.get(nama, nama) if inggris() else nama


def _simpan_url() -> None:
    if bahasa() == EN:
        st.query_params["lang"] = EN
    elif "lang" in st.query_params:
        del st.query_params["lang"]


def pemilih() -> None:
    """Tombol ID | EN (dipasang di sidebar)."""
    bahasa()
    with st.container(key="pemilih_bahasa"):
        st.segmented_control("Bahasa / Language", list(PILIHAN), format_func=PILIHAN.get, key=KUNCI,
                             label_visibility="collapsed", width="stretch")
    _simpan_url()
