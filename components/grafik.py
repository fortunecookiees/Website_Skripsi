"""Grafik Plotly bergaya netral (garis ink, ambang ISPU putus-putus)."""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from core.config import kategori_ispu

from .bahasa import kategori, t
from .format import BULAN, tanggal_pendek

INK, MUTED, LINE = "#347653", "#8C9B96", "#EDF1EF"
# ambang kategori: (nilai, warna garis, warna teks)
AMBANG = [(50, "#B9CFC0", "#3F7A57"), (100, "#D8C48A", "#9A7A18"),
          (200, "#E0B4B0", "#B23A32"), (300, "#9E9E9E", "#232323")]


def grafik_7_hari(prediksi: pd.DataFrame, key: str) -> None:
    nilai = [kategori_ispu(v)["nilai"] for v in prediksi["pm25"]]
    x = [f"t+{h}" for h in prediksi["horizon"]]
    hover = [f"<b>t+{h}</b> · {tanggal_pendek(tg, tahun=True)}<br>{n} ISPU · {kategori(kategori_ispu(n)['kategori'])}"
             for h, tg, n in zip(prediksi["horizon"], prediksi["tanggal"], nilai)]
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
        hoverlabel=dict(bgcolor="#FFFFFF", bordercolor="#DFE6E4", font=dict(color=INK, size=11)),
        xaxis=dict(showgrid=False, zeroline=False, showline=False, fixedrange=True, tickfont=dict(color=MUTED)),
        yaxis=dict(range=[0, y_max], showgrid=True, gridcolor=LINE, zeroline=False,
                   showticklabels=False, fixedrange=True),
    )
    st.plotly_chart(fig, key=key, config={"displayModeBar": False}, width="stretch")


def grafik_sekitar_acuan(aktual: pd.DataFrame, acuan: pd.Timestamp, prediksi: pd.DataFrame, key: str,
                         tinggi: int = 230) -> None:
    """Garis PM2.5 aktual (titik berongga = data diisi) + prediksi t+1..t+7 putus-putus + penanda tanggal acuan.

    `aktual`: kolom tanggal, pm25, pm25_asli. `prediksi`: kolom tanggal, pm25.
    """
    nilai_akt = [kategori_ispu(v)["nilai"] for v in aktual["pm25"]]
    nilai_pred = [kategori_ispu(v)["nilai"] for v in prediksi["pm25"]]
    asli = aktual["pm25_asli"].tolist()
    akt, pred, diisi = t("Aktual", "Actual"), t("Prediksi", "Predicted"), t(" · data diisi", " · filled data")
    hover_akt = [f"<b>{tanggal_pendek(tg, tahun=True)}</b><br>{akt} {n} ISPU{'' if a else diisi}"
                 for tg, n, a in zip(aktual["tanggal"], nilai_akt, asli)]
    hover_pred = [f"<b>{tanggal_pendek(tg, tahun=True)}</b> (t+{i + 1})<br>{pred} {n} ISPU"
                  for i, (tg, n) in enumerate(zip(prediksi["tanggal"], nilai_pred))]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=aktual["tanggal"], y=nilai_akt, mode="lines+markers", line=dict(color=INK, width=2),
        marker=dict(size=7, color=[INK if a else "#FFFFFF" for a in asli], line=dict(color=INK, width=1.6)),
        hovertext=hover_akt, hoverinfo="text"))
    fig.add_trace(go.Scatter(
        x=prediksi["tanggal"], y=nilai_pred, mode="lines+markers",
        line=dict(color=MUTED, width=2, dash="dash"),
        marker=dict(size=8, color="#FFFFFF", line=dict(color=MUTED, width=1.6)),
        hovertext=hover_pred, hoverinfo="text"))
    fig.add_vline(x=acuan, line=dict(color="#B7C6CE", width=1, dash="dash"))
    fig.add_annotation(x=acuan, y=1, yref="paper", text=t("tanggal acuan", "reference date"), showarrow=False,
                       xanchor="left", xshift=4, font=dict(size=9, color="#8DA0AC"))
    semua = nilai_akt + nilai_pred
    fig.update_layout(
        height=tinggi, margin=dict(l=8, r=8, t=10, b=6), showlegend=False,
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, Arial, sans-serif", size=10, color=MUTED),
        hoverlabel=dict(bgcolor="#FFFFFF", bordercolor="#DFE6E4", font=dict(color=INK, size=11)),
        xaxis=dict(showgrid=False, zeroline=False, fixedrange=True,
                   tickvals=list(aktual["tanggal"])[::2], ticktext=[tanggal_pendek(tg) for tg in list(aktual["tanggal"])[::2]]),
        yaxis=dict(range=[max(0, min(semua) - 10), max(semua) + 10], showgrid=True, gridcolor=LINE,
                   zeroline=False, fixedrange=True, nticks=5),
    )
    st.plotly_chart(fig, key=key, config={"displayModeBar": False}, width="stretch")


# stasiun dibedakan dengan nada abu-abu + pola garis (warna hanya untuk kategori ISPU)
GAYA_STASIUN = [("#347653", "solid"), ("#648BA6", "solid"), ("#5A9676", "dot"),
                ("#9DB8CC", "solid"), ("#546660", "dash")]


def grafik_historis(data: pd.DataFrame, stasiun: list[str], key: str, tinggi: int = 320) -> None:
    """Tren PM2.5 beberapa stasiun. `data`: kolom tanggal, stasiun, pm25, n_hari (hasil core.historis.agregasi)."""
    from core.config import STASIUN
    fig = go.Figure()
    for i, s in enumerate([s for s in STASIUN if s in stasiun]):
        d = data[data["stasiun"] == s]
        warna, pola = GAYA_STASIUN[i % len(GAYA_STASIUN)]
        hover = [f"<b>{s.split()[0]}</b> · {tanggal_pendek(tg, tahun=True)}<br>{v:.0f} ISPU · "
                 f"{kategori(kategori_ispu(v)['kategori'])}"
                 + (t(f"<br>rata-rata {n} hari", f"<br>{n}-day average") if n > 1 else "")
                 for tg, v, n in zip(d["tanggal"], d["pm25"], d["n_hari"])]
        fig.add_trace(go.Scatter(x=d["tanggal"], y=d["pm25"], name=s.split()[0] + " " + " ".join(s.split()[1:]),
                                 mode="lines+markers" if len(d) <= 60 else "lines",
                                 line=dict(color=warna, width=1.8, dash=pola), marker=dict(size=5, color=warna),
                                 hovertext=hover, hoverinfo="text"))
    y_max = max(110, float(data["pm25"].max()) * 1.1) if not data.empty else 110
    for batas, warna, teks in AMBANG:
        if batas <= y_max:
            fig.add_hline(y=batas, line=dict(color=warna, width=1, dash="dash"),
                          annotation_text=f"ISPU {batas}", annotation_position="top right",
                          annotation_font=dict(size=9, color=teks), annotation_bgcolor="rgba(255,255,255,.85)")
    # label sumbu-x berbahasa Indonesia (plotly memakai nama bulan Inggris)
    tgl = pd.Series(sorted(data["tanggal"].unique()))
    if len(tgl):
        idx = sorted({round(i * (len(tgl) - 1) / 5) for i in range(6)})
        rentang_hari = (tgl.iloc[-1] - tgl.iloc[0]).days
        teks_x = [(f"{BULAN[tg.month - 1][:3]} {tg.year}" if rentang_hari > 200 else tanggal_pendek(tg))
                  for tg in tgl.iloc[idx]]
        fig.update_xaxes(tickvals=list(tgl.iloc[idx]), ticktext=teks_x)
    fig.update_layout(
        height=tinggi, margin=dict(l=8, r=8, t=10, b=6),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, Arial, sans-serif", size=10, color=MUTED),
        hoverlabel=dict(bgcolor="#FFFFFF", bordercolor="#DFE6E4", font=dict(color=INK, size=11)),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0, font=dict(size=10.5, color="#546660")),
        xaxis=dict(showgrid=False, zeroline=False, fixedrange=False),
        yaxis=dict(range=[0, y_max], showgrid=True, gridcolor=LINE, zeroline=False, fixedrange=True, nticks=6),
        hovermode="closest",
    )
    st.plotly_chart(fig, key=key, config={"displayModeBar": False}, width="stretch")


def grafik_distribusi(tab: pd.DataFrame, key: str) -> None:
    """Batang bertumpuk persentase hari per kategori ISPU per stasiun (warna kategori ISPU)."""
    from core.config import KATEGORI_ISPU
    fig = go.Figure()
    label = [s.split()[0] for s in tab.index]
    for _, nama, rentang, warna, *_ in KATEGORI_ISPU:
        if nama not in tab.columns or not tab[nama].any():
            continue
        tampil = kategori(nama)
        fig.add_trace(go.Bar(y=label, x=tab[nama], name=tampil, orientation="h", marker=dict(color=warna),
                             hovertemplate=f"<b>%{{y}}</b> · {tampil} ({rentang})<br>%{{x:.1f}}% "
                                           f"{t('hari', 'of days')}<extra></extra>",
                             text=[f"{v:.0f}%" if v >= 8 else "" for v in tab[nama]], textposition="inside",
                             insidetextfont=dict(color="#FFFFFF", size=10)))
    fig.update_layout(
        barmode="stack", height=80 + 38 * len(tab), margin=dict(l=8, r=8, t=34, b=6),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", bargap=0.35,
        font=dict(family="Inter, Arial, sans-serif", size=10.5, color="#546660"),
        hoverlabel=dict(bgcolor="#FFFFFF", bordercolor="#DFE6E4", font=dict(color=INK, size=11)),
        legend=dict(orientation="h", yanchor="bottom", y=1.0, x=0, font=dict(size=10), traceorder="normal"),
        xaxis=dict(range=[0, 100], showgrid=True, gridcolor=LINE, ticksuffix="%", fixedrange=True, zeroline=False),
        yaxis=dict(autorange="reversed", fixedrange=True),
    )
    st.plotly_chart(fig, key=key, config={"displayModeBar": False}, width="stretch")


def grafik_optimasi(ev: dict, key: str) -> None:
    """Garis RMSE uji per horizon: hyperparameter bawaan vs Random Search vs PSO."""
    from core.config import HORIZONS
    x = [f"t+{h}" for h in HORIZONS]
    fig = go.Figure()
    for kunci, nama, warna, gaya, tebal in [("default", t("Hyperparameter Bawaan", "Default Hyperparameters"),
                                             "#8C9B96", "dot", 1.8),
                                            ("random_search", "Random Search", "#648BA6", "solid", 2),
                                            ("pso", "PSO", INK, "solid", 2.6)]:
        y = [ev[kunci][str(h)]["RMSE"] for h in HORIZONS]
        fig.add_trace(go.Scatter(
            x=x, y=y, name=nama, mode="lines+markers",
            line=dict(color=warna, width=tebal, dash=gaya),
            marker=dict(size=7, color=warna, line=dict(color="#FFFFFF", width=1.5)),
            hovertemplate=f"<b>%{{x}}</b> · {nama}<br>RMSE %{{y:.3f}}<extra></extra>",
        ))
    fig.update_layout(
        height=230, margin=dict(l=6, r=6, t=34, b=4), hovermode="x unified",
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, Arial, sans-serif", size=10.5, color="#546660"),
        hoverlabel=dict(bgcolor="#FFFFFF", bordercolor="#DFE6E4", font=dict(color=INK, size=11)),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0, font=dict(size=10.5)),
        xaxis=dict(showgrid=False, zeroline=False, fixedrange=True),
        yaxis=dict(title=dict(text="RMSE", font=dict(size=10)), showgrid=True, gridcolor=LINE,
                   zeroline=False, fixedrange=True),
    )
    st.plotly_chart(fig, key=key, config={"displayModeBar": False}, width="stretch")
