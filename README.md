# Discord Bot with Web Dashboard

Bot Discord yang canggih dengan antarmuka web untuk monitoring dan kontrol real-time. Bot ini dapat membalas pesan otomatis menggunakan Google Gemini AI atau pesan dari file teks.

## Fitur Utama

### 🤖 Bot Discord
- **Auto Reply dengan AI**: Menggunakan Google Gemini AI untuk membalas pesan
- **Multi-Channel Support**: Dapat bekerja di beberapa channel sekaligus
- **Multi-Token Support**: Mendukung beberapa akun bot Discord
- **Slow Mode Detection**: Otomatis mendeteksi dan menyesuaikan dengan slow mode
- **Message Management**: Opsi untuk menghapus pesan bot setelah waktu tertentu
- **Flexible Settings**: Pengaturan berbeda untuk setiap channel

### 🌐 Web Dashboard
- **Real-time Monitoring**: Monitor status bot secara real-time
- **Live Logs**: Melihat log aktivitas bot langsung di browser
- **Bot Control**: Start, stop, dan restart bot dari dashboard
- **Statistics**: Statistik pesan terkirim, diterima, dan aktivitas terakhir
- **API Status**: Monitor status Google API keys dan rate limiting
- **Responsive Design**: Tampilan yang bagus di desktop dan mobile

## Screenshot Dashboard

![Dashboard Preview](dashboard-preview.png)

## Persyaratan Sistem

- Python 3.7+
- Discord Bot Token
- Google API Key (untuk Gemini AI)
- Koneksi internet yang stabil

## Instalasi

### 1. Clone atau Download Kode
```bash
git clone <repository-url>
cd discord-bot-dashboard
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Setup Environment Variables
Buat file `.env` di direktori utama dengan konfigurasi berikut:

```env
# Discord Bot Tokens (pisahkan dengan koma jika lebih dari satu)
DISCORD_TOKENS=your_discord_token_1,your_discord_token_2

# Atau gunakan satu token saja
DISCORD_TOKEN=your_discord_token

# Google API Keys (pisahkan dengan koma jika lebih dari satu)
GOOGLE_API_KEYS=your_google_api_key_1,your_google_api_key_2
```

### 4. Buat File Pesan (Opsional)
Jika ingin menggunakan pesan dari file, buat file `pesan.txt` dengan satu pesan per baris:

```
Halo! Bagaimana kabarmu hari ini?
Terima kasih sudah mengirim pesan!
Wah menarik sekali!
Apa kabar?
Semoga harimu menyenangkan!
```

### 5. Mendapatkan Channel ID Discord
1. Buka Discord di browser atau aplikasi desktop
2. Klik kanan pada channel yang ingin digunakan
3. Pilih "Copy ID" (pastikan Developer Mode aktif di Settings > Advanced)

## Cara Penggunaan

### 1. Jalankan Bot
```bash
python dc.py
```

### 2. Konfigurasi Channel
Program akan meminta input:
- **Channel IDs**: Masukkan ID channel Discord (pisahkan dengan koma untuk multiple channels)
- **Untuk setiap channel**, atur:
  - Gunakan Google Gemini AI atau tidak
  - Bahasa prompt (ID/EN)
  - Delay membaca pesan
  - Interval auto reply
  - Penggunaan slow mode
  - Mode reply
  - Pengaturan penghapusan pesan

### 3. Akses Web Dashboard
Setelah bot berjalan, dashboard akan otomatis terbuka di browser:
```
http://127.0.0.1:5000
```

## Fitur Dashboard

### Status Cards
- **Bot Status**: Status online/offline, uptime, jumlah channel aktif
- **API Status**: Status Google API keys, rate limiting
- **Message Stats**: Statistik pesan terkirim dan diterima

### Controls
- **Start Bot**: Mulai bot
- **Stop Bot**: Hentikan bot
- **Restart Bot**: Restart bot
- **Clear Logs**: Bersihkan log

### Live Logs
- Monitor aktivitas bot real-time
- Auto scroll ON/OFF
- Color-coded log levels (Success, Error, Warning, Info, Wait)

## Konfigurasi Advanced

### Multiple API Keys
Untuk menghindari rate limiting, gunakan beberapa Google API keys:
```env
GOOGLE_API_KEYS=key1,key2,key3,key4,key5
```

### Multiple Bot Tokens
Untuk load balancing di beberapa channel:
```env
DISCORD_TOKENS=token1,token2,token3
```

### Pengaturan Channel
Setiap channel dapat dikonfigurasi dengan pengaturan berbeda:
- **AI Mode**: Gunakan Gemini AI atau pesan dari file
- **Language**: Bahasa Indonesia atau English
- **Delays**: Berbagai pengaturan delay
- **Reply Mode**: Balas sebagai reply atau pesan biasa
- **Auto Delete**: Hapus pesan bot otomatis

## Troubleshooting

### Bot Tidak Merespon
1. Pastikan bot token valid
2. Cek apakah bot ada permission di channel
3. Periksa log di dashboard untuk error

### API Error 429 (Rate Limited)
1. Bot akan otomatis switch ke API key lain
2. Tambahkan lebih banyak Google API keys
3. Kurangi frekuensi pesan

### Dashboard Tidak Terbuka
1. Pastikan port 5000 tidak digunakan aplikasi lain
2. Coba akses manual: http://127.0.0.1:5000
3. Periksa firewall/antivirus

### Memory/CPU Usage Tinggi
1. Kurangi jumlah channel aktif
2. Increase delay intervals
3. Disable real-time logging jika tidak perlu

## Tips Penggunaan

### Best Practices
1. **Rate Limiting**: Gunakan delay yang wajar (minimal 5-10 detik)
2. **API Keys**: Siapkan beberapa Google API keys untuk backup
3. **Channel Management**: Jangan gunakan terlalu banyak channel sekaligus
4. **Monitoring**: Selalu monitor dashboard untuk memastikan bot berjalan normal

### Optimisasi Performance
1. Gunakan multiple bot tokens untuk load balancing
2. Set delay yang optimal berdasarkan aktivitas channel
3. Enable slow mode detection untuk channel yang ramai
4. Gunakan auto delete untuk menghemat storage Discord

## Security

### Keamanan Token
- Jangan share Discord token atau Google API key
- Gunakan file `.env` dan jangan commit ke git
- Rotate token secara berkala

### Server Security
- Dashboard hanya bisa diakses dari localhost
- Tidak ada autentikasi eksternal
- Data tidak disimpan secara permanen

## Kontribusi

Silakan buat issue atau pull request untuk:
- Bug fixes
- Feature requests
- Dokumentasi improvements
- Performance optimizations

## License

Project ini menggunakan MIT License. Lihat file LICENSE untuk detail.

## Support

Jika mengalami masalah:
1. Cek section Troubleshooting di atas
2. Buat issue di GitHub repository
3. Sertakan log error dan konfigurasi (tanpa token)

---

**Disclaimer**: Gunakan bot ini dengan bijak dan sesuai dengan Terms of Service Discord. Pastikan tidak melakukan spam atau mengganggu pengguna lain.
