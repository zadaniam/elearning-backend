# auth_service.py

import httpx
from datetime import datetime
from database import DatabaseManager, register_url, email_url, login_url

class AuthService:
    @staticmethod
    async def register_user(email, password, whatsapp, nama, asal, nama_bisnis, bidang_bisnis):
        """Khusus menangani pendaftaran akun baru ke Firebase Auth"""
        try:
            print("--- AUTH: Sedang mendaftarkan akun baru ke Firebase Auth... ---")
            payload = {"email": email, "password": password, "returnSecureToken": True}
            
            async with httpx.AsyncClient() as client:
                r = await client.post(register_url, json=payload)
                res_data = r.json()
            
            if "error" in res_data:
                return {"success": False, "error": res_data["error"]["message"]}
                
            uid = res_data['localId']
            id_token = res_data['idToken']

            # Alur Otomatisasi Email Verifikasi
            try:
                async with httpx.AsyncClient() as client:
                    await client.post(email_url, json={"requestType": "VERIFY_EMAIL", "idToken": id_token}, timeout=5.0)
            except Exception as email_err:
                print(f"--- AUTH WARNING: Email gagal terkirim = {email_err} ---")


            user_data = {
                "akun": {"email": email, "whatsapp": whatsapp, "is_premium": False},
                "identitas": {"nama_lengkap": nama, "asal_daerah": asal, "nama_bisnis": nama_bisnis, "bidang_bisnis": bidang_bisnis},
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            await DatabaseManager.save_user_profile(uid, user_data)
            return {"success": True, "uid": uid, "is_premium": False}
        except Exception as e:
            return {"success": False, "error": str(e)}

    @staticmethod
    async def login_user(email, password):
        """Khusus menangani proses masuk akun (Login)"""
        try:
            async with httpx.AsyncClient() as client:
                r = await client.post(login_url, json={"email": email, "password": password, "returnSecureToken": True}, timeout=5.0)
                res_data = r.json()
            
            if "error" in res_data:
                return {"success": False, "error": res_data["error"]["message"]}
                
            uid = res_data['localId']
            
            return await DatabaseManager.get_user_profile(uid, email)
        except Exception as e:
            return {"success": False, "error": str(e)}
