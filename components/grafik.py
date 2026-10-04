"""Grafik Plotly bergaya netral (garis ink, ambang ISPU putus-putus)."""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from core.config import kategori_ispu

from .format import tanggal_pendek

INK, MUTED, LINE = "#1C1C1C", "#8C8C8C", "#EFEFEF"
# ambang kategori: (nilai, warna garis, warna teks)
AMBANG = [(50, "#B9CFC0", "#3F7A57"), (100, "#D8C48A", "#9A7A18"),
          (200, "#E0B4B0", "#B23A32"), (300, "#9E9E9E", "#232323")]


def grafik_7_hari(prediksi: pd.DataFrame, key: str) -> None:
    nilai = [kategori_ispu(v)["nilai"] for v in prediksi["pm25"]]
    x = [f"t+{h}" for h in prediksi["horizon"]]
    hover = [f"<b>t+{h}</b> · {tanggal_pendek(t, tahun=True)}<br>{n} ISPU · {kategori_ispu(n)['kategori']}"
             for h, t, n in zip(prediksi["horizon"], prediksi["tanggal"], nilai)]
    y_max = max(110, max(nilai) * 1.12)

    fig = go.Figure(go.Scatter(
        x=x, y=nilai, mode="lines+markers",
        line=dict(color=INK, width=2),
        marker=dict(size=8, color=INK, line=dict(color="#FFFFFF", width=2)),
        hovertext=hover, hoverinfo="text",
    ))
    for batas, warna, teks in AMBANG:
        if batas <= y_max:
            fig.add_hline(y=batas, line=dict(color=warna, width=1, dash="dash"),
                          annotation_text=f"ISPU {batas}", annotation_position="top right",
                          annotation_font=dict(size=9, color=teks))
    fig.update_layout(
        height=190, margin=dict(l=6, r=6, t=8, b=4), showlegend=False,
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, Arial, sans-serif", size=10, color=MUTED),
        hoverlabel=dict(bgcolor="#FFFFFF", bordercolor="#DEDEDE", font=dict(color=INK, size=11)),
        xaxis=dict(showgrid=False, zeroline=False, showline=False, fixedrange=True, tickfont=dict(color=MUTED)),
        yaxis=dict(range=[0, y_max], showgrid=True, gridcolor=LINE, zeroline=False,
                   showticklabels=False, fixedrange=True),
    )
    st.plotly_chart(fig, key=key, config={"displayModeBar": False}, width="stretch")
