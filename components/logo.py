"""Identitas aplikasi: nama NafasKota dan logo (garis hembusan napas + partikel PM2.5), monokrom."""
import base64

NAMA = "NafasKota"
TAGLINE = "Prediksi PM2.5 DKI Jakarta"
TAGLINE_EN = "PM2.5 Forecast for DKI Jakarta"
JUDUL_SKRIPSI = ("Prediksi PM2.5 dengan Integrasi Kepadatan Penduduk dan Ruang Terbuka Hijau di DKI "
                 "Jakarta Menggunakan Extreme Gradient Boosting dengan Optimasi Particle Swarm Optimization")
JUDUL_SKRIPSI_EN = ("PM2.5 Prediction Integrating Population Density and Green Open Space in DKI Jakarta "
                    "Using Extreme Gradient Boosting with Particle Swarm Optimization")


def tagline() -> str:
    from .bahasa import t
    return t(TAGLINE, TAGLINE_EN)


def judul_skripsi() -> str:
    from .bahasa import t
    return t(JUDUL_SKRIPSI, JUDUL_SKRIPSI_EN)

# viewBox 64x64: dua garis hembusan dengan ujung melingkar, satu garis pendek, dan tiga partikel
_ISI = (
    '<path d="M12 24 H34 a7 7 0 1 0 -7 -7" />'
    '<path d="M12 34 H44 a7 7 0 1 1 -7 7" />'
    '<path d="M12 44 H26" />'
)
_PARTIKEL = [(50, 15, 3.6), (56, 25, 2.4), (25, 54, 2.2)]


def svg_mentah(ukuran: int = 64, latar: str = "#FFFFFF", garis: str = "#347653") -> str:
    titik = "".join(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{garis}" />' for x, y, r in _PARTIKEL)
    return (f'<svg width="{ukuran}" height="{ukuran}" viewBox="0 0 64 64" xmlns="http://www.w3.org/2000/svg">'
            f'<rect width="64" height="64" rx="15" fill="{latar}" />'
            f'<g fill="none" stroke="{garis}" stroke-width="5" stroke-linecap="round">{_ISI}</g>{titik}</svg>')


def hiasan_uri(garis: str = "#347653") -> str:
    """Motif hembusan logo tanpa latar (data URI) untuk hiasan latar header/kartu."""
    titik = "".join(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{garis}" />' for x, y, r in _PARTIKEL)
    svg = (f'<svg viewBox="0 0 64 64" xmlns="http://www.w3.org/2000/svg">'
           f'<g fill="none" stroke="{garis}" stroke-width="3" stroke-linecap="round">{_ISI}</g>{titik}</svg>')
    return "data:image/svg+xml;base64," + base64.b64encode(svg.encode("utf-8")).decode("ascii")


def logo_svg(ukuran: int = 30, latar: str = "#FFFFFF", garis: str = "#347653", kelas: str = "logo") -> str:
    """Tag <img> berisi SVG (data URI); st.html membuang tag <svg> mentah tetapi mengizinkan gambar."""
    data = base64.b64encode(svg_mentah(ukuran, latar, garis).encode("utf-8")).decode("ascii")
    return (f'<img class="{kelas}" src="data:image/svg+xml;base64,{data}" width="{ukuran}" height="{ukuran}" '
            f'alt="Logo {NAMA}">')
