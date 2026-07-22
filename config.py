# backend/config.py
import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    # Mengambil nilai ENVIRONMENT dari .env. Jika tidak ditulis, otomatis dianggap "development"
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development").lower()
    
    # Menghasilkan nilai Boolean (True/False) untuk menyetel kondisi sistem
    IS_DEVELOPMENT: bool = ENVIRONMENT == "development"
    
    # 1. Firebase Config
    FIREBASE_API_KEY: str = os.getenv("FIREBASE_API_KEY", "")
    FIREBASE_PROJECT_ID: str = os.getenv("FIREBASE_PROJECT_ID", "")
    FIREBASE_BASE_URL: str = os.getenv("FIREBASE_BASE_URL", "")
    
    # 2. AI Config
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    
    # 3. Midtrans Config
    MIDTRANS_CLIENT_KEY: str = os.getenv("MIDTRANS_CLIENT_KEY", "")
    MIDTRANS_SERVER_KEY: str = os.getenv("MIDTRANS_SERVER_KEY", "")
    
    # Aturan otomatis untuk keamanan payment gateway
    MIDTRANS_IS_PRODUCTION: bool = not IS_DEVELOPMENT

    # Properti dinamis untuk CORS ALLOWED ORIGINS 
    @property
    def ALLOWED_ORIGINS(self) -> list[str]:
        # Ambil string dari .env, kalau kosong pakai localhost sebagai fallback
        raw_origins = os.getenv(
            "BASE_URL", 
            "http://localhost:3000,http://localhost:8000"
        )
        # Memecah string berbasis koma menjadi list Python: ['url1', 'url2']
        return [origin.strip() for origin in raw_origins.split(",")]

settings = Settings()
