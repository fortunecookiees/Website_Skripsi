# Konteks Project: Aplikasi Prediksi PM2.5 DKI Jakarta (Skripsi)

Aplikasi web Streamlit untuk menampilkan prediksi ISPU PM2.5 di 5 SPKU DKI Jakarta, 1–7 hari ke depan. Model XGBoost (hyperparameter hasil PSO) **sudah dilatih di Google Colab**. Aplikasi ini **tidak melakukan training ulang**, hanya inference. Tidak pakai database dan tidak pakai login. Semua data dibaca dari file statis.

## File yang tersedia

```
models/model_pm25_h1.pkl ... model_pm25_h7.pkl   # dict: {'model', 'scaler', 'fitur', 'horizon'}
models/hasil_evaluasi.json                       # metrik uji: default, random_search, pso, persistence (key "1".."7"), best_pso, best_rs
data/datasetskripsi.xlsx                         # dataset terpadu 3.275 baris (5 stasiun × 655 hari, 24 Jan 2024 – 8 Nov 2025)
train/training.py                                # kode training asli (ACUAN preprocessing, jangan diubah)
```

- Model h memprediksi PM2.5 hari t+h dari fitur hari t.
- Scaler sudah ada di dalam tiap .pkl. Urutan kolom input **harus** sama dengan `fitur` di .pkl.
- Library: xgboost==3.3.0, scikit-learn & numpy harus sama versinya dengan Colab (lihat requirements.txt).

## 21 fitur input (urutan sesuai .pkl)

- **Spasial** (variabel yang diteliti, beri penanda khusus di UI): kepadatan_penduduk_jiwa_km2, luas_rth_km2
- **Meteorologi**: suhu_c, kelembapan_pct, curah_hujan_mm, tutupan_awan_pct, kecepatan_angin_kmh, tekanan_hpa, arah_angin_deg
- **Polutan** (indeks ISPU): pm10, pm25, so2, co, o3, no2
- **Turunan** (dihitung otomatis, TIDAK bisa diubah user): pm25_lag1, pm25_lag2, pm25_lag3, pm25_roll3, bulan, hari

## Preprocessing di app (harus identik dengan training)

1. Buang kolom `max`, `parameter_kritis`, `kategori` kalau ada
2. Sort per `stasiun`, `tanggal`
3. Forward fill polutan per stasiun dengan `limit=7`
4. Lag 1–3 per stasiun, `pm25_roll3 = shift(1).rolling(3).mean()` per stasiun, `bulan = month`, `hari = dayofweek`
5. Split evaluasi: ambil tanggal unik setelah dropna (lag + target h1–h7). Data uji = tanggal >= `tu[int(n*0.85)]`. Replikasi persis dari `train/training.py`.

## Stasiun

| Stasiun            | Kecamatan     | Lat     | Lon      |
| ------------------ | ------------- | ------- | -------- |
| DKI1 Bundaran HI   | Menteng       | -6.1946 | 106.8229 |
| DKI2 Kelapa Gading | Kelapa Gading | -6.1553 | 106.9070 |
| DKI3 Jagakarsa     | Jagakarsa     | -6.3395 | 106.8261 |
| DKI4 Lubang Buaya  | Cipayung      | -6.2919 | 106.9086 |
| DKI5 Kebon Jeruk   | Kebon Jeruk   | -6.1919 | 106.7683 |

Nama stasiun di Excel bisa sedikit beda, cek dulu isi kolom `stasiun`.

## Kategori ISPU (PermenLHK No. 14/2020)

| Kategori           | Rentang | Warna  |
| ------------------ | ------- | ------ |
| Baik               | 1–50    | Hijau  |
| Sedang             | 51–100  | Biru   |
| Tidak Sehat        | 101–200 | Kuning |
| Sangat Tidak Sehat | 201–300 | Merah  |
| Berbahaya          | ≥301    | Hitam  |

Warna **hanya** dipakai untuk kategori ISPU. Elemen lain pakai warna netral.

## Modul aplikasi

### 1. Dashboard

- Pilih 1 dari 5 stasiun
- Panel input 21 fitur dikelompokkan: spasial (dengan penanda), meteorologi, polutan, turunan
- **Mode Prediksi Aktual**: semua nilai dikunci ke kondisi terakhir dataset (8 Nov 2025), prediksi 9–15 Nov 2025
- **Mode Simulasi**: spasial, meteorologi, dan polutan bisa diubah, sedangkan fitur turunan tetap terkunci. Tampilkan tabel perbandingan aktual vs simulasi + disclaimer "hasil simulasi bukan prediksi kondisi sebenarnya"
- Output: nilai PM2.5 t+1..t+7 + kategori & warna ISPU, grafik 7 hari
- Ringkasan status kelima stasiun (prediksi t+1 tiap stasiun)
- Peta interaktif lokasi 5 SPKU

### 2. Evaluation

- Pilih stasiun + tanggal acuan (hanya tanggal di periode uji yang t+7-nya masih ada di data)
- Tabel prediksi vs aktual untuk 7 horizon
- Grafik PM2.5 aktual di sekitar tanggal acuan + titik prediksi
- Bagian kedua: metrik seluruh data uji (MAE, RMSE, MAPE, R²) dari `hasil_evaluasi.json`, perbandingan Default vs Random Search vs PSO per horizon, dan peringkat feature importance dari `model_pm25_h1.pkl`

### 3. Information

- Cara kerja model (XGBoost + PSO, 7 model per horizon)
- Spesifikasi model (hyperparameter `best_pso`)
- Rincian 21 variabel + penjelasan variabel spasial
- Tabel kategori ISPU
- Panduan penggunaan aplikasi
- Info penyusun: Fortuna, NIM 535230144, Teknik Informatika, Universitas Tarumanagara (pembimbing: [isi nanti])

## Aturan kerja

- Kerjakan **bertahap**. Setelah tiap tahap selesai, berhenti dan tunggu konfirmasi sebelum lanjut.
- Jangan ubah file di `models/`, `data/`, dan `train/`.
- Kode rapi dan modular: logika preprocessing & inference dipisah dari UI.
- Teks UI dalam Bahasa Indonesia.
