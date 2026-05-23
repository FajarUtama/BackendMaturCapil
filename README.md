# MaturCapil Semarang — Backend API

Backend FastAPI untuk sistem pengaduan masyarakat **MaturCapil Semarang**, selaras dengan frontend `MaturCapilFrontend` dan dokumen `docs/API_SPEC_BACKEND.md`.

## Stack

- **FastAPI** + **Swagger** (`/docs`, `/redoc`)
- **MySQL** + SQLAlchemy (cocok dengan **XAMPP** + phpMyAdmin)
- **JWT** (access + refresh token)
- Upload file lokal (`/uploads`)

**Docker tidak wajib.** Backend ini dirancang jalan **native** di Windows: Python + MySQL dari XAMPP sudah cukup.

---

## Persiapan (XAMPP — disarankan)

### 1. Nyalakan MySQL di XAMPP

1. Buka **XAMPP Control Panel**
2. Start **Apache** (opsional, untuk phpMyAdmin) dan **MySQL**
3. Buka phpMyAdmin: http://localhost/phpmyadmin

### 2. Buat database

Di phpMyAdmin:

1. Tab **Databases**
2. Nama database: `maturcapil_db`
3. Collation: `utf8mb4_unicode_ci`
4. Klik **Create**

Tabel akan dibuat otomatis saat pertama kali menjalankan `scripts.seed` atau `python run.py` (SQLAlchemy `create_all`).

### 3. File environment

```powershell
cd D:\PROJECTS\MaturCapil\MaturCapilBackend
copy .env.example .env
```

Edit `.env` — sesuaikan `DATABASE_URL` dengan akun MySQL XAMPP Anda:

```env
# Password root kosong (default XAMPP)
DATABASE_URL=mysql+pymysql://root@localhost:3306/maturcapil_db?charset=utf8mb4

# Jika root punya password:
# DATABASE_URL=mysql+pymysql://root:password_anda@localhost:3306/maturcapil_db?charset=utf8mb4
```

> **Tip:** Jika password berisi karakter khusus (`@`, `#`, dll.), encode untuk URL atau buat user MySQL khusus untuk project ini.

### 4. Python & dependensi

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

### 5. Seed data demo

Pastikan MySQL XAMPP sudah **Running**, lalu:

```powershell
python -m scripts.seed
```

Akun demo (password: `Password1`):

| Email | Role |
|-------|------|
| citizen@maturcapil.id | Masyarakat |
| admin@maturcapil.id | Admin |
| superadmin@maturcapil.id | Super Admin |
| amir@maturcapil.id | Admin (permission terbatas) |

Setelah seed, di phpMyAdmin Anda bisa melihat tabel (`users`, `complaints`, `categories`, dll.) di database `maturcapil_db`.

### 6. Jalankan API

```powershell
python run.py
```

- API: http://localhost:3000/api/v1  
- Swagger: http://localhost:3000/docs  
- Health: http://localhost:3000/health  

---

## Integrasi Frontend

Di `MaturCapilFrontend/.env`:

```env
VITE_USE_MOCK_API=false
VITE_API_BASE_URL=http://localhost:3000/api/v1
```

---

## OTP email (development)

Jika `SMTP_HOST` kosong di `.env`, kode OTP dicetak ke **log konsol** terminal tempat `python run.py` berjalan.

---

## Deploy ke Railway

Proyek ini sudah menyertakan `railway.json` dan `Procfile` dengan start command:

```text
python start_railway.py
```

### Langkah

1. Push repo ke GitHub: https://github.com/FajarUtama/BackendMaturCapil
2. Di [Railway](https://railway.com) → **New Project** → **Deploy from GitHub** → pilih repo backend
3. **Tambah database MySQL** (wajib — tanpa ini error `Can't connect to MySQL server on 'localhost'`):
   - Klik **+ New** → **Database** → **MySQL**
   - Tunggu sampai status MySQL **Active**
4. **Hubungkan MySQL ke service backend** (pakai URL **internal**, bukan public):
   - Buka service **backend** → tab **Variables**
   - Tambah variabel:
     ```env
     DATABASE_URL=${{NamaServiceMySQL.MYSQL_URL}}
     ```
     (`MYSQL_URL`, **bukan** `MYSQL_PUBLIC_URL` — public proxy sering gagal dari dalam container)
   - Jangan ubah nama database di URL ke `maturcapil_db` kecuali Anda sudah membuatnya di MySQL. Default Railway: database **`railway`**. Backend otomatis menjalankan `CREATE DATABASE IF NOT EXISTS` untuk nama di `DATABASE_URL` (mis. `maturcapil_db`).
   - Simpan
5. Tambah variabel lain di service backend:

| Variable | Contoh |
|----------|--------|
| `SECRET_KEY` | string acak panjang (wajib production) |
| `DEBUG` | `false` |
| `APP_ENV` | `production` |
| `CORS_ORIGINS` | URL frontend Anda, mis. `https://app.vercel.app` |
| `PUBLIC_BASE_URL` | URL publik Railway, mis. `https://xxx.up.railway.app` |

**Port (penting — 502 connection refused):**

| Variable | Di Railway |
|----------|------------|
| `PORT` | **Jangan set manual** (jangan `3000` / `8000` dari `.env` lokal). Railway inject otomatis; app pakai `start_railway.py`. |
| `HOST` | Opsional / boleh dihapus — uvicorn selalu `0.0.0.0`. |

Di log deploy harus ada: `Starting uvicorn on 0.0.0.0:XXXX (PORT env='XXXX')` — angka itu harus sama dengan **Networking → Port** di service backend (biasanya biarkan **Auto**).

6. **Redeploy** backend setelah variabel disimpan
7. Cek log deploy — harus ada baris: `Database target: mysql+pymysql://user:****@...` (bukan `localhost`)
8. Seed data (sekali), lewat Railway **Shell** pada service backend:

```bash
python -m scripts.seed
```

### Variabel MySQL yang didukung otomatis

Backend membaca (urutan prioritas):

- `DATABASE_URL` (disarankan: reference `MYSQL_URL` dari service MySQL)
- `MYSQL_URL` (internal Railway)
- Atau rakit dari: `MYSQLHOST`, `MYSQLPORT`, `MYSQLUSER`, `MYSQLPASSWORD`, `MYSQLDATABASE`

Format `mysql://` dari Railway otomatis diubah ke `mysql+pymysql://`.

`MYSQL_PUBLIC_URL` **tidak** dipakai backend — hanya untuk DBeaver / MySQL Workbench dari laptop Anda.

> **Upload file:** di Railway, folder `uploads/` bersifat ephemeral (hilang saat redeploy). Untuk production jangka panjang, rencanakan MinIO/S3.

Referensi: [Railway FastAPI guide](https://docs.railway.com/guides/fastapi), [Railpack Python](https://railpack.com/languages/python).

---

## Docker (opsional)

File `docker-compose.yml` hanya alternatif jika Anda **tidak** memakai XAMPP. Boleh diabaikan sepenuhnya.

```bash
docker compose up -d
```

---

## Troubleshooting XAMPP

| Masalah | Solusi |
|---------|--------|
| `Can't connect to MySQL server` | Pastikan MySQL di XAMPP status **Running**, port 3306 tidak dipakai aplikasi lain |
| `Access denied for user 'root'` | Cek password di `.env` — samakan dengan phpMyAdmin |
| `Unknown database 'maturcapil_db'` | Buat database `maturcapil_db` di phpMyAdmin dulu |
| Port 3000 sudah dipakai | Ubah `PORT=3001` di `.env` dan sesuaikan `VITE_API_BASE_URL` di frontend |

---

## Endpoint utama

Semua path diawali `/api/v1`:

- `POST /auth/login`, `/auth/register`, `/auth/me`, …
- `GET|POST /complaints`, `PATCH /complaints/:id/status`, …
- `GET|POST /categories`, `GET|POST /users`, …
- `GET /audit-logs`, `GET /audit-logs/export`

**Dokumentasi API untuk FE (endpoint, payload, response):** [`docs/API_DOCUMENTATION.md`](docs/API_DOCUMENTATION.md)

Spesifikasi awal (referensi): `MaturCapilFrontend/docs/API_SPEC_BACKEND.md`.

---

## Struktur proyek

```
app/
  api/v1/       # Router endpoint
  core/         # Security, deps, constants
  models/       # SQLAlchemy models
  schemas/      # Pydantic request/response
  services/     # Business logic
scripts/seed.py # Data awal + buat tabel
```
