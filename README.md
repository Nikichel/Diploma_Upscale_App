# ResUp - SRGAN Image Upscaler 🚀

Проект для увеличения разрешения изображений с использованием нейросетей SRGAN. Клиент-серверное приложение с возможностью оплаты кредитов через Stripe и управлением балансом пользователя.

## Основные возможности ✨
- Увеличение разрешения изображений в 2x, 4x, 8x
- Опция улучшения визуального восприятия (билинейная фильтрация)
- Регистрация/авторизация пользователей
- Пополнение баланса через Stripe
- Логирование действий и обработки изображений

## Нейронная суть проекта 🧠

### Архитектура SRGAN
**Генератор** включает:
- Residual Blocks (16 слоёв) для глубокого обучения признаков
- Upsampling Blocks (PixelShuffle) для увеличения разрешения
- Post-processing с билинейной фильтрацией при активации опции

**Ключевые особенности:**
- Модель обучена на датасете DIV2K (высококачественные изображения)
- Использование функции потерь VGG для сохранения текстуры
- Адаптивная обработка под разные масштабы (2x → 4x → 8x через каскад)
- Поддержка CUDA для GPU-ускорения

**Примеры улучшений:**
| Оригинал | x2 Upscale | x4 Upscale | x8 Upscale |
|---------------------|-----------------------|-------------------------|--------------------------|
| ![Original](demo/orig_ship.jpg) | ![x2](demo/x2_enhanced_ship.jpg) | ![x4](demo/x4_enhanced_ship.jpg) | ![x8](demo/x8_enhanced_ship.jpg) |

## Технологический стек ⚙️
**Клиент:**
- Streamlit (UI)
- Stripe API (оплата)
- Cookies для управления сессиями

**Сервер:**
- FastAPI
- PostgreSQL (хранение пользователей)
- PyTorch (SRGAN модель)
- Stripe SDK

**ML:**
- PyTorch с предобученной SRGAN моделью
- Albumentations для преобразований
- OpenCV для постобработки

## Установка и запуск 🛠️

1. Клонировать репозиторий:
```bash
git clone https://github.com/yourusername/resup.git
cd resup
```

2. Настройка окружения
Установите:
	Python 3.10+
	PostgreSQL (или Docker для запуска через контейнер).
	Stripe CLI (для тестовых платежей).

3. Настройка переменных окружения
Создайте файл .env в корне проекта:
```bash
	env
	# Сервер  
	DB_HOST=localhost  
	DB_PORT=5432  
	DB_USER=postgres 
	DB_PASS=postgres  
	DB_NAME=srgan_db  

	# Stripe (тестовые ключи)  
	STRIPE_SECRET_KEY=sk_test_...  
	STRIPE_PUBLIC_KEY=pk_test_...  
 
	SECRET_KEY=your_secret_key  
	ALGORITHM=HS256  
	PATH_TO_MODEL=gen_and_disc.pth 
```
4. Запуск PostgreSQL

5. Установка зависимостей
```bash
	pip install -r requirements.txt  
```
6. Запуск сервера
```bash
	cd server  
	python app/main.py
```
Сервер запустится на http://localhost:8000.

7. Запуск клиента (Streamlit)
```bash
	cd client  
	streamlit run streamlit_app.py
```
Клиент откроется в браузере на http://localhost:8501.

8. Тестирование Stripe
	Используйте тестовые карты Stripe (например, 4242 4242 4242 4242).
