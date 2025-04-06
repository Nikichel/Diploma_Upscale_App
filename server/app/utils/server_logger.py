import logging
from datetime import datetime
import os

class ServerLogger:
    def __init__(self, log_dir: str = "logs/server"):
        self.logger = logging.getLogger("server_logger")
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
            os.path.join(log_dir, f"server_{datetime.now().strftime('%Y%m%d')}.log"),
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
    
    def log_request(self, method: str, path: str, status_code: int):
        self.info(f"Запрос: {method} {path} - Статус: {status_code}")
    
    def log_model_status(self, status: str):
        self.info(f"Статус модели: {status}")
    
    def log_image_processing(self, image_size: int, shape: tuple = None):
        self.debug(f"Обработка изображения: размер={image_size} байт, форма={shape}")
    
    def log_error(self, error: Exception, context: str = ""):
        self.error(f"Ошибка в {context}: {str(error)}")