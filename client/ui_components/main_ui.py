import streamlit as st
from streamlit_option_menu import option_menu
import time
import os
import base64

class MainUI:
    def __init__(self, auth_manager, payment_handler, image_processor, client, cookie_manager, logger):
        self.auth_manager = auth_manager
        self.payment_handler = payment_handler
        self.image_processor = image_processor
        self.client = client
        self.cookie_manager = cookie_manager
        self.logger = logger

    def render_navigation(self):
        if st.session_state.is_authenticated:
            menu_items = ["Главная", "Оплата", "Выйти"]
            menu_icons = ['house', 'wallet', 'box-arrow-left']
        else:
            menu_items = ["Войти", "Впервые?"]
            menu_icons = ['box-arrow-in-right', 'person-plus']

        selected = option_menu(
            menu_title=None,
            options=menu_items,
            icons=menu_icons,
            menu_icon="cast",
            default_index=0,
            key='menu',
            orientation="horizontal",
            styles={
                "container": {"padding": "0!important", "background-color": "#fafafa"},
                "icon": {"color": "orange", "font-size": "16px"}, 
                "nav-link": {"font-size": "16px", "text-align": "center", "margin":"0px", "--hover-color": "#eee"},
                "nav-link-selected": {"background-color": "#4CAF50"},
            }
        )
        
        st.session_state.selected_page = selected
        self._handle_navigation()

    def _handle_navigation(self):
        page_handlers = {
            "Главная": self._handle_home,
            "Оплата": self._handle_pay,
            "Войти": self._handle_login,
            "Впервые?": self._handle_registration,
            "Выйти": self._handle_logout
        }
        
        handler = page_handlers.get(st.session_state.selected_page)
        if handler: handler()

    def _handle_home(self):
        if not self._check_auth(): return
        self._render_home_page()

    def _handle_pay(self):
        if not self._check_auth(): return
        self.payment_handler.render_payment_page()

    def _handle_login(self):
        if st.session_state.is_authenticated:
            st.session_state.selected_page = "Главная"
            return
        self._render_login_page()

    def _handle_registration(self):
        if st.session_state.is_authenticated:
            st.session_state.selected_page = "Главная"
            st.rerun()
            return
        self._render_registration_page()

    def _handle_logout(self):
        self.auth_manager.clear_auth()
        st.success("Вы успешно вышли из системы")
        time.sleep(1)
        st.session_state.selected_page = "Войти"
        st.rerun()

    def _check_auth(self):
        if st.session_state.is_authenticated: return True
        st.warning("⚠️ Для этого действия необходимо войти в систему")
        st.session_state.selected_page = "Войти"
        st.rerun()
        return False
    
    def _render_login_page(self):
        st.title("Вход в систему 🔐")
        st.write("Пожалуйста, войдите в систему.")

        with st.form("login_form"):
            username = st.text_input("Email", placeholder="Введите email")
            password = st.text_input("Пароль", type="password", placeholder="Введите пароль")
            submitted = st.form_submit_button("Войти")
            
            if submitted:
                result = self.auth_manager.login(username, password)
                self.logger.info(result)
                
                # Проверяем тип результата
                if isinstance(result, dict) and "detail" in result:
                    st.error(result["detail"])
                elif result:  # Если результат True (успешный вход)
                    st.success("Вход выполнен успешно! 🎉")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("Произошла неизвестная ошибка")

    def _render_registration_page(self):
        st.title("Регистрация 📝")
        st.write("Пожалуйста, заполните форму регистрации.")
        
        with st.form("registration_form"):
            email = st.text_input("Email", placeholder="Введите email")
            password = st.text_input("Пароль", type="password", placeholder="Введите пароль")
            submitted = st.form_submit_button("Зарегистрироваться")
            
            if submitted:
                result = self.auth_manager.register(email, password)
                if "detail" in result:
                    st.error(result["detail"])
                else:
                    st.success(f"Пользователь {email} успешно зарегистрирован! 🎉")

    def _render_home_page(self):
        self._render_payment_status()

        st.markdown("""
            <div class="hero-section">
                <h1 class="main-title">ResUp</h1>
                <div class="subtitle">От пикселей к совершенству</div>
            </div>
        """, unsafe_allow_html=True)
        
        col_params = st.columns(2)
        with col_params[0]:
            st.session_state.scale_factor = st.radio(
                "Коэффициент увеличения",
                options=[2, 4, 8],
                index=1,
                horizontal=True
            )
        with col_params[1]:
            st.session_state.use_decoration = st.checkbox(
                "Улучшить визуальное восприятие (доп. 5 кредитов)",
                value=False
            )
        
        uploaded_file = st.file_uploader("Выберите изображение", type=["png", "jpg", "jpeg"])
        
        if uploaded_file is not None:
            self.image_processor.handle_image_upload(uploaded_file)

    def _render_payment_status(self):
        query_params = st.query_params
        if "success" in query_params:
            self._handle_successful_payment()
        elif "canceled" in query_params:
            self._handle_canceled_payment()

    def _handle_successful_payment(self):
        st.success("✅ Оплата прошла успешно! Спасибо за покупку!")
        product_id = self.cookie_manager.get_cookie("product_id")
        session_id = self.cookie_manager.get_cookie("session_id")

        result = self.client.payment_success(
            session_id=session_id,
            product_id=product_id,
            token=st.session_state.access_token
        )
        self.logger.info(f"Результат оплаты: {result}")
        if result:
            # Обновляем баланс в реальном времени
            st.session_state.user_balance = result["new_balance"]
            self.cookie_manager.set_cookie("user_balance", result["new_balance"], max_age=31556925)
            self.logger.info(f"Оплата прошла успешно! Баланс: {result['new_balance']}")

    def _handle_canceled_payment(self):
        st.warning("❌ Оплата отменена")