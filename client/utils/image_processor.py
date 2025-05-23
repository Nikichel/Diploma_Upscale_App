import streamlit as st
from PIL import Image
import io
import base64
import time
import os

class ImageProcessor:
    def __init__(self, client, logger, cookie_manager):
        self.client = client
        self.logger = logger
        self.cookie_manager = cookie_manager

    def render_image_columns(self, uploaded_file):
        try:
            image = Image.open(uploaded_file)
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("Оригинальное изображение")
                st.image(image, use_container_width=True)
                self.logger.log_ui_action("Отображено оригинальное изображение")

            return image, col2
        except Exception as e:
            self.logger.log_error(e, "открытие_изображения")
            st.error(f"Ошибка при открытии изображения: {str(e)}")
            return None, None

    def process_image(self, uploaded_file, scale_factor, use_decoration, token):
        try:
            start_time = time.time()
            uploaded_file.seek(0)
            
            with st.spinner("Обработка изображения..."):
                result = self.client.upscale_image(
                    image_bytes=uploaded_file.getvalue(),
                    scale_factor=scale_factor,
                    use_decoration=use_decoration,
                    token=token
                )
            print(result)
            process_time = time.time() - start_time
            self.logger.log_response(200 if "image" in result else 400, process_time)
            return result
        except Exception as e:
            self.logger.log_error(e, "обработка_запроса")
            st.error(f"Ошибка при обработке запроса: {str(e)}")
            return None

    def show_processed_image(self, image_data, col):
        with col:
            st.subheader("Обработанное изображение")
            upscaled_image = Image.open(io.BytesIO(base64.b64decode(image_data)))
            st.image(upscaled_image, use_container_width=True)
            self._create_download_button(upscaled_image)
            self.logger.info("Успешно отображено обработанное изображение")

    def _create_download_button(self, image):
        buf = io.BytesIO()
        image.save(buf, format="PNG")
        st.download_button(
            label="Скачать изображение",
            data=buf.getvalue(),
            file_name=f"upscaled_x{st.session_state.scale_factor}{'_enhanced' if st.session_state.use_decoration else ''}.png",
            mime="image/png",
            use_container_width=True,
            key="download_button"
        )

    def handle_image_upload(self, uploaded_file):
        """Обработка загруженного изображения"""
        self.logger.log_upload(uploaded_file.name, uploaded_file.size)
        
        try:
            image, result_col = self.render_image_columns(uploaded_file)
            if not image:
                return

            if st.button("Увеличить разрешение", use_container_width=True):
                self.process_and_display_image(uploaded_file, result_col)

        except Exception as e:
            self.logger.log_error(e, "handle_upload")
            st.error(f"Ошибка обработки файла: {str(e)}")

    def process_and_display_image(self, uploaded_file, result_col):
        """Обработка и отображение результата"""
        if not st.session_state.is_authenticated:
            st.warning("⚠️ Для обработки изображений необходимо войти в систему")
            st.session_state.selected_page = "Log In"
            st.rerun()
            return
        self.logger.info(f"Use decoration: {st.session_state.use_decoration}")
        result = self.process_image(
            uploaded_file=uploaded_file,
            scale_factor=st.session_state.scale_factor,
            use_decoration=st.session_state.use_decoration,
            token=st.session_state.access_token
        )

        if result and "image" in result:
            self.show_processed_image(result["image"], result_col)
            # #Manager Cokey
            token = self.cookie_manager.get_cookie('access_token')
            current_user = self.client.get_current_user(token)
            self.cookie_manager.set_cookie("user_balance", current_user["money"], max_age=31556925)

            st.success(f"Обработка завершена! Списано: {result['deducted_credits']} кредитов")
        else:
            st.error(result.get("error", "Неизвестная ошибка"))