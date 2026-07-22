# database.py

import httpx
from datetime import datetime
from config import settings 

if not settings.FIREBASE_API_KEY or not settings.FIREBASE_PROJECT_ID:
    raise RuntimeError("🚨 KESALAHAN KRITIKAL: Variabel Firebase di .env belum diisi!")

# Menggunakan variabel dari settings terpusat
BASE_URL = settings.FIREBASE_BASE_URL

register_url = f"https://identitytoolkit.googleapis.com/v1/accounts:signUp?key={settings.FIREBASE_API_KEY}"
email_url = f"https://identitytoolkit.googleapis.com/v1/accounts:sendOobCode?key={settings.FIREBASE_API_KEY}"
login_url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={settings.FIREBASE_API_KEY}"

class DatabaseManager:
    @staticmethod
    async def save_user_profile(uid: str, user_data: dict):
        """Menyimpan data profil user baru Secara Async"""
        async with httpx.AsyncClient() as client:
            await client.put(f"{BASE_URL}/users/{uid}.json", json=user_data)

    @staticmethod
    async def get_user_profile(uid: str, email: str):
        """Mengambil data profil lengkap user untuk login Secara Async"""
        profil_lengkap = {
            "success": True, "uid": uid, "email": email, "is_premium": False,
            "whatsapp": "", "nama_lengkap": "", "asal_daerah": "", "nama_bisnis": "", "bidang_bisnis": "", "created_at":""
        }
        try:
            async with httpx.AsyncClient() as client:
                db_response = await client.get(f"{BASE_URL}/users/{uid}.json", timeout=5.0)
                
            if db_response.status_code == 200 and db_response.json():
                user_profile = db_response.json()
                data_akun = user_profile.get("akun", {})
                data_identitas = user_profile.get("identitas", {})
                
                profil_lengkap.update({
                    "is_premium": data_akun.get("is_premium", False),
                    "whatsapp": data_akun.get("whatsapp", ""),
                    "nama_lengkap": data_identitas.get("nama_lengkap", ""),
                    "asal_daerah": data_identitas.get("asal_daerah", ""),
                    "nama_bisnis": data_identitas.get("nama_bisnis", ""),
                    "bidang_bisnis": data_identitas.get("bidang_bisnis", ""),
                    "created_at": user_profile.get("created_at", "")
                })
        except Exception:
            pass
        return profil_lengkap

    @staticmethod
    async def get_katalog_materi():
        try:
            async with httpx.AsyncClient() as client:
                r = await client.get(f"{BASE_URL}/materi.json", timeout=5.0)
            return list(r.json().values()) if r.json() else []
        except Exception:
            return []
    
    @staticmethod
    async def get_app_config():
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{BASE_URL}/config.json", timeout=5.0)
            if response.status_code == 200 and response.json():
                return response.json()
            return {"premium_price": 150000, "whatsapp_admin": "62895614609191"}
        except Exception:
            return {"premium_price": 150000, "whatsapp_admin": "62895614609191"}
        
    @staticmethod
    async def update_user_to_premium(uid: str):
        try:
            async with httpx.AsyncClient() as client:
                response = await client.patch(f"{BASE_URL}/users/{uid}/akun.json", json={"is_premium": True}, timeout=5.0)
            return response.status_code == 200
        except Exception:
            return False

    @staticmethod
    async def save_pending_transaction(order_id: str, amount: int, email: str, uid: str):
        try:
            waktu_sekarang = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            payload = {"amount": amount, "status": "pending", "email": email, "uid": uid, "created_at": waktu_sekarang}
            async with httpx.AsyncClient() as client:
                response = await client.put(f"{BASE_URL}/transactions/{order_id}.json", json=payload, timeout=5.0)
            return response.status_code == 200
        except Exception:
            return False

    @staticmethod
    async def get_transaction_by_id(order_id: str):
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{BASE_URL}/transactions/{order_id}.json", timeout=5.0)
            return response.json() if response.status_code == 200 else None
        except Exception:
            return None

    @staticmethod
    async def update_transaction_status(order_id: str, status: str):
        try:
            async with httpx.AsyncClient() as client:
                response = await client.patch(f"{BASE_URL}/transactions/{order_id}.json", json={"status": status}, timeout=5.0)
            return response.status_code == 200
        except Exception:
            return False


# =====================================================================
# 🛠️ FUNGSI KHUSUS ADMIN (SINKRON DENGAN WEB DASHBOARD)
# =====================================================================
    @staticmethod
    async def get_all_users():
        try:
            async with httpx.AsyncClient() as client:
                r = await client.get(f"{BASE_URL}/users.json", timeout=5.0)
            return r.json() if r.json() else {}
        except Exception:
            return {}

    @staticmethod
    async def get_all_transactions():
        try:
            async with httpx.AsyncClient() as client:
                r = await client.get(f"{BASE_URL}/transactions.json", timeout=5.0)
            return r.json() if r.json() else {}
        except Exception:
            return {}
    
    @staticmethod
    async def add_katalog_materi(materi_id: str, data_materi: dict):
        """ADMIN: Menambahkan materi pelajaran baru ke katalog Firebase"""
        try:
            data_materi["materi_id"] = materi_id
            data_materi["created_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            async with httpx.AsyncClient() as client:
                response = await client.put(f"{BASE_URL}/materi/{materi_id}.json", json=data_materi, timeout=5.0)
            return response.status_code == 200
        except Exception:
            return False

    @staticmethod
    async def update_katalog_materi(materi_id: str, data_materi_baru: dict):
        """ADMIN: Mengubah/mengedit isi materi pelajaran yang sudah ada"""
        try:
            data_materi_baru["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            async with httpx.AsyncClient() as client:
                response = await client.patch(f"{BASE_URL}/materi/{materi_id}.json", json=data_materi_baru, timeout=5.0)
            return response.status_code == 200
        except Exception:
            return False

    @staticmethod
    async def delete_katalog_materi(materi_id: str):
        """ADMIN: Menghapus materi pelajaran dari katalog berdasarkan ID"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.delete(f"{BASE_URL}/materi/{materi_id}.json", timeout=5.0)
            return response.status_code == 200
        except Exception:
            return False
        
    @staticmethod
    async def update_app_config(premium_price: int, whatsapp_admin: str):
        """ADMIN: Memperbarui konfigurasi harga premium dan nomor WA admin di Firebase"""
        try:
            payload = {
                "premium_price": premium_price, 
                "whatsapp_admin": whatsapp_admin
            }
            async with httpx.AsyncClient() as client:
                # Menggunakan PUT untuk menimpa konfigurasi terpusat di /config.json
                response = await client.put(f"{BASE_URL}/config.json", json=payload, timeout=5.0)
            return response.status_code == 200
        except Exception:
            return False

    @staticmethod
    async def ping_firebase():
        """
        Melakukan ping ringan ke Firebase untuk memeriksa readiness server.
        Menggunakan shallow=true agar Firebase hanya mengembalikan struktur kunci utama 
        tanpa mengunduh seluruh data (sangat cepat dan hemat bandwidth).
        """
        try:
            async with httpx.AsyncClient() as client:
                # Timeout ketat 2 detik agar load balancer tidak menunggu terlalu lama
                response = await client.get(f"{BASE_URL}/.json?shallow=true", timeout=2.0)
            return response.status_code == 200
        except Exception:
            return False

