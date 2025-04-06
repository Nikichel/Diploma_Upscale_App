import logging
from datetime import datetime
import os

class ClientLogger:
    def __init__(self, log_dir: str = "logs/client"):
        self.logger = logging.getLogger("client_logger")
        self.logger.setLevel(logging.DEBUG)
        
        # Создаем директорию для логов, если её нет
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
            
        # Формат логов
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        )
        
        # Файловый обработчик
        file_handler = logging.FileHandler(
            os.path.join(log_dir, f"client_{datetime.now().strftime('%Y%m%d')}.log"),
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        
        # Консольный обработчик
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        
        # Очищаем существующие обработчики
        if self.logger.handlers:
            self.logger.handlers.clear()
            
        # Добавляем обработчики
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)

    def debug(self, message: str):
        self.logger.debug(message)
    
    def info(self, message: str):
        self.logger.info(message)
    
    def warning(self, message: str):
        self.logger.warning(message)
    
    def error(self, message: str):
        self.logger.error(message)
    
    def log_upload(self, filename: str, file_size: int):
        self.info(f"Загрузка файла: {filename} (размер: {file_size} байт)")
    
    def log_response(self, status_code: int, response_time: float):
        self.info(f"Ответ сервера: {status_code} (время: {response_time:.2f}с)")
    
    def log_ui_action(self, action: str):
        self.debug(f"Действие UI: {action}")
    
    def log_error(self, error: Exception, context: str = ""):
        self.error(f"Ошибка в {context}: {str(error)}")