import logging
import json
import os
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InputMediaPhoto
from telegram.ext import (
    Application, CommandHandler, MessageHandler, 
    ContextTypes, filters
)

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

class Database:
    def __init__(self, filename='data.json'):
        self.filename = filename
        self._ensure_file_exists()
    
    def _ensure_file_exists(self):
        if not os.path.exists(self.filename):
            with open(self.filename, 'w', encoding='utf-8') as f:
                json.dump({
                    'exchange_rate': 12.5,
                    'users': [],
                    'statistics': {
                        'total_calculations': 0,
                        'total_users': 0
                    }
                }, f, ensure_ascii=False, indent=4)
    
    def _read_data(self):
        with open(self.filename, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def _write_data(self, data):
        with open(self.filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    
    def get_exchange_rate(self):
        data = self._read_data()
        return data.get('exchange_rate', 12.5)
    
    def set_exchange_rate(self, rate):
        data = self._read_data()
        data['exchange_rate'] = float(rate)
        self._write_data(data)
    
    def add_user(self, user_id, username):
        data = self._read_data()
        users = data['users']
        
        # Проверяем, есть ли пользователь уже в базе
        user_exists = any(user['user_id'] == user_id for user in users)
        
        if not user_exists:
            users.append({
                'user_id': user_id,
                'username': username,
                'first_seen': str(datetime.now())
            })
            data['statistics']['total_users'] += 1
            self._write_data(data)
    
    def increment_calculations(self):
        data = self._read_data()
        data['statistics']['total_calculations'] += 1
        self._write_data(data)
    
    def get_statistics(self):
        data = self._read_data()
        return data['statistics']
    
    def get_all_users(self):
        data = self._read_data()
        return data['users']

# Загрузка конфигурации
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

BOT_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_IDS = list(map(int, os.getenv('ADMIN_IDS', '').split(','))) if os.getenv('ADMIN_IDS') else []

# Инициализация базы данных
db = Database()

# Хранилище состояний пользователей
user_states = {}

# Клавиатура главного меню
def main_keyboard(user_id=None):
    keyboard = [
        [KeyboardButton("🧮 Рассчитать")],
        [KeyboardButton("📖 Инструкция")]
    ]
    if user_id in ADMIN_IDS:
        keyboard.append([KeyboardButton("⚙️ Админ-панель")])
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# Клавиатура админ-панели
def admin_keyboard():
    keyboard = [
        [KeyboardButton("📊 Статистика")],
        [KeyboardButton("💱 Изменить курс")],
        [KeyboardButton("📢 Рассылка")],
        [KeyboardButton("🔙 Назад")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# Клавиатура отмены
def cancel_keyboard():
    return ReplyKeyboardMarkup([[KeyboardButton("🔙 Отмена")]], resize_keyboard=True)

# Проверка прав администратора
def is_admin(user_id):
    return user_id in ADMIN_IDS

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    
    # Сбрасываем состояние пользователя
    user_states[user_id] = None
    db.add_user(user_id, user.username)
    
    welcome_text = (
        f"Привет, {user.first_name}! 👋\n"
        "Я бот-калькулятор стоимости товаров.\n"
        "Выберите действие:"
    )
    
    await update.message.reply_text(
        welcome_text,
        reply_markup=main_keyboard(user_id)
    )

async def send_instruction(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    # Текст инструкции
    instruction_text = (
        "📖 Инструкция по использованию:\n\n"
        "1. Нажмите кнопку '🧮 Рассчитать'\n"
        "2. Введите цену товара в юанях\n"
        "3. Бот автоматически рассчитает стоимость в рублях\n\n"
        "💡 *Пример:* 100 юаней = 1250 рублей (при курсе 12.5)\n\n"
        "🚛Доставка:\n"
        "• Стоимость доставки: 700₽/кг\n"
        "• Срок доставки: 15-20 дней\n"
        "• Тип доставки: Китай - до двери дома\n\n"
        "По всем вопросам обращаться: @MidSaleShop"
    )
    
    # Собираем все доступные фотографии
    photo_files = [
        'images/instruction1.jpg',
        'images/instruction2.jpg', 
        'images/instruction3.jpg',
        'images/instruction4.jpg',
        'images/instruction5.jpg',
        'images/instruction6.jpg'
    ]
    
    media_group = []
    photos_found = False
    
    # Создаем медиагруппу из найденных фотографий
    for i, photo_file in enumerate(photo_files):
        try:
            with open(photo_file, 'rb') as photo:
                # Первая фотография будет с текстом инструкции
                if i == 0:
                    media_group.append(InputMediaPhoto(media=photo, caption=instruction_text))
                else:
                    media_group.append(InputMediaPhoto(media=photo))
                photos_found = True
        except FileNotFoundError:
            logging.warning(f"Фото {photo_file} не найдено")
            continue
    
    if photos_found and len(media_group) > 0:
        # Отправляем все фотографии одним сообщением с текстом
        await update.message.reply_media_group(media=media_group)
        await update.message.reply_text(
            "Выберите действие:",
            reply_markup=main_keyboard(user_id)
        )
    else:
        # Если фотографий нет, отправляем только текст
        await update.message.reply_text(
            instruction_text,
            parse_mode='Markdown',
            reply_markup=main_keyboard(user_id)
        )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text
    
    # Если пользователь в состоянии ожидания ввода
    if user_id in user_states and user_states[user_id] is not None:
        state = user_states[user_id]
        
        if state == "waiting_price":
            await handle_price_input(update, context)
            return
        elif state == "waiting_exchange_rate":
            await handle_exchange_rate_input(update, context)
            return
        elif state == "waiting_broadcast":
            await handle_broadcast_input(update, context)
            return
    
    # Обработка кнопок главного меню
    if text == "🧮 Рассчитать":
        user_states[user_id] = "waiting_price"
        await update.message.reply_text(
            "💰 Введите цену в юанях:",
            reply_markup=cancel_keyboard()
        )
    
    elif text == "📖 Инструкция":
        await send_instruction(update, context)
    
    elif text == "⚙️ Админ-панель" and is_admin(user_id):
        await show_admin_panel(update, context)
    
    elif text == "🔙 Назад":
        user_states[user_id] = None
        await update.message.reply_text(
            "Главное меню:",
            reply_markup=main_keyboard(user_id)
        )
    
    elif text == "🔙 Отмена":
        user_states[user_id] = None
        await update.message.reply_text(
            "Действие отменено.",
            reply_markup=main_keyboard(user_id) if not is_admin(user_id) else admin_keyboard()
        )
    
    # Обработка кнопок админ-панели
    elif is_admin(user_id):
        await handle_admin_actions(update, context)

async def handle_price_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text
    
    if text == "🔙 Отмена":
        user_states[user_id] = None
        await update.message.reply_text(
            "Действие отменено.",
            reply_markup=main_keyboard(user_id)
        )
        return
    
    try:
        price_yuan = float(text.replace(',', '.'))
        exchange_rate = db.get_exchange_rate()
        price_rubles = price_yuan * exchange_rate
        
        db.increment_calculations()
        
        result_text = (
            f"💵 **Результат расчета:**\n\n"
            f"Цена в юанях: {price_yuan} ¥\n"
            f"Курс: 1 ¥ = {exchange_rate} ₽\n"
            f"**Итого: {price_rubles:.2f} ₽**\n\n"
            f"**Стоимость доставки(Китай- до двери Дома): 700₽/кг (Оплачивается отдельно)🚛 Срок доставки: 15-20 дней**\n\n"
            f"**По всем вопросам обращаться @MidSaleShop **"
        )
        
        user_states[user_id] = None
        await update.message.reply_text(
            result_text,
            parse_mode='Markdown',
            reply_markup=main_keyboard(user_id)
        )
        
    except ValueError:
        await update.message.reply_text(
            "❌ Пожалуйста, введите корректное число!\n"
            "Например: 100 или 99.99",
            reply_markup=cancel_keyboard()
        )

async def show_admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text("❌ Доступ запрещен!")
        return
    
    admin_text = "⚙️ **Админ-панель**\n\nВыберите действие:"
    await update.message.reply_text(
        admin_text,
        parse_mode='Markdown',
        reply_markup=admin_keyboard()
    )

async def handle_admin_actions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text
    
    if text == "📊 Статистика":
        stats = db.get_statistics()
        exchange_rate = db.get_exchange_rate()
        
        stats_text = (
            "📊 **Статистика бота:**\n\n"
            f"• Всего пользователей: {stats['total_users']}\n"
            f"• Всего расчетов: {stats['total_calculations']}\n"
            f"• Текущий курс: {exchange_rate} ₽/¥"
        )
        
        await update.message.reply_text(
            stats_text,
            parse_mode='Markdown',
            reply_markup=admin_keyboard()
        )
    
    elif text == "💱 Изменить курс":
        user_states[user_id] = "waiting_exchange_rate"
        current_rate = db.get_exchange_rate()
        await update.message.reply_text(
            f"💱 Текущий курс: {current_rate}\n"
            "Введите новый курс (например: 12.6):",
            reply_markup=cancel_keyboard()
        )
    
    elif text == "📢 Рассылка":
        user_states[user_id] = "waiting_broadcast"
        await update.message.reply_text(
            "📢 Введите сообщение для рассылки:",
            reply_markup=cancel_keyboard()
        )
    
    elif text == "🔙 Назад":
        user_states[user_id] = None
        await update.message.reply_text(
            "Главное меню:",
            reply_markup=main_keyboard(user_id)
        )

async def handle_exchange_rate_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text
    
    if text == "🔙 Отмена":
        user_states[user_id] = None
        await update.message.reply_text(
            "Действие отменено.",
            reply_markup=admin_keyboard()
        )
        return
    
    try:
        new_rate = float(text.replace(',', '.'))
        db.set_exchange_rate(new_rate)
        
        user_states[user_id] = None
        await update.message.reply_text(
            f"✅ Курс успешно изменен на: {new_rate}",
            reply_markup=admin_keyboard()
        )
        
    except ValueError:
        await update.message.reply_text(
            "❌ Пожалуйста, введите корректное число!\n"
            "Например: 12.5 или 12,6",
            reply_markup=cancel_keyboard()
        )

async def handle_broadcast_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text
    
    if text == "🔙 Отмена":
        user_states[user_id] = None
        await update.message.reply_text(
            "Действие отменено.",
            reply_markup=admin_keyboard()
        )
        return
    
    message = text
    users = db.get_all_users()
    
    success_count = 0
    fail_count = 0
    
    await update.message.reply_text("🔄 Начинаю рассылку...")
    
    for user in users:
        try:
            await context.bot.send_message(
                chat_id=user['user_id'],
                text=f"\n\n{message}"
            )
            success_count += 1
        except Exception as e:
            logging.error(f"Ошибка отправки пользователю {user['user_id']}: {e}")
            fail_count += 1
    
    user_states[user_id] = None
    await update.message.reply_text(
        f"📢 **Результат рассылки:**\n\n"
        f"✅ Успешно: {success_count}\n"
        f"❌ Не доставлено: {fail_count}",
        reply_markup=admin_keyboard()
    )

def main():
    if not BOT_TOKEN:
        print("❌ Ошибка: BOT_TOKEN не найден в переменных окружения!")
        print("Создайте файл .env с содержимым:")
        print("BOT_TOKEN=your_bot_token_here")
        print("ADMIN_IDS=123456789,987654321")
        return
    
    # Создаем папку для изображений, если её нет
    if not os.path.exists('images'):
        os.makedirs('images')
        print("📁 Создана папка 'images' для фотографий инструкции")
    
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Обработчики
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Запуск бота
    print("Бот запущен...")
    print("📸 Для добавления фотографий в инструкцию поместите их в папку 'images':")
    print("   - instruction1.jpg")
    print("   - instruction2.jpg") 
    print("   - instruction3.jpg")
    print("   - instruction4.jpg")
    print("   - instruction5.jpg")
    print("   - instruction6.jpg")
    application.run_polling()

if __name__ == '__main__':
    main()