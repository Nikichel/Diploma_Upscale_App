import streamlit as st

class AuthManager:
    def __init__(self, client, cookie_manager, logger):
        self.client = client
        self.cookie_manager = cookie_manager
        self.logger = logger

    def check_auth(self):
        if not hasattr(st.session_state, 'is_authenticated'):
            st.session_state.is_authenticated = False
            
        token = self.cookie_manager.get_cookie('access_token')
        if token and self.client.validate_token(token):
            st.session_state.update({
                "is_authenticated": True,
                "access_token": token
            })
            return True
        return False

    def clear_auth(self):
        st.session_state.is_authenticated = False
        st.session_state.access_token = None
        self.cookie_manager.remove_all_cookies()
        st.session_state.logout_processed = True

    def login(self, username, password):
        try:
            result = self.client.login(username, password)
            if isinstance(result, dict) and "detail" in result:
                return {"detail": result["detail"]}
            
            token = result["access_token"]
            self.cookie_manager.set_cookie('access_token', token, max_age=3600*24*7, secure=True)
            st.session_state.update({
                "is_authenticated": True,
                "access_token": token,
                "selected_page": "Home"
            })
            
            current_user = self.client.get_current_user(token)
            self.cookie_manager.set_cookie("user_balance", current_user["money"], max_age=31556925)
            return True
        except Exception as e:
            self.logger.error(f"Login error: {str(e)}")
            return {"detail": "Ошибка при входе в систему"}

    def register(self, email, password):
        result = self.client.register(email, password)
        if "detail" in result:
            return {"detail": result["detail"]}
        return result