from SRGAN_app import SRGANApp
import streamlit as st
import os

if __name__ == "__main__":
    BASE_DIR = os.path.dirname(__file__)
        # В начале вашего скрипта
    logo_path = os.path.join(BASE_DIR, "static", "logo2.png")
    st.set_page_config(
            page_title="ResUp", 
            page_icon=logo_path,  # Можно использовать эмодзи или путь к файлу
            layout="wide",
            initial_sidebar_state="collapsed"
        )

    app = SRGANApp()
    app.run()