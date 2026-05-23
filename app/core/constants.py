ROLES = ("Masyarakat", "Admin", "Super Admin")
CITIZEN_ROLE = "Masyarakat"
ADMIN_ROLES = ("Admin", "Super Admin")

ACCOUNT_STATUSES = ("ACTIVE", "INACTIVE", "SUSPENDED")

COMPLAINT_STATUSES = ("Menunggu Verifikasi", "Diproses", "Selesai", "Ditolak")
PRIORITIES = ("Tinggi", "Sedang", "Rendah")

ALL_PERMISSION_CODES = [
    "dashboard.view",
    "complaint.verify",
    "complaint.reject",
    "complaint.close",
    "complaint.export",
    "user.view",
    "user.create",
    "user.update",
    "user.delete",
    "category.manage",
    "auditlog.view",
]

# Bounding box Kota Semarang (approximate)
SEMARANG_LAT_MIN = -7.15
SEMARANG_LAT_MAX = -6.85
SEMARANG_LNG_MIN = 110.25
SEMARANG_LNG_MAX = 110.55

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}
ALLOWED_IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp"}
