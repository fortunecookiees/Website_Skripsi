"""Bahasa pesan dari core/ & auth/ (tanpa Streamlit).

Lapisan UI (components/bahasa.py) memanggil atur_inggris() setiap run. ContextVar bersifat per thread, dan
Streamlit menjalankan skrip tiap sesi di thread sendiri, jadi pilihan bahasa satu pengguna tidak bocor ke
pengguna lain. Default: Indonesia (dipakai juga oleh tes).
"""
from contextvars import ContextVar

_INGGRIS: ContextVar[bool] = ContextVar("bahasa_inggris", default=False)


def atur_inggris(nilai: bool) -> None:
    _INGGRIS.set(bool(nilai))


def tr(id_: str, en: str) -> str:
    """Teks pesan sesuai bahasa aktif."""
    return en if _INGGRIS.get() else id_


# Pesan tetap dari auth/ (kunci = teks Indonesia apa adanya). Dipakai lewat terjemah() agar konstanta
# & tes yang memeriksa teks Indonesia tidak berubah.
_PESAN_EN = {
    "Email sudah terdaftar. Silakan masuk atau gunakan email lain.":
        "This email is already registered. Sign in or use another email.",
    "Email atau password salah.": "Incorrect email or password.",
    "Password terlalu lemah. Gunakan minimal 6 karakter.": "Password is too weak. Use at least 6 characters.",
    "Format email tidak valid.": "Invalid email format.",
    "Data yang dikirim tidak valid. Periksa kembali email dan password.":
        "The submitted data is invalid. Check your email and password.",
    "Email belum dikonfirmasi. Periksa kotak masuk email Anda.": "Email not confirmed yet. Check your inbox.",
    "Pendaftaran akun baru sedang dinonaktifkan.": "New account registration is currently disabled.",
    "Masuk dengan email sedang dinonaktifkan.": "Email sign-in is currently disabled.",
    "Terlalu banyak percobaan. Coba lagi beberapa menit lagi.": "Too many attempts. Try again in a few minutes.",
    "Sesi berakhir. Silakan masuk kembali.": "Your session has ended. Please sign in again.",
    "Akun Anda dinonaktifkan oleh admin. Hubungi pengelola aplikasi.":
        "Your account has been deactivated by an admin. Contact the app maintainer.",
    "Password baru harus berbeda dari password lama.": "The new password must differ from the old one.",
    "Demi keamanan, keluar lalu masuk kembali sebelum mengganti password.":
        "For security, sign out and sign in again before changing your password.",
    "Terjadi kesalahan pada server autentikasi. Coba lagi nanti.":
        "The authentication server returned an error. Try again later.",
    "Tidak dapat terhubung ke server autentikasi. Periksa koneksi internet lalu coba lagi.":
        "Cannot reach the authentication server. Check your internet connection and try again.",
    "Konfigurasi Supabase tidak valid (URL salah). Hubungi pengelola aplikasi.":
        "Invalid Supabase configuration (wrong URL). Contact the app maintainer.",
    "Konfigurasi Supabase tidak valid (API key ditolak). Hubungi pengelola aplikasi.":
        "Invalid Supabase configuration (API key rejected). Contact the app maintainer.",
    "Nama wajib diisi.": "Name is required.",
    "Format email tidak valid, contoh: nama@email.com.": "Invalid email format, e.g. name@email.com.",
    "Password minimal 6 karakter.": "Password must be at least 6 characters.",
    "Konfirmasi password tidak cocok.": "Password confirmation does not match.",
    "Nama maksimal 60 karakter.": "Name must be at most 60 characters.",
    "Password lama wajib diisi.": "Old password is required.",
    "Password baru minimal 6 karakter.": "New password must be at least 6 characters.",
    "Konfirmasi password baru tidak cocok.": "New password confirmation does not match.",
    "Password wajib diisi.": "Password is required.",
    "Password lama salah.": "Incorrect old password.",
    "Permintaan ke server admin gagal. Coba lagi nanti.": "The request to the admin server failed. Try again later.",
    "Tidak dapat terhubung ke server Supabase. Periksa koneksi internet lalu coba lagi.":
        "Cannot reach the Supabase server. Check your internet connection and try again.",
    "Service key ditolak oleh Supabase. Periksa nilai service_key di secrets.":
        "Supabase rejected the service key. Check service_key in secrets.",
    "Bucket Storage tidak ditemukan. Periksa nama bucket di secrets.":
        "Storage bucket not found. Check the bucket name in secrets.",
    "Data tidak ditemukan di server.": "Data not found on the server.",
    "Anda tidak dapat menonaktifkan atau menghapus akun Anda sendiri.":
        "You cannot deactivate or delete your own account.",
    "Akun admin hanya dapat diubah melalui dashboard Supabase.":
        "Admin accounts can only be changed from the Supabase dashboard.",
    "Versi data tidak ditemukan.": "Data version not found.",
    "Key yang dipakai adalah secret key. Gunakan publishable key (sb_publishable_...).":
        "The key in use is a secret key. Use a publishable key (sb_publishable_...).",
    "Key Supabase harus berupa publishable key (sb_publishable_...).":
        "The Supabase key must be a publishable key (sb_publishable_...).",
    "Service key belum diisi di secrets (supabase.service_key).":
        "The service key is not set in secrets (supabase.service_key).",
    "service_key berisi publishable key. Gunakan secret key (sb_secret_...).":
        "service_key contains a publishable key. Use a secret key (sb_secret_...).",
    "service_key tidak dikenali. Gunakan secret key (sb_secret_...) atau service_role key.":
        "service_key is not recognized. Use a secret key (sb_secret_...) or a service_role key.",
    "Data terbaru dari admin gagal dimuat; menampilkan dataset penelitian.":
        "The latest admin data failed to load; showing the research dataset.",
}


def terjemah(teks: str) -> str:
    """Pesan tetap Indonesia -> Inggris jika bahasa Inggris aktif dan terjemahannya ada."""
    return _PESAN_EN.get(teks, teks) if _INGGRIS.get() else teks
