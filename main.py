# backend/main.py

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

from services.auth_service import AuthService
from services.gemini_service import GeminiService
from services.payment_service import PaymentService
from database import DatabaseManager

from pydantic import BaseModel, EmailStr


app = FastAPI(title="E-Learning Business Backend")
app.add_middleware(ProxyHeadersMiddleware, trusted_hosts="*")


ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:8000",
    "https://bisnisanda.com"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ai_service = GeminiService()
payment_service = PaymentService()

class UserLoginSchema(BaseModel):
    email: EmailStr
    password: str

class UserRegisterSchema(BaseModel):
    email: EmailStr  # Memastikan format email valid secara otomatis
    password: str
    whatsapp: str
    nama: str
    asal: str
    nama_bisnis: str
    bidang_bisnis: str

class PaymentChargeSchema(BaseModel):
    order_id: str
    item_name: str
    user_email: str
    uid: str

@app.post("/api/v1/auth/login")
async def api_login(payload: UserLoginSchema):
    """Mengalihkan fungsi login dari Flet ke FastAPI"""
    email = payload.email
    password = payload.password

    hasil = await AuthService.login_user(email, password)
    
    if not hasil.get("success", True):
        raise HTTPException(status_code=401, detail=hasil.get("error", "Login Gagal"))
    return hasil

@app.post("/api/v1/auth/register")
async def api_register(payload: UserRegisterSchema):
    """Mengalihkan fungsi register dari Flet ke FastAPI"""
    
    hasil = await AuthService.register_user(
        payload.email, payload.password, payload.whatsapp,
        payload.nama, payload.asal, payload.nama_bisnis, payload.bidang_bisnis
    )

    if not hasil.get("success"):
        raise HTTPException(status_code=400, detail=hasil.get("error", "Pendaftaran Gagal"))
    return hasil

@app.get("/api/v1/materi/katalog")
async def api_get_katalog():
    """Endpoint Resmi: Mengambil data materi dari Firebase melalui server yang aman"""
    try:
        materi = await DatabaseManager.get_katalog_materi()
        return {"status": "success", "data": materi}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gagal memuat materi: {str(e)}")

@app.post("/api/v1/chat/stream")
async def api_chat_stream(payload: dict):
    """
    Endpoint Resmi: Menerima prompt dari Flet, memanggil Gemini via SDK baru,
    lalu mencicil potongan teksnya (streaming) langsung ke aplikasi mobile.
    """
    user_prompt = payload.get("prompt", "")
    if not user_prompt:
        raise HTTPException(status_code=400, detail="Prompt tidak boleh kosong")
    
    def generate_stream():
        stream_response = ai_service.tanya_ai_stream(user_prompt)
        
        if stream_response is not None:
            for chunk in stream_response:
                if chunk.text:
                    yield chunk.text
        else:
            yield "Gagal mendapatkan respons dari AI."

    return StreamingResponse(generate_stream(), media_type="text/plain")

@app.get("/api/v1/payment/config")
async def get_payment_config():
    """Endpoint Resmi: Mengambil konfigurasi harga terbaru dari DATABASE"""

    current_config = await DatabaseManager.get_app_config()
    price = current_config.get("premium_price", 150000)
    whatsapp = current_config.get("whatsapp_admin", "62895614609191")
    
    return {
        "status": "success",
        "amount": price,
        "formatted_amount": f"Rp {price:,}".replace(",", "."),
        "whatsapp_admin": whatsapp
    }

@app.post("/api/v1/payment/charge")
async def create_transaction(payload: PaymentChargeSchema):
    """Endpoint 1: Membuat token pembayaran & mencatat data pending ke Firebase"""
    
    try:
        current_config = await DatabaseManager.get_app_config()
        active_price = current_config.get("premium_price", 150000)
        
        # Panggil modul payment service
        pay_res = payment_service.create_snap_token(payload.order_id, active_price, payload.item_name, payload.user_email)
        
        if not pay_res.get("success"):
            print(f"❌ [FASTAPI DETEKTIF] Midtrans gagal memberi token: {pay_res.get('error')}")
            raise HTTPException(status_code=500, detail=pay_res.get("error"))
        
        # Simpan ke Firebase
        db_success = await DatabaseManager.save_pending_transaction(payload.order_id, active_price, payload.user_email, payload.uid)
        print(f"   Status simpan transaksi ke Firebase: {db_success}")
        
        return {
            "status": "success",
            "token": pay_res['token'],
            "redirect_url": pay_res['redirect_url']
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/payment/webhook")
async def midtrans_webhook(request: Request):
    """Endpoint 2: Webhook otomatis dari Midtrans (Data divalidasi via Firebase)"""
    try:
        notification = await request.json()
        order_id = notification.get('order_id')
        transaction_status = notification.get('transaction_status')
        fraud_status = notification.get('fraud_status')
        
        print(f"\n🔔 🕵️‍♂️ DETEKTIF WEBHOOK: Masuk Order ID : {order_id} | Status: {transaction_status}")
        
        tx_data = await DatabaseManager.get_transaction_by_id(order_id)
        
        if tx_data:
            target_status = "pending"

            if transaction_status == 'capture':
                target_status = 'challenge' if fraud_status == 'challenge' else 'success'
            elif transaction_status == 'settlement':
                target_status = 'success'
            elif transaction_status in ['cancel', 'deny', 'expire']:
                target_status = 'failed'
            elif transaction_status == 'pending':
                target_status = 'pending'

            await DatabaseManager.update_transaction_status(order_id, target_status)
                
            if target_status == 'success':
                target_uid = tx_data.get('uid')
                if target_uid:
                    is_success = await DatabaseManager.update_user_to_premium(target_uid)
                    if is_success:
                        print(f"🚀 [SERVER] Sukses naik kelas Premium untuk UID: {target_uid}")
                else:
                    print("--- ❌ WEBHOOK ERROR: UID kosong di data transaksi Firebase ---")
                
            return {"status": "OK"}
        else:
            print(f"--- ❌ WEBHOOK WARNING: Order ID {order_id} TIDAK DIKENAL di Firebase! ---")
            raise HTTPException(status_code=404, detail="Order ID tidak ditemukan di database")
            
    except Exception as e:
        print(f"--- 💥 WEBHOOK CRASH: {str(e)} ---")
        raise HTTPException(status_code=400, detail=f"Webhook Error: {str(e)}")

@app.get("/api/v1/payment/status/{order_id}")
async def check_status(order_id: str):
    """Endpoint 3: Dipanggil Flet secara berkala untuk mengecek status di Firebase"""

    tx_data = await DatabaseManager.get_transaction_by_id(order_id)
    if tx_data:
        return {"order_id": order_id, "status": tx_data.get('status', 'pending')}
    raise HTTPException(status_code=404, detail="Transaksi Tidak Ditemukan")



# =====================================================================
# 🛠️ ENDPOINTS KHUSUS ADMIN (FULL HTMX & HTML TEMPLATE - MONOLITH)
# =====================================================================

from fastapi import Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

import os

# Mengunci jalur folder secara dinamis berdasarkan tempat file main.py ini berada
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ADMIN_FOLDER_PATH = os.path.join(BASE_DIR, "templates-admin")

# Mengunci jalur folder 'static' secara dinamis
STATIC_FOLDER_PATH = os.path.join(BASE_DIR, "static")

# Mount folder static agar bisa diakses publik oleh browser
app.mount("/static", StaticFiles(directory=STATIC_FOLDER_PATH), name="static")

# Inisialisasi Jinja2 untuk membaca folder 'templates'
templates = Jinja2Templates(directory=ADMIN_FOLDER_PATH)

@app.get("/admin/dashboard", response_class=HTMLResponse)
async def view_admin_dashboard(request: Request):
    """Menyajikan visual HTML Dashboard secara matang setelah rute lokasi terkunci aman"""
    try:
        # 1. Ambil seluruh data dari Firebase via DatabaseManager Anda
        current_config = await DatabaseManager.get_app_config()
        users_dict = await DatabaseManager.get_all_users()
        txs_dict = await DatabaseManager.get_all_transactions()
        
        # 2. Hitung statistik dasar secara aman dari tipe data dictionary
        total_users = len(users_dict) if isinstance(users_dict, dict) else 0
        total_txs = len(txs_dict) if isinstance(txs_dict, dict) else 0
        
        # 3. Kalkulasi total omset dari transaksi yang sukses
        total_revenue = 0
        if isinstance(txs_dict, dict):
            for tx in txs_dict.values():
                if isinstance(tx, dict) and tx.get("status") == "success":
                    total_revenue += int(tx.get("amount", 0))

        # 4. Susun bungkus data untuk dikirim ke komponen visual Jinja2
        konteks_data = {
            "current_page": "dashboard",
            "current_price": current_config.get("premium_price", 150000) if isinstance(current_config, dict) else 150000,
            "whatsapp_admin": current_config.get("whatsapp_admin", "") if isinstance(current_config, dict) else "",
            "total_users": total_users,
            "total_txs": total_txs,
            "total_revenue": f"Rp {total_revenue:,}".replace(",", ".")
        }
        
        # 5. Render visual menggunakan urutan parameter standar FastAPI terbaru
        return templates.TemplateResponse(request, "dashboard.html", konteks_data)
        
    except Exception as e:
        return HTMLResponse(
            content=f"""
            <div style='padding:25px; font-family:sans-serif; color:#dc2626; background:#fef2f2; border:1px solid #fee2e2; border-radius:16px; max-width:600px; margin:40px auto;'>
                <h3 style='margin-top:0;'>💥 Gagal Memuat Sistem Visual Dashboard</h3>
                <hr style='border-color:#fee2e2;'/>
                <p><b>Pesan Eror:</b> {str(e)}</p>
                <p style='font-size:12px; color:#991b1b;'>Periksa kembali apakah inisialisasi folder 'templates-admin' di bagian atas main.py sudah sesuai.</p>
            </div>
            """, 
            status_code=500
        )

# --- 2. AKSI: UPDATE CONFIG (DIPANGGIL FORM HTMX POST) ---
@app.post("/admin/update-config", response_class=HTMLResponse)
async def admin_update_config(premium_price: int = Form(...), whatsapp_admin: str = Form(...)):
    """Memproses perubahan harga & WA dari form, lalu mengembalikan komponen alert sukses"""
    success = await DatabaseManager.update_app_config(premium_price, whatsapp_admin)
    if success:
        return """
        <div class="p-4 bg-green-50 border border-green-200 text-green-700 rounded-2xl text-sm font-semibold shadow-sm">
            🚀 Berhasil diperbarui! Aplikasi mobile pengguna telah tersinkronisasi.
        </div>
        """
    return '<div class="p-4 bg-red-50 border border-red-200 text-red-700 rounded-2xl text-sm font-semibold shadow-sm">❌ Gagal menyimpan ke Firebase.</div>'


# --- 3. HALAMAN TABEL DATA PENGGUNA (VERSI VISUAL RESMI & AMAN) ---
@app.get("/admin/users", response_class=HTMLResponse)
async def view_admin_users(request: Request):
    """Merender tabel pengguna aplikasi mobile dengan aman dari Firebase"""
    try:
        users = await DatabaseManager.get_all_users()
        formatted_users = []
        
        if isinstance(users, dict):
            for uid, data in users.items():
                if isinstance(data, dict):
                    formatted_users.append({
                        "uid": uid,
                        "email": data.get("akun", {}).get("email", ""),
                        "whatsapp": data.get("akun", {}).get("whatsapp", ""),
                        "is_premium": data.get("akun", {}).get("is_premium", False),
                        "nama_lengkap": data.get("identitas", {}).get("nama_lengkap", "Belum mengisi"),
                        "nama_bisnis": data.get("identitas", {}).get("nama_bisnis", "-"),
                        "bidang_bisnis": data.get("identitas", {}).get("bidang_bisnis", "-"),
                        "created_at": data.get("created_at", "-")
                    })
        
        konteks_data = {
            "current_page": "users",
            "users": formatted_users
        }
        
        # Mengirim parameter request di posisi pertama sesuai standar FastAPI terbaru
        return templates.TemplateResponse(request, "users.html", konteks_data)
        
    except Exception as e:
        return HTMLResponse(content=f"<div style='padding:20px; color:red; font-family:sans-serif;'><b>Gagal Memuat Tabel User:</b> {str(e)}</div>")


# --- 4. HALAMAN MANAJEMEN MATERI (SKEMA BARU: TITLE, URL, DESKRIPSI, KATEGORI, SILABUS, THUMBNAIL) ---
@app.get("/admin/materi", response_class=HTMLResponse)
async def view_admin_materi(request: Request):
    """Menampilkan katalog materi dengan membaca field baru maupun data lama secara aman"""
    try:
        import httpx
        from database import BASE_URL
        
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{BASE_URL}/materi.json", timeout=5.0)
        materi_raw = response.json() if response.status_code == 200 and response.json() else {}
        
        formatted_materi = []
        
        if isinstance(materi_raw, dict):
            for key_id, data in materi_raw.items():
                if isinstance(data, dict):
                    formatted_materi.append({
                        "materi_id": key_id,
                        # Membaca 'title' (format database Anda) dengan fallback 'judul'
                        "title": data.get("title", data.get("judul", "Materi Tanpa Judul")),
                        # Membaca 'url' (format database Anda) dengan fallback 'link_video'
                        "url": data.get("url", data.get("link_video", "")),
                        "deskripsi": data.get("deskripsi", "Belum ada deskripsi."),
                        "kategori": data.get("kategori", "Umum"),
                        "silabus": data.get("silabus", ""),
                        "thumbnail": data.get("thumbnail", ""),
                        "is_premium": data.get("is_premium", data.get("is_free", False))
                    })
                    
        konteks_data = {
            "current_page": "materi",
            "materi_list": formatted_materi
        }
        return templates.TemplateResponse(request, "materi/list.html", konteks_data)
    except Exception as e:
        return HTMLResponse(content=f"<div style='padding:20px; color:red;'><b>Gagal Memuat Katalog:</b> {str(e)}</div>")


@app.post("/admin/materi/add", response_class=HTMLResponse)
async def admin_add_materi_action(
    materi_id: str = Form(...), judul: str = Form(...), 
    deskripsi: str = Form(...), kategori: str = Form(...), 
    link_video: str = Form(...), silabus: str = Form(...),
    thumbnail: str = Form(...), is_premium: str = Form("false")
):
    """Memproses data form baru dan menyimpannya sesuai dengan kata kunci (keys) standar aplikasi mobile"""
    try:
        # Konversi teks "true"/"false" dari HTML select menjadi Boolean murni
        is_premium_boolean = True if is_premium.lower() == "true" else False

        # Menyusun payload rapi menggunakan format 'title' & 'url' agar selaras dengan database mobile Anda
        payload = {
            "title": judul,         # Disimpan sebagai 'title' agar dibaca aplikasi Flet mobile
            "url": link_video,      # Disimpan sebagai 'url' agar dibaca aplikasi Flet mobile
            "is_premium": is_premium_boolean,
            "deskripsi": deskripsi, # Kolom baru pelengkap bisnis Anda
            "kategori": kategori,   # Kolom baru pelengkap bisnis Anda
            "silabus": silabus,     # Kolom baru pelengkap bisnis Anda
            "thumbnail": thumbnail  # Kolom baru pelengkap bisnis Anda
        }
        
        success = await DatabaseManager.add_katalog_materi(materi_id, payload)
        if success:
            return HTMLResponse(content="", headers={"HX-Refresh": "true"})
        return '<div class="p-3 bg-red-50 text-red-700 rounded-xl text-xs font-semibold">❌ Gagal menyimpan ke Firebase.</div>'
    except Exception as e:
        return f'<div class="p-3 bg-red-50 text-red-700 rounded-xl text-xs font-semibold">❌ Eror: {str(e)}</div>'
    

@app.delete("/admin/materi/delete/{materi_id}", response_class=HTMLResponse)
async def admin_delete_materi_action(materi_id: str):
    """Menghapus materi pelajaran secara asinkron (realtime) tanpa reload dari baris tabel"""
    success = await DatabaseManager.delete_katalog_materi(materi_id)
    if success:
        # Mengembalikan string kosong agar HTMX langsung menghilangkan baris tabel tersebut secara halus (swap delete)
        return HTMLResponse(content="")
    return '<script>alert("Gagal menghapus materi");</script>'


app.mount("/static", StaticFiles(directory="static"), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)