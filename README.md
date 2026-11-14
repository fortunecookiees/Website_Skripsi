<a id="readme-top"></a>

<!-- PROJECT SHIELDS -->

[![Contributors][contributors-shield]][contributors-url]
[![Forks][forks-shield]][forks-url]
[![Stargazers][stars-shield]][stars-url]
[![Issues][issues-shield]][issues-url]

<!-- PROJECT LOGO -->
<br />
<div align="center">
  <a href="https://github.com/fortunecookiees/Website_Skripsi">
    <img src="assets/logo.png" alt="NafasKota Logo" width="300" height="auto">
  </a>

<h3 align="center">NafasKota</h3>

  <p align="center">
    Prediksi PM2.5 DKI Jakarta untuk Tujuh Hari ke Depan
    <br />
    Aplikasi web prediksi ISPU PM2.5 menggunakan XGBoost dengan optimasi Particle Swarm Optimization (PSO)
    <br />
    <br />
    <a href="https://nafaskota.streamlit.app">Lihat Aplikasi</a>
    ·
    <a href="https://github.com/fortunecookiees/Website_Skripsi/issues">Laporkan Bug</a>
  </p>
</div>

<!-- TABLE OF CONTENTS -->
<details>
  <summary>Daftar Isi</summary>
  <ol>
    <li>
      <a href="#tentang-aplikasi">Tentang Aplikasi</a>
      <ul>
        <li><a href="#dibangun-dengan">Dibangun Dengan</a></li>
        <li><a href="#fitur">Fitur</a></li>
      </ul>
    </li>
    <li>
      <a href="#memulai">Memulai</a>
      <ul>
        <li><a href="#prasyarat">Prasyarat</a></li>
        <li><a href="#instalasi">Instalasi</a></li>
      </ul>
    </li>
    <li><a href="#penggunaan">Penggunaan</a></li>
    <li><a href="#training-model">Training Model</a></li>
    <li><a href="#struktur-folder">Struktur Folder</a></li>
  </ol>
</details>

<!-- ABOUT THE PROJECT -->

## Tentang Aplikasi

NafasKota adalah aplikasi web untuk memprediksi indeks ISPU PM2.5 hingga **tujuh hari ke depan** pada lima Stasiun Pemantauan Kualitas Udara (SPKU) di DKI Jakarta, yaitu Bundaran HI, Kelapa Gading, Jagakarsa, Lubang Buaya, dan Kebon Jeruk. Model prediksi dibangun menggunakan **Extreme Gradient Boosting (XGBoost)** yang hyperparameter-nya dioptimasi dengan **Particle Swarm Optimization (PSO)**.

**Kenapa NafasKota?**

- Konsentrasi PM2.5 di DKI Jakarta masih sering melampaui batas aman
- Informasi kualitas udara yang tersedia umumnya hanya menunjukkan kondisi saat ini
- Prediksi beberapa hari ke depan membantu masyarakat mengantisipasi penurunan kualitas udara

Model memanfaatkan data polutan, meteorologi, kepadatan penduduk, dan luas Ruang Terbuka Hijau (RTH) periode Januari 2024 – November 2025. Pada data uji, XGBoost-PSO menghasilkan rata-rata RMSE **14,210**, lebih rendah dibandingkan hyperparameter bawaan (15,303) dan Random Search (14,647).

Repositori ini merupakan bagian dari skripsi Program Studi Teknik Informatika, Fakultas Teknologi Informasi, Universitas Tarumanagara.

<p align="right">(<a href="#readme-top">kembali ke atas</a>)</p>

### Dibangun Dengan

- [![Python][Python.org]][Python-url]
- [![Streamlit][Streamlit.io]][Streamlit-url]
- [![XGBoost][XGBoost-badge]][XGBoost-url]
- [![scikit-learn][Sklearn-badge]][Sklearn-url]
- [![Plotly][Plotly-badge]][Plotly-url]
- [![Supabase][Supabase.com]][Supabase-url]

<p align="right">(<a href="#readme-top">kembali ke atas</a>)</p>

### Fitur

- **Prediksi 7 Hari**: prediksi PM2.5 t+1 hingga t+7 beserta kategori ISPU dan saran kesehatan
- **Mode Simulasi**: ubah nilai polutan, cuaca, kepadatan penduduk, dan luas RTH untuk melihat perubahan prediksi
- **Peta Stasiun**: lokasi lima SPKU beserta titik RTH di sekitarnya
- **Data Historis**: tren, distribusi kategori, dan rata-rata bulanan PM2.5
- **Evaluation**: perbandingan prediksi dengan nilai aktual, metrik evaluasi, dan perbandingan metode optimasi
- **Unggah Data**: prediksi dan validasi dari data milik pengguna (wajib masuk)
- **Admin**: kelola pengguna dan perbarui data Dashboard
- **Dua Bahasa**: tersedia dalam Bahasa Indonesia dan Inggris

<p align="right">(<a href="#readme-top">kembali ke atas</a>)</p>

<!-- GETTING STARTED -->

## Memulai

Ikuti langkah berikut untuk menjalankan NafasKota di komputer lokal.

### Prasyarat

- **Python 3.13**
  ```sh
  python --version
  ```
- **Git**
  ```sh
  git --version
  ```

### Instalasi

1. **Clone repositori**

   ```sh
   git clone https://github.com/fortunecookiees/Website_Skripsi.git
   cd Website_Skripsi
   ```

2. **Buat virtual environment dan install library**

   ```sh
   python -m venv venv
   venv\Scripts\activate  # Windows
   # atau
   source venv/bin/activate  # macOS/Linux
   pip install -r requirements.txt
   ```

3. **Atur konfigurasi Supabase**

   Salin `.streamlit/secrets.example.toml` menjadi `.streamlit/secrets.toml`, lalu isi:

   ```toml
   [supabase]
   url = "your_supabase_url"
   key = "your_publishable_key"
   service_key = "your_secret_key"   # khusus fitur Admin
   bucket = "your_storage_bucket"    # khusus fitur Admin
   ```

   Tanpa konfigurasi ini, fitur akun dan admin tidak aktif, tetapi halaman lain tetap dapat digunakan.

4. **Jalankan aplikasi**

   ```sh
   streamlit run app.py
   ```

<p align="right">(<a href="#readme-top">kembali ke atas</a>)</p>

<!-- USAGE -->

## Penggunaan

1. Buka http://localhost:8501
2. Pilih menu **Dashboard**, lalu pilih salah satu dari lima stasiun
3. Lihat prediksi PM2.5 tujuh hari ke depan, grafik, dan peta
4. Pilih **Mode Simulasi** untuk mengubah nilai variabel, lalu klik **Prediksi**
5. Buka **Evaluation** untuk melihat kinerja model pada data uji
6. Masuk atau daftar akun untuk menggunakan **Unggah Data** dengan template yang tersedia

Panduan lengkap tersedia pada manual program di menu **Information** atau file `assets/manual_program.pdf`.

<p align="right">(<a href="#readme-top">kembali ke atas</a>)</p>

<!-- TRAINING -->

## Training Model

Pre-processing dan training model dijalankan di Google Colab menggunakan notebook `models/training model.ipynb` (versi skrip: `train/training.py`). Hasilnya berupa:

- `model_pm25_h1.pkl` – `model_pm25_h7.pkl`: tujuh model XGBoost-PSO beserta scaler
- `hasil_evaluasi.json`: metrik model bawaan, Random Search, PSO, dan persistence
- `hasil_skenario.json`: hasil skenario fitur S1, S2, dan S3

Untuk memastikan hasil aplikasi sama dengan hasil training:

```sh
python tes_inference.py
```

<p align="right">(<a href="#readme-top">kembali ke atas</a>)</p>

<!-- STRUCTURE -->

## Struktur Folder

```
app.py          # pintu masuk aplikasi dan navigasi
views/          # satu file untuk setiap halaman
components/     # elemen tampilan dan akses data
core/           # preprocessing, inference, metrik, validasi unggahan
auth/           # autentikasi dan penyimpanan Supabase
models/         # model .pkl, hasil evaluasi, dan notebook training
data/           # dataset penelitian dan koordinat RTH
train/          # kode training
assets/         # logo dan manual program
```

<p align="right">(<a href="#readme-top">kembali ke atas</a>)</p>

<!-- MARKDOWN LINKS & IMAGES -->

[contributors-shield]: https://img.shields.io/github/contributors/fortunecookiees/Website_Skripsi.svg?style=for-the-badge
[contributors-url]: https://github.com/fortunecookiees/Website_Skripsi/graphs/contributors
[forks-shield]: https://img.shields.io/github/forks/fortunecookiees/Website_Skripsi.svg?style=for-the-badge
[forks-url]: https://github.com/fortunecookiees/Website_Skripsi/network/members
[stars-shield]: https://img.shields.io/github/stars/fortunecookiees/Website_Skripsi.svg?style=for-the-badge
[stars-url]: https://github.com/fortunecookiees/Website_Skripsi/stargazers
[issues-shield]: https://img.shields.io/github/issues/fortunecookiees/Website_Skripsi.svg?style=for-the-badge
[issues-url]: https://github.com/fortunecookiees/Website_Skripsi/issues

<!-- Technology Badges -->

[Python.org]: https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white
[Python-url]: https://www.python.org/
[Streamlit.io]: https://img.shields.io/badge/Streamlit-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white
[Streamlit-url]: https://streamlit.io/
[XGBoost-badge]: https://img.shields.io/badge/XGBoost-189FDD?style=for-the-badge&logoColor=white
[XGBoost-url]: https://xgboost.readthedocs.io/
[Sklearn-badge]: https://img.shields.io/badge/scikit--learn-F7931E?style=for-the-badge&logo=scikitlearn&logoColor=white
[Sklearn-url]: https://scikit-learn.org/
[Plotly-badge]: https://img.shields.io/badge/Plotly-3F4F75?style=for-the-badge&logo=plotly&logoColor=white
[Plotly-url]: https://plotly.com/
[Supabase.com]: https://img.shields.io/badge/Supabase-3ECF8E?style=for-the-badge&logo=supabase&logoColor=white
[Supabase-url]: https://supabase.com/
