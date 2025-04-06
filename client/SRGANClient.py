import requests
from utils.client_logger import ClientLogger
import os
class SRGANClient:
    def __init__(self, base_url=os.getenv("API_URL")):
        self.base_url = base_url
        self.logger = ClientLogger()

    def validate_token(self, token):
        """Валидация токена через API"""
        try:
            response = requests.get(
                f"{self.base_url}/token/validate",
                headers={"Authorization": f"Bearer {token}"}
            )
            return response.status_code == 200
        except Exception as e:
            self.logger.log_error(e, "token_validation")
            return False

    def get_products(self, token):
        """Получение списка продуктов"""
        try:
            response = requests.get(
                f"{self.base_url}/products",
                headers={"Authorization": f"Bearer {token}"}
            )
            if response.status_code == 200:
                return response.json()["products"]
            return None
        except Exception as e:
            self.logger.log_error(e, "get_products")
            return None

    def create_checkout_session(self, token, price_id):
        """Создание платежной сессии"""
        try:
            response = requests.post(
                f"{self.base_url}/create-checkout-session?price_id={price_id}",
                headers={"Authorization": f"Bearer {token}"}
            )
            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            self.logger.log_error(e, "create_checkout_session")
            return None

    def login(self, username, password):
        """Аутентификация пользователя"""
        try:
            response = requests.post(
                f"{self.base_url}/token",
                data={"username": username, "password": password}
            )
            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            self.logger.log_error(e, "login")
            return None

    def register(self, email, password):
        """Регистрация нового пользователя"""
        try:
            response = requests.post(
                f"{self.base_url}/register",
                json={"email": email, "password": password}
            )
            if response.status_code == 200:
                return response.json()
            return {"detail": response.json().get("detail", "Registration failed")}
        except Exception as e:
            self.logger.log_error(e, "register")
            return {"detail": "Connection error"}

    def payment_success(self, session_id, product_id, token):
        """Подтверждение успешной оплаты"""
        try:
            response = requests.get(
                f"{self.base_url}/payment-success?session_id={session_id}&product_id={product_id}",
                headers={"Authorization": f"Bearer {token}"}
            )
            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            self.logger.log_error(e, "payment_success")
            return None

    def upscale_image(self, image_bytes, scale_factor, use_decoration, token):
        """Отправка изображения на апскейлинг"""
        try:
            files = {"file": image_bytes}
            data = {
                "scale_factor": scale_factor,
                "use_decoration": use_decoration
            }
            response = requests.post(
                f"{self.base_url}/upscale",
                files=files,
                data=data,
                headers={"Authorization": f"Bearer {token}"}
            )
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 402:
                return {"error": "Недостаточно средств на балансе"}
            return {"error": response.text}
            
        except Exception as e:
            self.logger.log_error(e, "upscale_image")
            return {"error": str(e)}
        
    def get_current_user(self, token: str):
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(f"{self.base_url}/users/me", headers=headers)
        response.raise_for_status()
        return response.json()