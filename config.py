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
    FIREBASE_BASE_URL: str = f"https://{FIREBASE_PROJECT_ID}-default-rtdb.asia-southeast1.firebasedatabase.app"
    
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
        # Tautan dasar yang selalu diizinkan di semua lingkungan
        origins = [
            "http://localhost:3000",
            "http://localhost:8000"
        ]

        if self.ENVIRONMENT == "production":
            origins.append("https://elearning-backend-production-b5a4.up.railway.app")
        elif self.ENVIRONMENT == "staging":
            origins.append("https://elearning-backend-staging-8f81.up.railway.app")
            
        return origins

settings = Settings()
