import streamlit as st
from PIL import Image
import io
import base64
import time
from utils.client_logger import ClientLogger
from SRGANClient import SRGANClient
import os
from streamlit_option_menu import option_menu
from streamlit_cookies_controller import CookieController

st.set_page_config(initial_sidebar_state="collapsed")

class SRGANUI:
    def __init__(self):
        self.logger = ClientLogger()
        self.API = os.getenv("API_URL")
        self.client = SRGANClient(base_url=self.API)
        self.controller = CookieController()
        
        # Инициализация состояний
        if "selected_page" not in st.session_state:
            st.session_state.selected_page = "Home"
        if "is_authenticated" not in st.session_state:
            st.session_state.is_authenticated = False
        if "access_token" not in st.session_state:
            st.session_state.access_token = None
        if "scale_factor" not in st.session_state:
            st.session_state.scale_factor = 4
        if "use_decoration" not in st.session_state:
            st.session_state.use_decoration = False
            
        self.check_auth_cookie()
        self.load_css()
                        
    def load_css(self):
        """Загрузка CSS стилей"""
        css_path = os.path.join(os.path.dirname(__file__), "static", "styles.css")
        try:
            with open(css_path) as f:
                st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
        except Exception as e:
            self.logger.error(f"Ошибка загрузки CSS: {e}")

    def check_auth_cookie(self):
        """Проверка наличия валидного токена в куках"""
        try:
            token = self.controller.get('access_token')
            if token and self.client.validate_token(token):
                st.session_state.is_authenticated = True
                st.session_state.access_token = token
                self.logger.info("User authenticated from cookies")
            else:
                self.clear_auth_data()
        except Exception as e:
            self.logger.log_error(e, "cookie_validation")
            self.clear_auth_data()

    def clear_auth_data(self):
        """Очистка данных аутентификации"""
        st.session_state.is_authenticated = False
        st.session_state.access_token = None
        
        try:
            for key in list(self.controller.getAll().keys()):
                self.controller.remove(key)
        except:
            pass
        
        st.session_state.logout_processed = True

    def render_original_image(self, image, col):
        """Отображение оригинального изображения"""
        with col:
            st.subheader("Оригинальное изображение")
            st.image(image, use_container_width=True)
            self.logger.log_ui_action("Отображено оригинальное изображение")

    def render_processed_image(self, image_data, col):
        """Отображение обработанного изображения и кнопки скачивания"""
        with col:
            st.subheader("Обработанное изображение")
            upscaled_image = Image.open(io.BytesIO(base64.b64decode(image_data)))
            st.image(upscaled_image, use_container_width=True)
            
            st.session_state.processed_image = upscaled_image
            
            if st.session_state.processed_image:
                buf = io.BytesIO()
                st.session_state.processed_image.save(buf, format="PNG")
                byte_im = buf.getvalue()
                
                st.download_button(
                    label="Скачать изображение",
                    data=byte_im,
                    file_name=f"upscaled_x{st.session_state.scale_factor}{'_enhanced' if st.session_state.use_decoration else ''}.png",
                    mime="image/png",
                    use_container_width=True,
                    key="download_button"
                )
            
            self.logger.info("Успешно отображено обработанное изображение")

    def render_home(self):
        """Отображение страницы с апскейлингом"""
        self.payment_status()
        st.title("SRGAN Апскейлер Изображений")
        st.write("Загрузите изображение для увеличения разрешения")
        
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
                "Улучшить качество фото (доп. 5 кредитов)",
                value=False
            )
        
        uploaded_file = st.file_uploader("Выберите изображение", type=["png", "jpg", "jpeg"])
        
        if uploaded_file is not None:
            self.logger.log_upload(uploaded_file.name, uploaded_file.size)
            
            try:
                image = Image.open(uploaded_file)
                col1, col2 = st.columns(2)
                
                self.render_original_image(image, col1)

                if st.button("Увеличить разрешение", use_container_width=True):
                    if not st.session_state.is_authenticated:
                        st.warning("⚠️ Для обработки изображений необходимо войти в систему")
                        st.session_state.selected_page = "Log In"
                        st.rerun()
                        return
                        
                    self.logger.log_ui_action("Нажата кнопка увеличения разрешения")
                    try:
                        start_time = time.time()
                        uploaded_file.seek(0)
                        
                        with st.spinner("Обработка изображения..."):
                            result = self.client.upscale_image(
                                image_bytes=uploaded_file.getvalue(),
                                scale_factor=st.session_state.scale_factor,
                                use_decoration=st.session_state.use_decoration,
                                token=st.session_state.access_token
                            )
                        
                        process_time = time.time() - start_time
                        self.logger.log_response(200 if "image" in result else 400, process_time)
                        
                        if "image" in result:
                            self.render_processed_image(result["image"], col2)
                            new_balance = result["remaining_credits"]
                            self.controller.set("user_balance", new_balance, max_age=31556925)
                            st.success(f"Обработка завершена! Списано: {result['deducted_credits']} кредитов")
                        else:
                            st.error(result.get("error", "Неизвестная ошибка"))
                            
                    except Exception as e:
                        self.logger.log_error(e, "обработка_запроса")
                        st.error(f"Ошибка при обработке запроса: {str(e)}")
            except Exception as e:
                self.logger.log_error(e, "открытие_изображения")
                st.error(f"Ошибка при открытии изображения: {str(e)}")

    def render_pay(self):
        st.title("Выбор тарифа 💳")
        st.write("Выберите подходящий вариант:")

        if not st.session_state.is_authenticated:
            st.warning("⚠️ Для просмотра тарифов необходимо войти в систему")
            st.session_state.selected_page = "Log In"
            st.rerun()
            return

        if 'selected_product' not in st.session_state:
            st.session_state.selected_product = None
        if 'selected_price' not in st.session_state:
            st.session_state.selected_price = None
        
        products = self.client.get_products(st.session_state.access_token)
        if products:
            columns = st.columns(len(products))
            
            for i, (col, product) in enumerate(zip(columns, products)):
                with col:
                    price = product.get('default_price')
                    
                    if price:
                        product_id = product['id']
                        price_id = price['id']
                        amount = price['unit_amount']/100
                        
                        selected = st.session_state.selected_product == product_id
                        card_class = "pricing-card selected" if selected else "pricing-card"
                        
                        st.markdown(f"""
                        <div class="{card_class}">
                            <div class="pricing-title">{product['name']}</div>
                            <div class="price">{amount} {price['currency'].upper()}</div>
                            <div class="per-item">{product.get('description', '')}</div>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        if st.button(f"Выбрать {product['name']}", key=f"select_{product_id}", 
                                    use_container_width=True):
                            
                            st.session_state.selected_product = product_id
                            st.session_state.selected_price = price_id
                            self.controller.set("price_id", price_id)
                            st.session_state.payment_amount = amount
                            st.rerun()
            
            st.markdown('</div>', unsafe_allow_html=True)
            
            if st.session_state.selected_product:
                selected_product_name = next(
                    (p['name'] for p in products if p['id'] == st.session_state.selected_product), 
                    "Выбранный тариф"
                )
                st.markdown(f"<p style='text-align: center; margin: 15px 0;'>Выбран тариф: <b>{selected_product_name}</b></p>", 
                           unsafe_allow_html=True)
                
                st.markdown("<div class='central-button'>", unsafe_allow_html=True)
                
                session_data = self.client.create_checkout_session(
                    token=st.session_state.access_token,
                    price_id=st.session_state.selected_price
                )
                if session_data:
                    self.controller.set("product_id", st.session_state.selected_product)
                    st.markdown(f"""
                    <div style="text-align: center; margin: 20px 0;">
                        <a href="{session_data['checkout_url']}" target="_self" style="
                            background-color: #4CAF50;
                            color: white;
                            padding: 12px 24px;
                            text-decoration: none;
                            border-radius: 6px;
                            font-size: 1rem;
                            display: inline-block;
                        ">Перейти к оплате →</a>
                    </div>
                    """, unsafe_allow_html=True)
                    session_id = session_data["session_id"]
                    self.controller.set("session_id", session_id, max_age=60)
                
                st.markdown("</div>", unsafe_allow_html=True)

    def payment_status(self):
        query_params = st.query_params
        if "success" in query_params and query_params["success"] == "true":
            st.success("✅ Оплата прошла успешно! Спасибо за покупку!")

            product_id = self.controller.get("product_id")
            session_id = self.controller.get("session_id")

            result = self.client.payment_success(
                session_id=session_id,
                product_id=product_id,
                token=st.session_state.access_token
            )

            if result:
                st.success(result["message"])
                current_user_balance = result["new_balance"]
                self.controller.set("user_balance", current_user_balance, max_age=31556925)

            st.query_params.clear()
            time.sleep(3)
            st.rerun()
        elif "canceled" in query_params and query_params["canceled"] == "true":
            st.warning("❌ Оплата отменена")
            st.query_params.clear()

    def render_login(self):
        st.title("Вход в систему 🔐")
        st.write("Пожалуйста, войдите в систему.")

        self.clear_auth_data()
       
        with st.form("login_form"):
            username = st.text_input("Email", placeholder="Введите email")
            password = st.text_input("Пароль", type="password", placeholder="Введите пароль")
            submitted = st.form_submit_button("Войти")
            
            if submitted:
                result = self.client.login(username, password)
                if result:
                    token = result["access_token"]
                    self.controller.set(
                        'access_token', 
                        token, 
                        max_age=3600*24*7,
                        secure=True,
                    )
                    st.session_state.access_token = token
                    st.session_state.is_authenticated = True
                    
                    st.success("Вход выполнен успешно! 🎉")
                    st.session_state.selected_page = "Home"
                    time.sleep(1)
                    current_user = self.client.get_current_user(token)
                    self.controller.set("user_balance", current_user["money"], max_age=31556925)
                    st.rerun()
                else:
                    st.error("Неверный email или пароль")

    def render_registration(self):
        st.title("Регистрация 📝")
        st.write("Пожалуйста, заполните форму регистрации.")
        
        with st.form("registration_form"):
            email = st.text_input("Email", placeholder="Введите email")
            password = st.text_input("Пароль", type="password", placeholder="Введите пароль")
            submitted = st.form_submit_button("Зарегистрироваться")
            
            if submitted:
                result = self.client.register(email, password)
                if "detail" in result:
                    st.error(result["detail"])
                else:
                    st.success(f"Пользователь {email} успешно зарегистрирован! 🎉")

    def show_money_panel(self):
        if not st.session_state.is_authenticated:
            return
        current_user = self.client.get_current_user(st.session_state.access_token)
        balance = current_user["money"] or 0

        panel_html = f"""
        <div class="currency-panel">
            <div class="currency-title">{balance} 👛</div>
        </div>
        """
        
        st.markdown(panel_html, unsafe_allow_html=True)

    def show_interface(self):
        self.show_money_panel()

        if st.session_state.is_authenticated:
            menu_items = ["Home", "Pay", "Log Out"]
            menu_icons = ['house', 'wallet', 'box-arrow-left']
        else:
            menu_items = ["Log In", "For the first time?"]
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
        
        if st.session_state.selected_page == "Home":
            if not st.session_state.is_authenticated:
                st.session_state.selected_page = "Log In"
                st.rerun()
                return
            self.render_home()
        elif st.session_state.selected_page == "Pay":
            if not st.session_state.is_authenticated:
                st.session_state.selected_page = "Log In"
                st.rerun()
                return
            self.render_pay()
        elif st.session_state.selected_page == "Log In":
            if st.session_state.is_authenticated:
                st.session_state.selected_page = "Home"
                #st.rerun()
                return
            self.render_login()
        elif st.session_state.selected_page == "For the first time?":
            if st.session_state.is_authenticated:
                st.session_state.selected_page = "Home"
                st.rerun()
                return
            self.render_registration()
        elif st.session_state.selected_page == "Log Out":
            self.clear_auth_data()
            st.success("Вы успешно вышли из системы")
            time.sleep(1)
            st.session_state.selected_page = "Log In"
            # st.rerun()
            return