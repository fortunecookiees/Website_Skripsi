"""Peta folium lokasi 5 SPKU: marker warna kategori t+1 + lingkaran luas RTH."""
import math

import folium
import streamlit as st
from streamlit_folium import st_folium

from core.config import KATEGORI_ISPU, STASIUN, kategori_ispu

from .format import angka

RTH_HIJAU = "#2E7D4F"
# basemap abu-abu netral tanpa API key (CartoDB kini mewajibkan key)
TILE = "https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}"
TILE_ATTR = "Tiles &copy; Esri &mdash; Esri, DeLorme, NAVTEQ"
RADIUS_RTH_MAKS = 42  # piksel untuk RTH terluas; lainnya sebanding akar luas


def peta_stasiun(pred_t1: dict[str, float], luas_rth: dict[str, float], key: str) -> None:
    """`pred_t1` & `luas_rth` = {stasiun: nilai}. Luas lingkaran hijau sebanding luas RTH kecamatan."""
    lat = sum(s["lat"] for s in STASIUN.values()) / len(STASIUN)
    lon = sum(s["lon"] for s in STASIUN.values()) / len(STASIUN)
    m = folium.Map(location=[lat, lon], zoom_start=11, tiles=TILE, attr=TILE_ATTR,
                   control_scale=True, scrollWheelZoom=False)
    rth_maks = max(luas_rth.values())

    for nama, info in STASIUN.items():
        k = kategori_ispu(pred_t1[nama])
        rth = luas_rth[nama]
        folium.CircleMarker(
            [info["lat"], info["lon"]], radius=RADIUS_RTH_MAKS * math.sqrt(rth / rth_maks),
            stroke=False, fill=True, fill_color=RTH_HIJAU, fill_opacity=0.16,
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
                html=(f'<div style="font:600 10.5px Inter,Arial,sans-serif;color:#5A7280;text-align:center;'
                      f'text-shadow:0 0 3px #fff,0 0 3px #fff">{nama.split()[0]} · {k["nilai"]}</div>'),
            ),
        ).add_to(m)

    lats = [s["lat"] for s in STASIUN.values()]
    lons = [s["lon"] for s in STASIUN.values()]
    m.fit_bounds([[min(lats), min(lons)], [max(lats), max(lons)]], padding=(45, 45))
    st_folium(m, key=key, height=360, use_container_width=True, returned_objects=[])
    _legend()


def _legend() -> None:
    item = [f'<span><i style="background:{warna}"></i>{nama} ({rentang})</span>'
            for _, nama, rentang, warna, _, _ in KATEGORI_ISPU[:4]]
    item.append(f'<span><i class="rth" style="background:{RTH_HIJAU};opacity:.3"></i>'
                "Luas RTH kecamatan (luas lingkaran sebanding)</span>")
    st.html(f'<div class="legend">{"".join(item)}</div>')
