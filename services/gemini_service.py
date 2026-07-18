# gemini_service.py

from google import genai
from google.genai import types
from config import settings

class GeminiService:
    def __init__(self):
        # Mengambil API KEY dari environment variable komputer Anda
        # Pastikan Anda sudah set lewat terminal: export GEMINI_API_KEY="kunci_anda" (Mac/Linux) atau set GEMINI_API_KEY="kunci_anda" (Windows)
        self.api_key = settings.GEMINI_API_KEY
        self.client = genai.Client(api_key=self.api_key)
        self.model_id = 'gemini-2.5-flash'


    def tanya_ai_stream(self, pertanyaan: str):
        try:
            config = types.GenerateContentConfig(
                system_instruction="Anda adalah konsultan bisnis profesional. Bantu pengguna dewasa ini membangun bisnis mereka dengan jawaban yang taktis, solutif, realistis, dan menggunakan bahasa Indonesia yang profesional."
            )
            
            # 🌟 GANTI DI SINI: Menggunakan generate_content_stream
            response_stream = self.client.models.generate_content_stream(
                model=self.model_id,
                contents=pertanyaan,
                config=config,
            )
            return response_stream
        except Exception as e:
            return None
