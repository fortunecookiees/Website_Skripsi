"""Peta folium lokasi 5 SPKU: marker warna kategori t+1, lingkaran luas RTH, dan layer titik RTH (opsional)."""
import math
from html import escape

import folium
import pandas as pd
import streamlit as st
from streamlit_folium import st_folium

from core.config import KATEGORI_ISPU, STASIUN, kategori_ispu

from .format import angka

RTH_HIJAU = "#2E7D4F"
# basemap citra satelit Esri + lapisan label nama tempat (keduanya tanpa API key)
TILE = "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
TILE_LABEL = ("https://server.arcgisonline.com/ArcGIS/rest/services/Reference/"
              "World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}")
TILE_ATTR = "Tiles &copy; Esri &mdash; Esri, Maxar, Earthstar Geographics, GIS User Community"
RADIUS_RTH_MAKS = 42  # piksel untuk RTH terluas; lainnya sebanding akar luas
NAMA_LAYER_RTH = "Titik RTH"
SUMBER_LOKASI = {"objek": "OpenStreetMap (objek terverifikasi)", "manual": "Input manual"}


def _popup_rth(r: pd.Series) -> folium.Popup:
    kel = "" if pd.isna(r.get("kelurahan")) else f"Kel. {str(r['kelurahan']).title()}, "
    html = (f'<div style="font:12px Inter,Arial,sans-serif;line-height:1.5;min-width:180px">'
            f'<b>{escape(str(r["nama_rth"]).title())}</b><br>'
            f'{escape(str(r["jenis_rth"]).title())} · {angka(float(r["luas_m2"]))} m²<br>'
            f'<span style="color:#8c8c8c">{escape(kel)}Kec. {escape(str(r["kecamatan"]).title())}<br>'
            f'Lokasi: {SUMBER_LOKASI.get(r["presisi"], r["presisi"])}</span></div>')
    return folium.Popup(html, max_width=260)


def _layer_rth(titik: pd.DataFrame) -> folium.FeatureGroup:
    """Titik RTH terverifikasi; default tersembunyi, dinyalakan lewat kontrol layer."""
    fg = folium.FeatureGroup(name=NAMA_LAYER_RTH, show=False)
    for _, r in titik.iterrows():
        folium.CircleMarker(
            [r["lat"], r["lon"]], radius=5, color="#FFFFFF", weight=1.5,
            fill=True, fill_color=RTH_HIJAU, fill_opacity=0.9,
            tooltip=str(r["nama_rth"]).title(), popup=_popup_rth(r),
        ).add_to(fg)
    return fg


def peta_stasiun(pred_t1: dict[str, float], luas_rth: dict[str, float], key: str,
                 titik_rth: pd.DataFrame | None = None) -> None:
    """`pred_t1` & `luas_rth` = {stasiun: nilai}. Luas lingkaran hijau sebanding luas RTH kecamatan.

    `titik_rth`: titik RTH terverifikasi (kolom lat, lon, nama_rth, jenis_rth, luas_m2, presisi, ...).
    """
    lat = sum(s["lat"] for s in STASIUN.values()) / len(STASIUN)
    lon = sum(s["lon"] for s in STASIUN.values()) / len(STASIUN)
    m = folium.Map(location=[lat, lon], zoom_start=11, tiles=None, control_scale=True, scrollWheelZoom=False)
    folium.TileLayer(TILE, attr=TILE_ATTR, name="Peta dasar", control=False).add_to(m)
    folium.TileLayer(TILE_LABEL, attr=TILE_ATTR, name="Label", overlay=True, control=False,
                     opacity=0.85).add_to(m)
    rth_maks = max(luas_rth.values())

    for nama, info in STASIUN.items():
        k = kategori_ispu(pred_t1[nama])
        rth = luas_rth[nama]
        folium.CircleMarker(
            [info["lat"], info["lon"]], radius=RADIUS_RTH_MAKS * math.sqrt(rth / rth_maks),
            color="#FFFFFF", weight=1, opacity=0.7,  # garis tepi agar terlihat di atas citra satelit
            fill=True, fill_color=RTH_HIJAU, fill_opacity=0.35,
        ).add_to(m)
        tooltip = (f"<b>{nama}</b><br>Kec. {info['kecamatan']}<br>"
                   f"Prediksi t+1: <b>{k['nilai']} ISPU</b> · {k['kategori']}<br>"
                   f"Luas RTH: {angka(rth, 3)} km²")
        folium.CircleMarker(
            [info["lat"], info["lon"]], radius=9.5, color="#FFFFFF", weight=2.5,
            fill=True, fill_color=k["warna"], fill_opacity=1, tooltip=tooltip,
        ).add_to(m)
        folium.Marker(
            [info["lat"], info["lon"]],
            icon=folium.DivIcon(
                icon_size=(110, 16), icon_anchor=(55, -14),
                html=(f'<div style="font:600 10.5px Inter,Arial,sans-serif;color:#FFFFFF;text-align:center;'
                      f'text-shadow:0 0 3px #000,0 0 3px #000,0 0 2px #000">{nama.split()[0]} · {k["nilai"]}</div>'),
            ),
        ).add_to(m)

    ada_titik = titik_rth is not None and not titik_rth.empty
    if ada_titik:
        _layer_rth(titik_rth).add_to(m)
        folium.LayerControl(position="topright", collapsed=False).add_to(m)

    lats = [s["lat"] for s in STASIUN.values()]
    lons = [s["lon"] for s in STASIUN.values()]
    m.fit_bounds([[min(lats), min(lons)], [max(lats), max(lons)]], padding=(45, 45))
    st_folium(m, key=key, height=360, use_container_width=True, returned_objects=[])
    _legend(len(titik_rth) if ada_titik else 0)


def _legend(n_titik: int) -> None:
    item = [f'<span><i style="background:{warna}"></i>{nama} ({rentang})</span>'
            for _, nama, rentang, warna, _, _ in KATEGORI_ISPU[:4]]
    item.append(f'<span><i class="rth" style="background:{RTH_HIJAU};opacity:.5"></i>'
                "Luas RTH kecamatan (ukuran relatif antarstasiun)</span>")
    catatan = ""
    if n_titik:
        item.append(f'<span><i class="rth" style="background:{RTH_HIJAU};width:7px;height:7px"></i>'
                    f'Titik RTH ({n_titik} lokasi, aktifkan lewat kotak "{NAMA_LAYER_RTH}" di kanan atas peta)</span>')
        catatan = ('<div class="note">Hanya RTH yang lokasinya terverifikasi sebagai taman/hutan/makam '
                   'yang ditampilkan.</div>')
    st.html(f'<div class="legend">{"".join(item)}</div>{catatan}')
