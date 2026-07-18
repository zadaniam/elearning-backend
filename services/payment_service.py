# payment_service.py

import midtransclient
from config import settings 

class PaymentService:
    def __init__(self):
        # Ambil konfigurasi dari environment
        self.server_key = settings.MIDTRANS_SERVER_KEY
        self.is_production = settings.MIDTRANS_IS_PRODUCTION

        # Inisialisasi SDK Midtrans Snap
        self.snap = midtransclient.Snap(
            is_production=self.is_production,
            server_key=self.server_key
        )

    def create_snap_token(self, order_id: str, amount: int, item_name: str, user_email: str):
        """Membuat token transaksi Midtrans"""
        try:
            param = {
                "transaction_details": {
                    "order_id": order_id,
                    "gross_amount": amount,
                },
                "item_details": [{
                    "id": "premium-01",
                    "price": amount,
                    "quantity": 1,
                    "name": item_name
                }],
                "customer_details": {
                    "email": user_email
                }
            }
            transaction = self.snap.create_transaction(param)
            return {
                "success": True,
                "token": transaction['token'],
                "redirect_url": transaction['redirect_url']
            }
        except Exception as e:
            print(f"--- ❌ PAYMENT SERVICE ERROR: {e} ---")
            return {"success": False, "error": str(e)}
