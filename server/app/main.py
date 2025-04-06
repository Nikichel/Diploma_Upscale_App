import asyncio
from app import FastAPIApp
from utils.server_logger import ServerLogger
import uvicorn
import signal
import sys
import os
from dotenv import load_dotenv

load_dotenv()

class Server:
    def __init__(self):
        self.logger = ServerLogger()
        self.app = None
        
        # Настраиваем обработчики сигналов для корректного завершения
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)

    async def init_app(self):
        """Асинхронная инициализация приложения"""
        self.logger.info("Инициализация приложения...")
        self.app = FastAPIApp()
        await self.app.load_model()
        self.logger.info("Приложение инициализировано успешно")
        return self.app

    def signal_handler(self, signum, frame):
        """Обработчик сигналов для корректного завершения"""
        self.logger.info(f"Получен сигнал {signum}. Начало завершения работы...")
        asyncio.create_task(self.cleanup())
        sys.exit(0)

    async def cleanup(self):
        """Очистка ресурсов при завершении"""
        self.logger.info("Начало очистки ресурсов...")
        if hasattr(self.app, 'cleanup'):
            await self.app.cleanup()
        self.logger.info("Очистка ресурсов завершена")

    async def run_server(self):
        """Запуск сервера"""
        try:
            # Инициализация приложения
            self.app = await self.init_app()
            
            # Запуск сервера
            self.logger.info("Запуск сервера...")
            config = uvicorn.Config(
                app=self.app.app,
                #host=os.getenv("API_URL"),
                host="127.0.0.1",
                port=8000,
                log_level="info"
            )
            server = uvicorn.Server(config)
            await server.serve()
            
        except Exception as e:
            self.logger.log_error(e, "server_run")
            await self.cleanup()
            raise
        finally:
            await self.cleanup()

if __name__ == "__main__":
    server = Server()
    try:
        asyncio.run(server.run_server())
    except KeyboardInterrupt:
        print("\nПолучен сигнал прерывания. Завершение работы...")
    except Exception as e:
        print(f"Критическая ошибка: {str(e)}")
    finally:
        if server.app:
            asyncio.run(server.cleanup())