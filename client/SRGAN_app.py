import os
import time
from utils.client_logger import ClientLogger
from SRGAN_client import SRGANClient
from utils.cookie_manager import CookieManager
from utils.auth_manager import AuthManager
from utils.image_processor import ImageProcessor
from ui_components.payment_handler import PaymentHandler
from ui_components.main_ui import MainUI
import streamlit as st

class SRGANApp:
    def __init__(self):
        self.logger = ClientLogger()
        self.cookie_manager = CookieManager()
        self.client = SRGANClient(base_url=os.getenv("API_URL"))
        self.auth_manager = AuthManager(self.client, self.cookie_manager, self.logger)
        self.image_processor = ImageProcessor(self.client, self.logger, self.cookie_manager)
        self.payment_handler = PaymentHandler(self.client, self.cookie_manager)
        self.main_ui = MainUI(self.auth_manager, self.payment_handler, self.image_processor, self.client, self.cookie_manager, self.logger)

        self._init_session_state()
        self._load_styles()
        self.auth_manager.check_auth()
        
    def _init_session_state(self):
        defaults = {
            "selected_page": "Home",
            "is_authenticated": False,
            "access_token": None,
            "scale_factor": 4,
            "use_decoration": False
        }
        for key, value in defaults.items():
            if key not in st.session_state:
                st.session_state[key] = value

    def _load_styles(self):
        css_path = os.path.join(os.path.dirname(__file__), "static", "styles.css")
        try:
            with open(css_path) as f:
                st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
        except Exception as e:
            self.logger.error(f"Ошибка загрузки CSS: {e}")

    def run(self):
        self._render_balance()
        self.main_ui.render_navigation()
        self._handle_payment_status()

    def _render_balance(self):
        if not st.session_state.is_authenticated: return
        balance = self.cookie_manager.get_cookie("user_balance")
        self.logger.info(f"Баланс: {balance}")
        st.markdown(f"""
            <div class="currency-panel">
                <div class="currency-title">{balance} 👛</div>
            </div>
        """, unsafe_allow_html=True)

    def _handle_payment_status(self):
        if not self.auth_manager.check_auth():
            return
        query_params = st.query_params
        if "success" in query_params or "canceled" in query_params:
            self.auth_manager.check_auth()  # Проверяем аутентификацию перед обработкой

            if "success" in query_params:
                self._render_balance()
            st.query_params.clear()
           