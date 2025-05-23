from streamlit_cookies_controller import CookieController
import streamlit as st

class CookieManager:
    def __init__(self):
        self.controller = CookieController()
        
    def set_cookie(self, key, value, max_age=None, secure=False, httponly=False):
        """Установка куки"""
        try:
            self.controller.set(
                name=key,
                value=value,
                max_age=max_age,
                secure=secure
            )
            return True
        except Exception as e:
            st.error(f"Ошибка установки куки: {str(e)}")
            return False
    
    def get_cookie(self, key):
        """Получение значения куки"""
        try:
            return self.controller.get(name=key)
        except:
            return None
    
    def remove_cookie(self, key):
        """Удаление куки"""
        try:
            self.controller.remove(name=key)
            return True
        except:
            return False
    
    def remove_all_cookies(self):
        """Удаление всех куки"""
        try:
            for key in list(self.controller.getAll().keys()):
                self.controller.remove(name=key)
            return True
        except:
            return False
    
    def get_all_cookies(self):
        """Получение всех куки"""
        try:
            return self.controller.getAll()
        except:
            return {}
    
    def check_cookie_exists(self, key):
        """Проверка существования куки"""
        try:
            return key in self.controller.getAll()
        except:
            return False