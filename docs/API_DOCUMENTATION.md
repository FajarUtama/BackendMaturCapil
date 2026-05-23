# Dokumentasi API — MaturCapil Semarang (Backend)

Dokumen referensi implementasi **Frontend** terhadap backend FastAPI ini.

| Item | Nilai |
|------|--------|
| **Base URL (dev)** | `http://localhost:3000/api/v1` |
| **Swagger interaktif** | `http://localhost:3000/docs` |
| **ReDoc** | `http://localhost:3000/redoc` |
| **Health check** | `GET http://localhost:3000/health` |
| **Env FE** | `VITE_API_BASE_URL=http://localhost:3000/api/v1` |
| **Versi dokumen** | 2026-05-23 |

---

## Daftar isi

1. [Konvensi umum](#1-konvensi-umum)
2. [Tipe data](#2-tipe-data)
3. [Autentikasi & sesi](#3-autentikasi--sesi)
4. [Pengaduan (Complaints)](#4-pengaduan-complaints)
5. [Kategori](#5-kategori)
6. [Manajemen user](#6-manajemen-user)
7. [Audit log](#7-audit-log)
8. [Ringkasan endpoint](#8-ringkasan-endpoint)
9. [Contoh integrasi FE](#9-contoh-integrasi-fe)

---

## 1. Konvensi umum

### 1.1 Header

| Header | Nilai | Keterangan |
|--------|--------|------------|
| `Authorization` | `Bearer {access_token}` | Wajib untuk endpoint terproteksi |
| `Content-Type` | `application/json` | Request JSON |
| `Content-Type` | `multipart/form-data` | Upload file (laporan / bukti) |
| `Accept` | `application/json` | Disarankan |

### 1.2 Format response

Semua endpoint JSON mengembalikan envelope:

**Sukses (HTTP 2xx):**

```json
{
  "success": true,
  "message": "Pesan opsional",
  "data": {}
}
```

**Gagal (HTTP 4xx / 5xx):**

```json
{
  "success": false,
  "message": "Pesan error utama",
  "errors": {
    "email": ["Email sudah terdaftar."]
  }
}
```

**Validasi Pydantic (HTTP 422):**

```json
{
  "success": false,
  "message": "Validasi gagal.",
  "errors": {
    "password": ["Password minimal 8 karakter."]
  }
}
```

**Batas laporan (email belum verifikasi) — HTTP 403:**

```json
{
  "success": false,
  "message": "Anda hanya dapat membuat 1 laporan sebelum email diverifikasi.",
  "needs_email_verification": true
}
```

> FE dapat membaca `needs_email_verification` atau `needsEmailVerification`.

### 1.3 Penamaan field

- **Request body:** `snake_case` (`category_id`, `password_confirmation`)
- **Response:** `snake_case` (disarankan; mapper FE mendukung `camelCase`)

### 1.4 Pagination

Digunakan pada list `complaints`, `users`, `audit-logs`:

```json
{
  "success": true,
  "data": {
    "items": [],
    "meta": {
      "page": 1,
      "per_page": 20,
      "total": 100
    }
  }
}
```

| Query | Default | Maks |
|--------|---------|------|
| `page` | `1` | — |
| `per_page` | `20` | `100` |

### 1.5 Timestamp

Format ISO 8601 UTC dengan suffix `Z`, contoh: `2026-05-23T10:00:00Z`.

### 1.6 URL file upload

Foto disimpan lokal dan diakses via:

```text
{PUBLIC_BASE_URL}/uploads/{path_relatif}
```

Contoh dev: `http://localhost:3000/uploads/complaints/a1b2c3d4.jpg`

### 1.7 Validasi bisnis (server)

| Field / aturan | Ketentuan |
|----------------|-----------|
| **NIK** | 16 digit angka, unik |
| **Password** | Min 8 karakter, ≥1 huruf besar, ≥1 angka |
| **OTP** | 6 digit, expired **5 menit**, max kirim ulang **3x**, cooldown **60 detik** |
| **Foto laporan** | Maks **3** file, maks **5 MB**/file, JPG / PNG / WebP |
| **Lokasi** | Koordinat harus di bounding box **Kota Semarang** |
| **Email belum verifikasi** | Maks **1** laporan aktif per warga |
| **Login gagal** | Maks **5** percobaan / **15 menit** per email |

### 1.8 Role & permission

| Role | Keterangan |
|------|------------|
| `Masyarakat` | Portal warga |
| `Admin` | Portal pemerintah, hak akses via `permissions[]` |
| `Super Admin` | Semua permission otomatis |

**Daftar permission:**

```text
dashboard.view
complaint.verify
complaint.reject
complaint.close
complaint.export
user.view
user.create
user.update
user.delete
category.manage
auditlog.view
```

**Masking data sensitif:** Admin biasa menerima NIK/email ter-mask di list user. **Super Admin** menerima data lengkap.

---

## 2. Tipe data

### 2.1 User

```json
{
  "id": "usr-a1b2c3d4e5f6",
  "name": "Budi Santoso",
  "email": "citizen@maturcapil.id",
  "role": "Masyarakat",
  "nik": "3374012345678901",
  "status": "ACTIVE",
  "email_verified": true,
  "email_verified_at": "2026-05-01T08:00:00Z",
  "permissions": [],
  "created_at": "2026-05-01T08:00:00Z",
  "deleted_at": null,
  "deleted_by": null
}
```

| Field `status` | Nilai |
|----------------|--------|
| Akun aktif | `ACTIVE` |
| Nonaktif | `INACTIVE` |
| Ditangguhkan | `SUSPENDED` |

### 2.2 Category

```json
{
  "id": "ktp",
  "name": "KTP-el",
  "code": "KTP",
  "description": "Pengaduan KTP elektronik",
  "is_active": true,
  "deleted_at": null,
  "deleted_by": null
}
```

### 2.3 Complaint

```json
{
  "id": "comp-a1b2c3d4e5f6",
  "ticket_number": "TKT-2026-0001",
  "user_id": "usr-a1b2c3d4e5f6",
  "user_name": "Budi Santoso",
  "title": "Judul aduan",
  "description": "Deskripsi lengkap",
  "category_id": "ktp",
  "status": "Menunggu Verifikasi",
  "priority": "Sedang",
  "latitude": -6.9822,
  "longitude": 110.4091,
  "address": "Jl. Contoh, Semarang",
  "created_at": "2026-05-15T08:12:00Z",
  "photos": ["http://localhost:3000/uploads/complaints/abc.jpg"],
  "evidence_after_photos": [],
  "resolution_note": "",
  "resolved_at": null
}
```

| `status` | Arti |
|----------|------|
| `Menunggu Verifikasi` | Baru masuk |
| `Diproses` | Diverifikasi admin |
| `Selesai` | Ditutup dengan bukti |
| `Ditolak` | Ditolak admin |

| `priority` | Nilai |
|------------|--------|
| Prioritas | `Tinggi` \| `Sedang` \| `Rendah` |

### 2.4 Status log

```json
{
  "id": "log-a1b2c3d4e5f6",
  "complaint_id": "comp-a1b2c3d4e5f6",
  "status": "Menunggu Verifikasi",
  "note": "Aduan berhasil diajukan oleh masyarakat.",
  "changed_by": "Budi Santoso",
  "created_at": "2026-05-15T08:12:00Z"
}
```

### 2.5 Chat message

```json
{
  "id": "chat-a1b2c3d4e5f6",
  "complaint_id": "comp-a1b2c3d4e5f6",
  "sender_id": "usr-a1b2c3d4e5f6",
  "sender_name": "Budi Santoso",
  "message": "Isi pesan",
  "created_at": "2026-05-15T08:15:00Z"
}
```

### 2.6 Audit log

```json
{
  "id": "audit-a1b2c3d4e5f6",
  "user_id": "usr-b2c3d4e5f6a7",
  "user_name": "Siti Aminah",
  "action": "VERIFY_COMPLAINT",
  "table_name": "complaints",
  "record_id": "comp-a1b2c3d4e5f6",
  "detail": "Laporan diverifikasi dan diteruskan.",
  "ip_address": "127.0.0.1",
  "created_at": "2026-05-15T08:20:00Z"
}
```

**Nilai `action` umum:** `LOGIN`, `LOGOUT`, `VERIFY_COMPLAINT`, `REJECT_COMPLAINT`, `CLOSE_COMPLAINT`, `UPDATE_STATUS`, `CREATE_USER`, `UPDATE_USER`, `DEACTIVATE_USER`, `RESET_PASSWORD`, `PERMISSION_CHANGE`, `CREATE_CATEGORY`, `UPDATE_CATEGORY`, `DELETE_CATEGORY`

### 2.7 Token payload (login / register verify)

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "random-url-safe-string",
  "token_type": "Bearer",
  "expires_in": 3600,
  "user": { }
}
```

| Field | Keterangan |
|--------|------------|
| `expires_in` | Detik sampai access token expired (default **3600** = 60 menit) |
| `refresh_token` | Disimpan FE untuk fitur refresh (endpoint refresh belum tersedia) |

---

## 3. Autentikasi & sesi

Prefix: `/auth`

---

### 3.1 Login

`POST /auth/login`

| | |
|--|--|
| **Auth** | Tidak |
| **Role** | — |

**Request body:**

```json
{
  "email": "citizen@maturcapil.id",
  "password": "Password1",
  "portal": "citizen"
}
```

| Field | Tipe | Wajib | Keterangan |
|--------|------|--------|------------|
| `email` | string | ✓ | Email terdaftar |
| `password` | string | ✓ | — |
| `portal` | string | ✓ | `citizen` → role `Masyarakat`; `admin` → `Admin` / `Super Admin` |

**Response `200`:**

```json
{
  "success": true,
  "message": "Login berhasil",
  "data": {
    "access_token": "eyJ...",
    "refresh_token": "...",
    "token_type": "Bearer",
    "expires_in": 3600,
    "user": {
      "id": "usr-...",
      "name": "Budi Santoso",
      "email": "citizen@maturcapil.id",
      "role": "Masyarakat",
      "nik": "3374012345678901",
      "status": "ACTIVE",
      "email_verified": true,
      "email_verified_at": "2026-05-01T08:00:00Z",
      "permissions": [],
      "created_at": "2026-05-01T08:00:00Z",
      "deleted_at": null,
      "deleted_by": null
    }
  }
}
```

**Error:**

| HTTP | `message` (contoh) |
|------|---------------------|
| 401 | Email atau password salah |
| 403 | Akun dinonaktifkan / Akun ditangguhkan |
| 403 | Gunakan Portal Admin / Gunakan Portal Warga |
| 429 | Terlalu banyak percobaan login |

---

### 3.2 Logout

`POST /auth/logout`

| | |
|--|--|
| **Auth** | ✓ Bearer |

**Request body:** kosong `{}` atau tanpa body

**Response `200`:**

```json
{
  "success": true,
  "message": "Logout berhasil"
}
```

**Side effect:** refresh token user di-revoke di server.

---

### 3.3 Profil dari token

`GET /auth/me`

| | |
|--|--|
| **Auth** | ✓ Bearer |

**Response `200`:**

```json
{
  "success": true,
  "data": {
    "id": "usr-...",
    "name": "Budi Santoso",
    "email": "citizen@maturcapil.id",
    "role": "Masyarakat",
    "nik": "3374012345678901",
    "status": "ACTIVE",
    "email_verified": true,
    "email_verified_at": "2026-05-01T08:00:00Z",
    "permissions": [],
    "created_at": "2026-05-01T08:00:00Z",
    "deleted_at": null,
    "deleted_by": null
  }
}
```

---

### 3.4 Registrasi warga (langkah 1 — kirim OTP)

`POST /auth/register`

| | |
|--|--|
| **Auth** | Tidak |

**Request body:**

```json
{
  "name": "Nama Lengkap",
  "nik": "3374012345678901",
  "email": "baru@email.com",
  "password": "Password1",
  "password_confirmation": "Password1"
}
```

**Response `200`:**

```json
{
  "success": true,
  "message": "Kode OTP telah dikirim ke email Anda. Berlaku 5 menit.",
  "data": {
    "email": "baru@email.com"
  }
}
```

**Error:** duplikat email/NIK, validasi password/NIK, password tidak cocok.

> **Dev:** jika SMTP tidak dikonfigurasi, OTP dicetak di log terminal backend.

---

### 3.5 Registrasi warga (langkah 2 — verifikasi OTP)

`POST /auth/register/verify-otp`

| | |
|--|--|
| **Auth** | Tidak |

**Request body:**

```json
{
  "email": "baru@email.com",
  "otp": "123456"
}
```

**Response `200`:**

```json
{
  "success": true,
  "data": {
    "access_token": "eyJ...",
    "refresh_token": "...",
    "token_type": "Bearer",
    "expires_in": 3600,
    "user": {
      "id": "usr-...",
      "role": "Masyarakat",
      "email_verified": true,
      "email_verified_at": "2026-05-23T10:00:00Z"
    }
  }
}
```

Akun langsung login (token dikembalikan).

---

### 3.6 Kirim ulang OTP registrasi

`POST /auth/register/resend-otp`

| | |
|--|--|
| **Auth** | Tidak |

**Request body:**

```json
{
  "email": "baru@email.com"
}
```

**Response `200`:**

```json
{
  "success": true,
  "message": "OTP baru telah dikirim."
}
```

**Error:** sesi registrasi tidak ada, OTP expired, batas 3x, cooldown 60 detik.

---

### 3.7 Kirim OTP verifikasi email (user sudah login)

`POST /auth/email/send-otp`

| | |
|--|--|
| **Auth** | ✓ Bearer |
| **Role** | `Masyarakat` |

**Request body:** kosong

**Response `200`:**

```json
{
  "success": true,
  "message": "OTP dikirim ke email Anda."
}
```

---

### 3.8 Kirim ulang OTP email

`POST /auth/email/resend-otp`

| | |
|--|--|
| **Auth** | ✓ Bearer |
| **Role** | `Masyarakat` |

**Request body:** kosong

**Response:** sama seperti resend registrasi.

---

### 3.9 Verifikasi email (OTP)

`POST /auth/email/verify`

| | |
|--|--|
| **Auth** | ✓ Bearer |
| **Role** | `Masyarakat` |

**Request body:**

```json
{
  "otp": "123456"
}
```

**Response `200`:**

```json
{
  "success": true,
  "message": "Email terverifikasi",
  "data": {
    "user": {
      "id": "usr-...",
      "email_verified": true,
      "email_verified_at": "2026-05-23T10:00:00Z"
    }
  }
}
```

---

## 4. Pengaduan (Complaints)

Prefix: `/complaints`

---

### 4.1 Daftar laporan

`GET /complaints`

| | |
|--|--|
| **Auth** | ✓ Bearer |

**Query parameters:**

| Param | Tipe | Keterangan |
|--------|------|------------|
| `user_id` | string | Filter per warga (admin) |
| `status` | string | `Menunggu Verifikasi`, `Diproses`, dll. |
| `category_id` | string | ID kategori |
| `priority` | string | `Tinggi` / `Sedang` / `Rendah` |
| `search` | string | Judul, ticket, deskripsi, nama pelapor |
| `page` | int | Default `1` |
| `per_page` | int | Default `20`, maks `100` |

**Perilaku:**

- **Masyarakat:** hanya laporan milik sendiri
- **Admin / Super Admin:** semua laporan

**Response `200`:**

```json
{
  "success": true,
  "data": {
    "items": [
      {
        "id": "comp-...",
        "ticket_number": "TKT-2026-0001",
        "user_id": "usr-...",
        "user_name": "Budi Santoso",
        "title": "Judul",
        "description": "Deskripsi",
        "category_id": "ktp",
        "status": "Menunggu Verifikasi",
        "priority": "Sedang",
        "latitude": -6.9822,
        "longitude": 110.4091,
        "address": "Kota Semarang",
        "created_at": "2026-05-15T08:12:00Z",
        "photos": ["http://localhost:3000/uploads/complaints/x.jpg"],
        "evidence_after_photos": [],
        "resolution_note": "",
        "resolved_at": null
      }
    ],
    "meta": {
      "page": 1,
      "per_page": 20,
      "total": 4
    }
  }
}
```

---

### 4.2 Detail laporan

`GET /complaints/{id}`

| | |
|--|--|
| **Auth** | ✓ Bearer |

**Response `200`:** objek `Complaint` lengkap (satu objek di `data`).

**Error `403`:** warga mengakses laporan orang lain.

---

### 4.3 Buat laporan

`POST /complaints`

| | |
|--|--|
| **Auth** | ✓ Bearer |
| **Role** | `Masyarakat` |

**Opsi A — JSON** (`Content-Type: application/json`):

```json
{
  "title": "Judul aduan",
  "description": "Deskripsi minimal 10 karakter",
  "category_id": "ktp",
  "priority": "Sedang",
  "latitude": -6.9822,
  "longitude": 110.4091,
  "address": "Jl. Contoh, Semarang",
  "photos": ["http://localhost:3000/uploads/complaints/sudah-upload.jpg"]
}
```

**Opsi B — Multipart** (`Content-Type: multipart/form-data`):

| Field | Tipe | Wajib |
|--------|------|--------|
| `title` | string | ✓ |
| `description` | string | ✓ |
| `category_id` | string | ✓ |
| `priority` | string | default `Sedang` |
| `latitude` | number/string | ✓ |
| `longitude` | number/string | ✓ |
| `address` | string | ✓ |
| `photos[]` | file | opsional, maks 3 |

**Response `201`:**

```json
{
  "success": true,
  "message": "Aduan berhasil dikirim",
  "data": {
    "id": "comp-...",
    "ticket_number": "TKT-2026-0005",
    "status": "Menunggu Verifikasi",
    "created_at": "2026-05-23T10:00:00Z"
  }
}
```

**Error `403` + `needs_email_verification`:** warga belum verifikasi email dan sudah punya ≥1 laporan.

**Side effect:** status log awal dibuat otomatis.

---

### 4.4 Ubah status (verifikasi / tolak)

`PATCH /complaints/{id}/status`

| | |
|--|--|
| **Auth** | ✓ Bearer |
| **Permission** | Lihat tabel di bawah |

**Request body:**

```json
{
  "status": "Diproses",
  "note": "Laporan diverifikasi dan diteruskan ke operator."
}
```

| `status` | Permission |
|----------|------------|
| `Diproses` | `complaint.verify` |
| `Ditolak` | `complaint.reject` |
| Lainnya | `complaint.verify` |

**Response `200`:**

```json
{
  "success": true,
  "data": {
    "id": "comp-...",
    "ticket_number": "TKT-2026-0001",
    "status": "Diproses"
  }
}
```

(`data` berisi objek complaint lengkap.)

**Side effect:** status log + audit (`VERIFY_COMPLAINT` / `REJECT_COMPLAINT` / `UPDATE_STATUS`).

---

### 4.5 Tutup laporan (selesai)

`POST /complaints/{id}/close`

| | |
|--|--|
| **Auth** | ✓ Bearer |
| **Permission** | `complaint.close` |

**Opsi A — JSON:**

```json
{
  "resolution_note": "KTP telah dicetak dan diserahkan.",
  "evidence_after_photos": [
    "http://localhost:3000/uploads/evidence_after/after1.jpg"
  ]
}
```

**Opsi B — Multipart:**

| Field | Tipe |
|--------|------|
| `resolution_note` | string |
| `evidence[]` / `evidence_after[]` | file (foto bukti perbaikan) |

**Response `200`:**

```json
{
  "success": true,
  "data": {
    "id": "comp-...",
    "status": "Selesai",
    "resolution_note": "KTP telah dicetak dan diserahkan.",
    "resolved_at": "2026-05-23T12:00:00Z",
    "evidence_after_photos": ["http://localhost:3000/uploads/evidence_after/x.jpg"]
  }
}
```

---

### 4.6 Timeline status

`GET /complaints/{id}/status-logs`

| | |
|--|--|
| **Auth** | ✓ Bearer |

**Response `200`:**

```json
{
  "success": true,
  "data": [
    {
      "id": "log-...",
      "complaint_id": "comp-...",
      "status": "Menunggu Verifikasi",
      "note": "Aduan berhasil diajukan oleh masyarakat.",
      "changed_by": "Budi Santoso",
      "created_at": "2026-05-15T08:12:00Z"
    }
  ]
}
```

---

### 4.7 Daftar chat

`GET /complaints/{id}/chats`

| | |
|--|--|
| **Auth** | ✓ Bearer |

**Response `200`:**

```json
{
  "success": true,
  "data": [
    {
      "id": "chat-...",
      "complaint_id": "comp-...",
      "sender_id": "usr-...",
      "sender_name": "Budi Santoso",
      "message": "Pesan",
      "created_at": "2026-05-15T08:15:00Z"
    }
  ]
}
```

> Chat saat ini **REST polling** (belum WebSocket).

---

### 4.8 Kirim chat

`POST /complaints/{id}/chats`

| | |
|--|--|
| **Auth** | ✓ Bearer |

**Request body:**

```json
{
  "message": "Isi pesan chat"
}
```

**Response `201`:**

```json
{
  "success": true,
  "data": {
    "id": "chat-...",
    "complaint_id": "comp-...",
    "sender_id": "usr-...",
    "sender_name": "Siti Aminah",
    "message": "Isi pesan chat",
    "created_at": "2026-05-15T08:16:00Z"
  }
}
```

---

## 5. Kategori

Prefix: `/categories`

---

### 5.1 Daftar kategori

`GET /categories`

| | |
|--|--|
| **Auth** | ✓ Bearer |

**Query:**

| Param | Default | Keterangan |
|--------|---------|------------|
| `include_inactive` | `false` | Admin: tampilkan nonaktif |
| `active_only` | `false` | Paksa hanya aktif |

**Perilaku:** warga (`Masyarakat`) otomatis hanya kategori `is_active=true`.

**Response `200`:**

```json
{
  "success": true,
  "data": [
    {
      "id": "ktp",
      "name": "KTP-el",
      "code": "KTP",
      "description": "Pengaduan KTP elektronik",
      "is_active": true,
      "deleted_at": null,
      "deleted_by": null
    }
  ]
}
```

---

### 5.2 Tambah kategori

`POST /categories`

| | |
|--|--|
| **Auth** | ✓ |
| **Permission** | `category.manage` |

**Request body:**

```json
{
  "name": "KTP-el",
  "code": "KTP",
  "description": "Pengaduan KTP elektronik"
}
```

**Response `201`:**

```json
{
  "success": true,
  "data": {
    "id": "ktp",
    "name": "KTP-el",
    "code": "KTP",
    "is_active": true
  }
}
```

---

### 5.3 Ubah kategori

`PATCH /categories/{id}`

| | |
|--|--|
| **Permission** | `category.manage` |

**Request body (partial):**

```json
{
  "name": "Nama baru",
  "code": "KODE",
  "description": "...",
  "is_active": true
}
```

**Response `200`:** objek kategori terbarui di `data`.

---

### 5.4 Hapus kategori (soft delete)

`DELETE /categories/{id}`

| | |
|--|--|
| **Permission** | `category.manage` |

**Response `200`:**

```json
{
  "success": true,
  "message": "Kategori dinonaktifkan"
}
```

Set `is_active: false`, `deleted_at`, `deleted_by`.

---

## 6. Manajemen user

Prefix: `/users`

---

### 6.1 Daftar user

`GET /users`

| | |
|--|--|
| **Permission** | `user.view` |

**Query:** `role`, `search`, `status`, `page`, `per_page`

| `role` | Filter |
|--------|--------|
| `Masyarakat` | Warga saja |
| `Admin` | Admin + Super Admin |

**Response `200`:**

```json
{
  "success": true,
  "data": {
    "items": [
      {
        "id": "usr-...",
        "name": "Budi Santoso",
        "email": "fa******@gmail.com",
        "role": "Masyarakat",
        "nik": "3374********8901",
        "status": "ACTIVE",
        "email_verified": true,
        "created_at": "2026-05-01T08:00:00Z"
      }
    ],
    "meta": { "page": 1, "per_page": 20, "total": 10 }
  }
}
```

---

### 6.2 Detail user

`GET /users/{id}`

| | |
|--|--|
| **Permission** | `user.view` |

**Response `200`:** objek user di `data` (tanpa field password).

---

### 6.3 Tambah warga (oleh admin)

`POST /users/citizens`

| | |
|--|--|
| **Permission** | `user.create` |

**Request body:**

```json
{
  "name": "Nama Warga",
  "email": "warga@email.com",
  "nik": "3374012345678901",
  "password": "Password1"
}
```

**Response `201`:**

```json
{
  "success": true,
  "data": {
    "id": "usr-...",
    "role": "Masyarakat",
    "email_verified": false,
    "status": "ACTIVE"
  }
}
```

---

### 6.4 Tambah admin

`POST /users/admins`

| | |
|--|--|
| **Permission** | `user.create` |

**Request body:**

```json
{
  "name": "Admin Baru",
  "email": "admin@email.com",
  "password": "Password1",
  "nik": "3374023456789012",
  "permissions": [
    "dashboard.view",
    "complaint.verify",
    "complaint.reject",
    "complaint.close"
  ]
}
```

**Response `201`:** objek user Admin + `permissions[]`.

---

### 6.5 Ubah user

`PATCH /users/{id}`

| | |
|--|--|
| **Permission** | `user.update` |

**Request body (partial):**

```json
{
  "name": "Nama Baru",
  "email": "email@baru.com",
  "nik": "3374012345678901",
  "status": "ACTIVE"
}
```

**Response `200`:** user terbarui.

---

### 6.6 Nonaktifkan user

`DELETE /users/{id}`

| | |
|--|--|
| **Permission** | `user.delete` |

**Response `200`:**

```json
{
  "success": true,
  "message": "Akun dinonaktifkan"
}
```

Soft delete: `status=INACTIVE`, `deleted_at` terisi.

---

### 6.7 Reset password

`POST /users/{id}/reset-password`

| | |
|--|--|
| **Permission** | `user.update` |

**Request body:**

```json
{
  "password": "PasswordBaru1",
  "force_reset": true
}
```

**Response `200`:**

```json
{
  "success": true,
  "message": "Password direset. Email notifikasi terkirim."
}
```

---

### 6.8 Atur permission admin

`PUT /users/{id}/permissions`

| | |
|--|--|
| **Role** | **Super Admin** saja |

**Request body:**

```json
{
  "permissions": [
    "dashboard.view",
    "complaint.verify",
    "user.view"
  ]
}
```

**Response `200`:**

```json
{
  "success": true,
  "data": {
    "id": "usr-...",
    "role": "Admin",
    "permissions": ["dashboard.view", "complaint.verify", "user.view"]
  }
}
```

---

## 7. Audit log

Prefix: `/audit-logs`

---

### 7.1 Daftar audit log

`GET /audit-logs`

| | |
|--|--|
| **Permission** | `auditlog.view` |

**Query:** `action`, `search`, `date_from`, `date_to`, `page`, `per_page`

**Response `200`:**

```json
{
  "success": true,
  "data": {
    "items": [
      {
        "id": "audit-...",
        "user_id": "usr-...",
        "user_name": "Siti Aminah",
        "action": "VERIFY_COMPLAINT",
        "table_name": "complaints",
        "record_id": "comp-...",
        "detail": "Laporan diverifikasi",
        "ip_address": "127.0.0.1",
        "created_at": "2026-05-15T08:20:00Z"
      }
    ],
    "meta": { "page": 1, "per_page": 20, "total": 50 }
  }
}
```

Log **immutable** — tidak ada endpoint update/delete.

---

### 7.2 Export CSV

`GET /audit-logs/export`

| | |
|--|--|
| **Permission** | `auditlog.view` |
| **Response** | `Content-Type: text/csv` (file download) |

**Query:** sama seperti list (`action`, dll.)

**Header CSV:**  
`ID Log, Petugas, Aksi, Tabel, ID Record, IP, Keterangan, Waktu`

---

## 8. Ringkasan endpoint

| # | Method | Path | Auth | Permission / Role |
|---|--------|------|:----:|-------------------|
| 1 | POST | `/auth/login` | — | — |
| 2 | POST | `/auth/logout` | ✓ | — |
| 3 | GET | `/auth/me` | ✓ | — |
| 4 | POST | `/auth/register` | — | — |
| 5 | POST | `/auth/register/verify-otp` | — | — |
| 6 | POST | `/auth/register/resend-otp` | — | — |
| 7 | POST | `/auth/email/send-otp` | ✓ | Masyarakat |
| 8 | POST | `/auth/email/resend-otp` | ✓ | Masyarakat |
| 9 | POST | `/auth/email/verify` | ✓ | Masyarakat |
| 10 | GET | `/complaints` | ✓ | scope by role |
| 11 | GET | `/complaints/{id}` | ✓ | owner / admin |
| 12 | POST | `/complaints` | ✓ | Masyarakat |
| 13 | PATCH | `/complaints/{id}/status` | ✓ | verify / reject |
| 14 | POST | `/complaints/{id}/close` | ✓ | `complaint.close` |
| 15 | GET | `/complaints/{id}/status-logs` | ✓ | — |
| 16 | GET | `/complaints/{id}/chats` | ✓ | — |
| 17 | POST | `/complaints/{id}/chats` | ✓ | — |
| 18 | GET | `/categories` | ✓ | — |
| 19 | POST | `/categories` | ✓ | `category.manage` |
| 20 | PATCH | `/categories/{id}` | ✓ | `category.manage` |
| 21 | DELETE | `/categories/{id}` | ✓ | `category.manage` |
| 22 | GET | `/users` | ✓ | `user.view` |
| 23 | GET | `/users/{id}` | ✓ | `user.view` |
| 24 | POST | `/users/citizens` | ✓ | `user.create` |
| 25 | POST | `/users/admins` | ✓ | `user.create` |
| 26 | PATCH | `/users/{id}` | ✓ | `user.update` |
| 27 | DELETE | `/users/{id}` | ✓ | `user.delete` |
| 28 | POST | `/users/{id}/reset-password` | ✓ | `user.update` |
| 29 | PUT | `/users/{id}/permissions` | ✓ | Super Admin |
| 30 | GET | `/audit-logs` | ✓ | `auditlog.view` |
| 31 | GET | `/audit-logs/export` | ✓ | `auditlog.view` |

### Endpoint belum tersedia (rencana)

| Method | Path | Keterangan |
|--------|------|------------|
| POST | `/auth/refresh` | Refresh access token |
| POST | `/auth/forgot-password` | Lupa password |
| GET | `/dashboard/stats` | Statistik dashboard admin |
| GET | `/complaints/export` | Export Excel/CSV aduan |

---

## 9. Contoh integrasi FE

### 9.1 Client dasar (fetch)

```javascript
const API_BASE = import.meta.env.VITE_API_BASE_URL; // http://localhost:3000/api/v1

async function api(path, { method = 'GET', body, token } = {}) {
  const headers = { Accept: 'application/json' };
  if (token) headers.Authorization = `Bearer ${token}`;
  if (body) headers['Content-Type'] = 'application/json';

  const res = await fetch(`${API_BASE}${path}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });

  const json = await res.json();
  if (!res.ok || json.success === false) {
    const err = new Error(json.message || 'Request gagal');
    err.status = res.status;
    err.errors = json.errors;
    err.needsEmailVerification = json.needs_email_verification;
    throw err;
  }
  return json;
}
```

### 9.2 Login & simpan token

```javascript
const { data } = await api('/auth/login', {
  method: 'POST',
  body: { email, password, portal: 'citizen' },
});
localStorage.setItem('access_token', data.access_token);
localStorage.setItem('refresh_token', data.refresh_token);
```

### 9.3 Buat laporan dengan foto

```javascript
const fd = new FormData();
fd.append('title', title);
fd.append('description', description);
fd.append('category_id', categoryId);
fd.append('priority', 'Sedang');
fd.append('latitude', String(lat));
fd.append('longitude', String(lng));
fd.append('address', address);
photos.forEach((file, i) => fd.append('photos[]', file, `photo-${i}.jpg`));

const res = await fetch(`${API_BASE}/complaints`, {
  method: 'POST',
  headers: { Authorization: `Bearer ${token}` },
  body: fd,
});
const json = await res.json();
```

### 9.4 Akun demo (setelah seed)

| Email | Password | Portal |
|-------|----------|--------|
| `citizen@maturcapil.id` | `Password1` | `citizen` |
| `admin@maturcapil.id` | `Password1` | `admin` |
| `superadmin@maturcapil.id` | `Password1` | `admin` |

### 9.5 Mapping ke service FE yang ada

Layer service frontend (`MaturCapilFrontend/src/services/`) sudah diselaraskan dengan kontrak ini:

| Service | File |
|---------|------|
| Auth | `authService.js` |
| Complaints | `complaintService.js` |
| Categories | `categoryService.js` |
| Users | `userService.js` |
| Audit | `auditService.js` |
| HTTP client | `apiClient.js` |
| Mapper | `mappers.js` |

Set `VITE_USE_MOCK_API=false` dan `VITE_API_BASE_URL=http://localhost:3000/api/v1` untuk menghubungkan ke backend ini.

---

## Lampiran: Kode HTTP

| Kode | Penggunaan |
|------|------------|
| 200 | Sukses (GET, PATCH, POST non-create) |
| 201 | Created (register complaint, chat, user) |
| 400 | Validasi bisnis / OTP salah |
| 401 | Token invalid / login gagal |
| 403 | Forbidden / permission / portal salah |
| 404 | Resource tidak ditemukan |
| 422 | Validasi request body (Pydantic) |
| 429 | Rate limit (login, OTP resend) |
