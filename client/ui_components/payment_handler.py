import streamlit as st

class PaymentHandler:
    def __init__(self, client, cookie_manager):
        self.client = client
        self.cookie_manager = cookie_manager

    def render_payment_page(self):
        st.title("Выбор тарифа 💳")
        st.write("Выберите подходящий вариант:")

        products = self.client.get_products(st.session_state.access_token)
        if not products: return

        self._render_product_cards(products)
        self._handle_selected_product(products)

    def _render_product_cards(self, products):
        columns = st.columns(len(products))
        for col, product in zip(columns, products):
            with col:
                self._render_product_card(product)

    def _render_product_card(self, product):
        price = product.get('default_price')
        if not price: return

        product_id = product['id']
        selected = st.session_state.get('selected_product') == product_id
        card_class = "pricing-card selected" if selected else "pricing-card"
        
        st.markdown(f"""
            <div class="{card_class}">
                <div class="pricing-title">{product['name']}</div>
                <div class="price">{price['unit_amount']/100} {price['currency'].upper()}</div>
                <div class="per-item">{product.get('description', '')}</div>
            </div>
        """, unsafe_allow_html=True)

        if st.button(f"Выбрать {product['name']}", key=f"select_{product_id}", use_container_width=True):
            self._handle_product_selection(product, price)

    def _handle_product_selection(self, product, price):
        st.session_state.update({
            "selected_product": product['id'],
            "selected_price": price['id'],
            "payment_amount": price['unit_amount']/100
        })
        self.cookie_manager.set_cookie("price_id", price['id'])
        st.rerun()

    def _handle_selected_product(self, products):
        if not st.session_state.get('selected_product'): return
        
        selected_product_name = next(
            (p['name'] for p in products if p['id'] == st.session_state.selected_product),
            "Выбранный тариф"
        )
        
        st.markdown(f"<p style='text-align: center; margin: 15px 0;'>Выбран тариф: <b>{selected_product_name}</b></p>", 
                   unsafe_allow_html=True)
        
        self._render_payment_button()

    def _render_payment_button(self):
        session_data = self.client.create_checkout_session(
            token=st.session_state.access_token,
            price_id=st.session_state.selected_price
        )
        
        if not session_data: return
        
        self.cookie_manager.set_cookie("product_id", st.session_state.selected_product)
        session_id = session_data["session_id"]
        self.cookie_manager.set_cookie("session_id", session_id, max_age=600)
            
        st.markdown("""
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.15.4/css/all.min.css">
        """, unsafe_allow_html=True)
    
        st.markdown(f"""
            <div class="payment-button-container">
                <a href="{session_data['checkout_url']}" class="payment-button" target="_self">
                    <i class="fas fa-credit-card"></i> Оплатить сейчас
                </a>
            </div>
        """, unsafe_allow_html=True)