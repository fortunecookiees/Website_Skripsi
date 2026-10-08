"""Geocoding titik RTH per kecamatan -> data/rth_koordinat.csv (dijalankan SEKALI, di luar aplikasi).

Pemakaian (dari root project):
    .venv\\Scripts\\python scripts\\geocode_rth.py

- Nominatim (OpenStreetMap) via geopy, jeda >= 1 detik per permintaan sesuai kebijakan Nominatim.
- Semua jawaban di-cache di data/.cache_geocode_rth.json, jadi script bisa dihentikan dan dilanjutkan.
- Pencarian bertingkat: alamat lengkap -> nama RTH + kelurahan + kecamatan -> pusat kelurahan.
- Presisi: "objek" (taman/hutan/makam OSM dengan nama yang cocok), "jalan" (ruas jalan),
  "kelurahan" (batas kelurahan), "gagal". Kantor, stasiun, halte, toko, dsb. ditolak.
- Koordinat manual (data/rth_manual.csv, mis. dari Google Maps) menimpa hasil di atas dengan presisi
  "manual" setelah lolos validasi polygon. Setelah mengisi file itu, jalankan ulang script ini.
- Validasi berlapis: titik harus di dalam polygon DKI Jakarta DAN polygon kecamatannya.
- File sumber (data/daftar_alamat_rth_per_kecamatan.xlsx) tidak diubah; koreksi luas dilakukan di sini.

geopy hanya dibutuhkan script ini (tidak masuk requirements.txt aplikasi).
"""
import json
import re
import sys
from pathlib import Path

import pandas as pd
from geopy.extra.rate_limiter import RateLimiter
from geopy.geocoders import Nominatim

ROOT = Path(__file__).resolve().parent.parent
SUMBER = ROOT / "data" / "daftar_alamat_rth_per_kecamatan.xlsx"
KELUARAN = ROOT / "data" / "rth_koordinat.csv"
CACHE = ROOT / "data" / ".cache_geocode_rth.json"
MANUAL = ROOT / "data" / "rth_manual.csv"  # koordinat dari Google Maps; baris dengan lat/lon kosong diabaikan

USER_AGENT = "pm25-jakarta-skripsi/1.0 (geocoding RTH sekali jalan; skripsi Teknik Informatika Untar)"
JEDA_DETIK = 1.1
VIEWBOX = [(-6.10, 106.65), (-6.40, 107.00)]  # arahan pencarian ke Jakarta (bukan pembatas)

KECAMATAN = {  # sheet -> (stasiun, kota)
    "MENTENG": ("DKI1 Bundaran HI", "Jakarta Pusat"),
    "KELAPA GADING": ("DKI2 Kelapa Gading", "Jakarta Utara"),
    "JAGAKARSA": ("DKI3 Jagakarsa", "Jakarta Selatan"),
    "CIPAYUNG": ("DKI4 Lubang Buaya", "Jakarta Timur"),
    "KEBON JERUK": ("DKI5 Kebon Jeruk", "Jakarta Barat"),
}

# Koreksi data sumber: (sheet, no, luas lama) -> luas benar. Dicocokkan 3 kunci agar tidak salah baris.
KOREKSI_LUAS = {("JAGAKARSA", 1, 1731952.0): 17319.52}  # Fly Over Tanjung Barat (Bawah)

# OSM Indonesia: provinsi admin_level 4, kota 5, kecamatan 6, kelurahan 7.
LEVEL_KECAMATAN, LEVEL_KELURAHAN = 6, 7


# ---------------------------------------------------------------------
# Cache & pemanggilan Nominatim
# ---------------------------------------------------------------------
class Geocoder:
    def __init__(self):
        self.cache = json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {}
        nominatim = Nominatim(user_agent=USER_AGENT, timeout=30)
        self._cari = RateLimiter(nominatim.geocode, min_delay_seconds=JEDA_DETIK, max_retries=3,
                                 error_wait_seconds=10, swallow_exceptions=False)
        self.panggilan = 0

    def _simpan(self):
        tmp = CACHE.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.cache, ensure_ascii=False), encoding="utf-8")
        tmp.replace(CACHE)

    def cari(self, kueri: str, polygon: bool = False, limit: int = 3) -> list[dict]:
        kunci = f"{'poly' if polygon else 'pt'}|{kueri}"
        if kunci not in self.cache:
            hasil = self._cari(kueri, exactly_one=False, limit=limit, country_codes="id", viewbox=VIEWBOX,
                               geometry="geojson" if polygon else None, addressdetails=False, extratags=True)
            self.panggilan += 1
            self.cache[kunci] = [h.raw for h in (hasil or [])]
            self._simpan()
        return self.cache[kunci]


# ---------------------------------------------------------------------
# Geometri: titik di dalam (Multi)Polygon GeoJSON, ray casting dengan dukungan lubang
# ---------------------------------------------------------------------
def _dalam_cincin(lon: float, lat: float, cincin: list) -> bool:
    dalam, n = False, len(cincin)
    for i in range(n):
        x1, y1 = cincin[i][0], cincin[i][1]
        x2, y2 = cincin[(i + 1) % n][0], cincin[(i + 1) % n][1]
        if (y1 > lat) != (y2 > lat) and lon < (x2 - x1) * (lat - y1) / (y2 - y1) + x1:
            dalam = not dalam
    return dalam


def dalam_polygon(lat: float, lon: float, geojson: dict) -> bool:
    polys = [geojson["coordinates"]] if geojson["type"] == "Polygon" else geojson["coordinates"]
    for poly in polys:
        if _dalam_cincin(lon, lat, poly[0]) and not any(_dalam_cincin(lon, lat, lubang) for lubang in poly[1:]):
            return True
    return False


def admin_level(h: dict) -> int | None:
    lv = (h.get("extratags") or {}).get("admin_level")
    return int(lv) if h.get("class") == "boundary" and lv and str(lv).isdigit() else None


def ambil_polygon(g: Geocoder, kueri: str, level: int | None = None) -> dict:
    """Polygon batas administratif pertama (opsional: dengan admin_level tertentu)."""
    for h in g.cari(kueri, polygon=True, limit=10):
        geo = h.get("geojson") or {}
        if h.get("class") == "boundary" and geo.get("type") in ("Polygon", "MultiPolygon")                 and (level is None or admin_level(h) == level):
            return geo
    sys.exit(f"Polygon tidak ditemukan untuk '{kueri}'. Periksa koneksi atau ubah kueri.")


# ---------------------------------------------------------------------
# Pembersihan teks alamat/nama sebelum dicari
# ---------------------------------------------------------------------
_GANTI = [
    (r"\bJH\.\s*", "Jalur Hijau "), (r"\bJL\.\s*", "Jalan "), (r"\bJLN?\b\.?\s*", "Jalan "),
    # kata "Kelurahan/Kecamatan" dibuang: membuat Nominatim condong ke puskesmas/kantor kecamatan
    (r"\bKEL(URAHAN)?\.?\s+", ""), (r"\bKEC(AMATAN)?\.?\s+", ""), (r"\bKOTA\s+(?=JAKARTA)", ""),
    (r"\bTPU\.\s*", "TPU "),
]
_BUANG = [
    r"\bRT\.?\s*\d+\s*/?\s*RW\.?\s*\d+", r"\bRT\.?\s*\d+", r"\bRW\.?\s*\d+",       # RT/RW
    r"\bS\.?\s*/?\s*D\.?\b.*?(?=,|$)",                                            # "S/D ..." sampai koma
    r"\bSISI\s+(UTARA|SELATAN|TIMUR|BARAT)\b", r"\(\s*BAWAH\s*\)", r"[()]",
    r"\bDAERAH KHUSUS IBUKOTA JAKARTA\b", r"\b\d{5}\b",                            # provinsi panjang & kode pos
]


def bersihkan(teks) -> str:
    if pd.isna(teks):
        return ""
    s = str(teks)
    for pola, ganti in _GANTI:
        s = re.sub(pola, ganti, s, flags=re.I)
    for pola in _BUANG:
        s = re.sub(pola, " ", s, flags=re.I)
    s = re.sub(r"\s+,", ",", s)
    s = re.sub(r"(,\s*)+,", ",", s)
    s = re.sub(r"\s+", " ", s).strip(" ,.")
    return s


# ---------------------------------------------------------------------
# Proses per baris
# ---------------------------------------------------------------------
def muat_sumber() -> pd.DataFrame:
    lembar = pd.read_excel(SUMBER, sheet_name=list(KECAMATAN))
    df = pd.concat([d.assign(kecamatan=nama) for nama, d in lembar.items()], ignore_index=True)
    df["luas_m2"] = df["luas_m2"].astype(float)
    for (sheet, no, lama), baru in KOREKSI_LUAS.items():
        m = (df["kecamatan"] == sheet) & (df["no"] == no) & (df["luas_m2"] == lama)
        if m.sum() != 1:
            sys.exit(f"Koreksi {sheet} no.{no} tidak menemukan tepat satu baris (ditemukan {m.sum()}).")
        print(f"Koreksi luas: {sheet} no.{no} {df.loc[m, 'nama_rth'].iloc[0]!r}: {lama:,.0f} -> {baru:,.2f} m2")
        df.loc[m, "luas_m2"] = baru
    return df


def kandidat_kueri(r: pd.Series, kota: str) -> list[tuple[str, str]]:
    """[(kueri, tingkat)] berurutan: alamat -> nama+kelurahan -> pusat kelurahan."""
    kec = r["kecamatan"].title()
    kel = "" if pd.isna(r["kelurahan"]) else str(r["kelurahan"]).title()
    alamat, nama = bersihkan(r["alamat"]), bersihkan(r["nama_rth"])
    out = []
    if alamat:
        out.append((alamat if "jakarta" in alamat.lower() else f"{alamat}, {kota}", "alamat"))
    if nama:
        out.append((", ".join(x for x in [nama, kel, kec, kota] if x), "alamat"))
    if kel:
        out.append((f"{kel}, {kec}, {kota}", "kelurahan"))
    return list(dict.fromkeys(out))  # buang kueri ganda, urutan dipertahankan


# Objek OSM yang memang berupa RTH (taman/hutan/makam/area hijau) -> presisi "objek"
OBJEK_RTH = {
    "leisure": {"park", "garden", "nature_reserve", "recreation_ground", "playground", "common"},
    "landuse": {"cemetery", "recreation_ground", "forest", "grass", "village_green", "meadow"},
    "natural": {"wood", "scrub", "grassland"},
    "amenity": {"grave_yard"},
}
# Jenis RTH di data -> objek OSM yang sesuai (TAMAN tidak boleh cocok ke makam, TPU harus makam, dst.)
_TAMAN = {("leisure", t) for t in ("park", "garden", "recreation_ground", "playground", "common")}     | {("landuse", t) for t in ("recreation_ground", "grass", "village_green")}
_MAKAM = {("landuse", "cemetery"), ("amenity", "grave_yard")}
_HUTAN = {("natural", t) for t in ("wood", "scrub", "grassland")} | {("landuse", "forest"), ("leisure", "park"),
                                                                       ("leisure", "nature_reserve")}
SESUAI_JENIS = {"TAMAN": _TAMAN, "TPU": _MAKAM, "HUTAN": _HUTAN, "KEBUN BIBIT": _TAMAN | _HUTAN,
                "JALUR HIJAU": _TAMAN | _HUTAN}
# Ruas jalan -> presisi "jalan" (lokasi hanya sepanjang jalan, tidak ditampilkan di peta)
JENIS_JALAN = {"motorway", "trunk", "primary", "secondary", "tertiary", "unclassified", "residential",
               "living_street", "service", "pedestrian", "footway", "path", "track", "road"}
# Kata umum yang tidak membedakan satu RTH dengan RTH lain (tidak dipakai untuk cek nama)
KATA_UMUM = {"TAMAN", "HUTAN", "KOTA", "TPU", "RTH", "RPTRA", "JALUR", "HIJAU", "JALAN", "JL", "JLN", "RT", "RW",
             "KEBUN", "BIBIT", "MAKAM", "PEMAKAMAN", "UMUM", "RAYA", "DAN", "DI", "KEL", "KEC", "KELURAHAN",
             "KECAMATAN", "JAKARTA", "PUSAT", "UTARA", "SELATAN", "TIMUR", "BARAT", "NO", "GG", "GANG", "JH"}


def _kata_khas(teks) -> set[str]:
    kata = re.findall(r"[A-Z]+", str(teks).upper())
    return {k for k in kata if len(k) >= 3 and k not in KATA_UMUM}


def jenis_hasil(h: dict, nama_rth: str, jenis_rth: str) -> str | None:
    """'objek' | 'jalan' | None (ditolak: kantor, stasiun, halte, toko, RTH lain/jenis berbeda, dll.)."""
    kelas, tipe = h.get("class"), h.get("type")
    if tipe in OBJEK_RTH.get(kelas, set()):
        # objek yang sama: jenisnya sesuai DAN nama OSM memuat minimal satu kata khas dari nama RTH
        sesuai = (kelas, tipe) in SESUAI_JENIS.get(str(jenis_rth).upper(), set())
        return "objek" if sesuai and _kata_khas(h.get("name")) & _kata_khas(nama_rth) else None
    if kelas == "highway" and tipe in JENIS_JALAN:
        return "jalan"
    return None


URUTAN_PRESISI = ["objek", "jalan", "kelurahan"]  # objek didahulukan meski ditemukan di tingkat kueri lebih akhir


def geocode_baris(g: Geocoder, r: pd.Series, kota: str, poly_jkt: dict, poly_kec: dict) -> dict:
    """Kumpulkan kandidat valid dari semua tingkat kueri, lalu pilih presisi terbaik (objek > jalan > kelurahan)."""
    terbaik: dict[str, dict] = {}
    for kueri, tingkat in kandidat_kueri(r, kota):
        if tingkat == "kelurahan" and ("objek" in terbaik or "jalan" in terbaik):
            break  # pusat kelurahan tidak diperlukan
        for h in g.cari(kueri):
            level = admin_level(h)
            if tingkat == "kelurahan":
                if level != LEVEL_KELURAHAN:  # tingkat 3 hanya menerima batas kelurahan
                    continue
                presisi = "kelurahan"
            elif level == LEVEL_KELURAHAN:
                presisi = "kelurahan"
            elif (presisi := jenis_hasil(h, r["nama_rth"], r["jenis_rth"])) is None:
                continue
            lat, lon = float(h["lat"]), float(h["lon"])
            if presisi in terbaik or not dalam_polygon(lat, lon, poly_jkt) or not dalam_polygon(lat, lon, poly_kec):
                continue
            terbaik[presisi] = {"lat": lat, "lon": lon, "presisi": presisi, "kueri": kueri,
                                "osm_jenis": f"{h.get('class')}/{h.get('type')}", "osm_nama": h.get("name") or ""}
        if "objek" in terbaik:
            break
    for p in URUTAN_PRESISI:
        if p in terbaik:
            return terbaik[p]
    return {"lat": None, "lon": None, "presisi": "gagal", "kueri": "", "osm_jenis": "", "osm_nama": ""}


def terapkan_manual(out: pd.DataFrame, poly_jkt: dict, poly_kec: dict) -> pd.DataFrame:
    """Timpa hasil geocoding dengan koordinat manual (presisi "manual") setelah divalidasi polygon."""
    if not MANUAL.exists():
        return out
    m = pd.read_csv(MANUAL, encoding="utf-8-sig")
    m["lat"], m["lon"] = pd.to_numeric(m["lat"], errors="coerce"), pd.to_numeric(m["lon"], errors="coerce")
    m = m.dropna(subset=["lat", "lon"])
    print(f"\nTitik manual terisi: {len(m)} dari {MANUAL.name}")
    for _, r in m.iterrows():
        idx = out.index[(out["kecamatan"] == r["kecamatan"]) & (out["no"] == int(r["no"]))]
        label = f"{r['kecamatan']} no.{int(r['no'])} {str(r.get('nama_rth', ''))[:35]!r}"
        if len(idx) != 1:
            print(f"  DILEWATI {label}: kecamatan/no tidak ditemukan di data sumber")
            continue
        if not (dalam_polygon(r["lat"], r["lon"], poly_jkt) and dalam_polygon(r["lat"], r["lon"], poly_kec[r["kecamatan"]])):
            print(f"  DILEWATI {label}: ({r['lat']}, {r['lon']}) di luar Jakarta/kecamatan {r['kecamatan']}")
            continue
        catatan = "" if pd.isna(r.get("catatan")) else str(r.get("catatan"))
        out.loc[idx, ["lat", "lon", "presisi", "kueri", "osm_jenis", "osm_nama"]] = \
            [r["lat"], r["lon"], "manual", f"manual: {catatan}".strip(": "), "", ""]
        print(f"  OK {label}")
    return out


def main():
    g = Geocoder()
    df = muat_sumber()
    print(f"{len(df)} titik RTH dari {SUMBER.name}. Cache: {len(g.cache)} entri.\n")

    poly_jkt = ambil_polygon(g, "Daerah Khusus Ibukota Jakarta")
    poly_kec = {k: ambil_polygon(g, f"{k.title()}, {kota}", level=LEVEL_KECAMATAN) for k, (_, kota) in KECAMATAN.items()}

    hasil = []
    for i, r in df.iterrows():
        stasiun, kota = KECAMATAN[r["kecamatan"]]
        h = geocode_baris(g, r, kota, poly_jkt, poly_kec[r["kecamatan"]])
        hasil.append({"kecamatan": r["kecamatan"], "stasiun": stasiun, "no": int(r["no"]),
                      "kelurahan": r["kelurahan"], "nama_rth": r["nama_rth"], "alamat": r["alamat"],
                      "jenis_rth": r["jenis_rth"], "luas_m2": r["luas_m2"], **h})
        if (i + 1) % 20 == 0 or i + 1 == len(df):
            print(f"  {i + 1}/{len(df)} baris  (permintaan baru ke Nominatim: {g.panggilan})", flush=True)

    out = terapkan_manual(pd.DataFrame(hasil), poly_jkt, poly_kec)
    out.to_csv(KELUARAN, index=False, encoding="utf-8-sig")
    print(f"\nTersimpan: {KELUARAN.relative_to(ROOT)}\n")
    ringkas = pd.crosstab(out["kecamatan"], out["presisi"], margins=True, margins_name="TOTAL")
    print(ringkas.reindex(columns=[c for c in ["objek", "manual", "jalan", "kelurahan", "gagal", "TOTAL"] if c in ringkas.columns])
          .to_string())


if __name__ == "__main__":
    main()
