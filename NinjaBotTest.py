from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, 
    CallbackContext, filters, CallbackQueryHandler, JobQueue
)
import json
import os
import pytz
from datetime import datetime
import asyncio

# Хранение важных дат и их конфигураций
events = []
chat_ids = {
    "Словцова": None,
    "Взлетка": None,
    "Баумана": None,
    "Свердловская": None,
    "Матезалки": None,
    "Камунальная": None
}
selected_chats = []  # Список для хранения выбранных групп

def load_events(filename='events.json'):
    """Загружает события из файла JSON."""
    if os.path.exists(filename):
        with open(filename, 'r') as file:
            return json.load(file)
    return []

def save_events(events, filename='events.json'):
    """Сохраняет события в файл JSON."""
    with open(filename, 'w') as file:
        json.dump(events, file)

def load_chat_ids(filename='chat_ids.json'):
    """Загружает ID групп из файла JSON."""
    if os.path.exists(filename):
        with open(filename, 'r') as file:
            data = json.load(file)
            for group in chat_ids.keys():
                if group not in data:
                    data[group] = None
            return data
    else:
        return chat_ids

def save_chat_ids(chat_ids, filename='chat_ids.json'):
    """Сохраняет ID групп в файл JSON."""
    with open(filename, 'w') as file:
        json.dump(chat_ids, file)

async def start(update: Update, context: CallbackContext) -> None:
    """Отправляет сообщение с кнопкой 'Приступить'."""
    keyboard = [
        [InlineKeyboardButton("Приступить", callback_data='start_process')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text('Добро пожаловать! Нажмите "Приступить", чтобы начать.', reply_markup=reply_markup)

async def button_handler(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    await query.answer()

    if query.data == 'start_process':
        await query.edit_message_text(
            text='Привет! Используйте формат: YYYY-MM-DD Описание HH:MM Повторений для добавления событий.'
        )
        keyboard = [
            [InlineKeyboardButton("Добавить событие", callback_data='add_event')],
            [InlineKeyboardButton("Показать события", callback_data='show_events')],
            [InlineKeyboardButton("Помощь", callback_data='help')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.reply_text('Выберите действие:', reply_markup=reply_markup)

    elif query.data == 'add_event':
        selected_chats.clear()
        await query.edit_message_text(
            text="Выберите, куда отправлять событие:", 
            reply_markup=await get_chat_selection_keyboard()
        )

    elif query.data.startswith('confirm_event'):
        await query.edit_message_text(text="Выбраны чаты: " + ', '.join(selected_chats))
        context.user_data['awaiting_event_input'] = True
        
    elif query.data in chat_ids:
        if query.data in selected_chats:
            selected_chats.remove(query.data)
        else:
            selected_chats.append(query.data)
        keyboard = await get_chat_selection_keyboard()
        await query.edit_message_text(text="Выберите, куда отправлять событие:", reply_markup=keyboard)

async def handle_event_input(update: Update, context: CallbackContext) -> None:
    if context.user_data.get('awaiting_event_input'):
        try:
            args = update.message.text.split()
            date_str = args[0]
            description = ' '.join(args[1:-2])
            time_str = args[-2]
            frequency = int(args[-1])

            new_event = {
                'date': date_str,
                'description': description,
                'time': time_str,
                'frequency': frequency,
                'chat_id': selected_chats
            }
            events.append(new_event)
            save_events(events)

            await update.message.reply_text(f'Событие добавлено: {date_str} {time_str} - {description} ({frequency} раз)')
            del context.user_data['awaiting_event_input']
        except (IndexError, ValueError) as e:
            await update.message.reply_text('Ошибка! Введите данные в правильном формате: YYYY-MM-DD Описание HH:MM Повторений')

async def handle_message(update: Update, context: CallbackContext) -> None:
    if update.message.text == '/start':
        await start(update, context)
    elif context.user_data.get('awaiting_event_input'):
        await handle_event_input(update, context)
    else:
        await update.message.reply_text("Пожалуйста, используйте меню для навигации или введите команду /help для получения помощи.")

async def get_chat_selection_keyboard():
    keyboard = []
    for chat in chat_ids:
        if chat_ids[chat] is not None:
            button_label = f"✅ {chat}" if chat in selected_chats else chat
            keyboard.append([InlineKeyboardButton(button_label, callback_data=chat)])
    keyboard.append([InlineKeyboardButton("Назад", callback_data='back_to_menu')])
    keyboard.append([InlineKeyboardButton("Подтвердить выбор", callback_data='confirm_event')])
    return InlineKeyboardMarkup(keyboard)

def main() -> None:
    global events, chat_ids
    events = load_events()
    chat_ids = load_chat_ids()

    application = ApplicationBuilder().token("8044750997:AAGsanhJ6VvfEjoJe-zVBqGOgw7bi0TbqKQ").build()

    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Бот запущен. Ожидание команд...")
    application.run_polling()

if __name__ == '__main__':
    main()
