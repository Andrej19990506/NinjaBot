from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, 
    CallbackContext, filters, CallbackQueryHandler
)
from telegram.error import BadRequest, TelegramError
import json
import os
import re
import pytz
from datetime import datetime
import asyncio
import logging

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.DEBUG
)

# Хранение важных дат и их конфигураций
events = []
chat_ids = {
    "Словцова": None,
    "Взлетка": None,
    "Баумана": None,
    "Свердловская": None,
    "Матезалки": None,
    "Комунальная": None
}
selected_chats = []  # Список для хранения выбранных групп

# employees = [
#     {"fio": "Иванов Иван", "rank": "Специалист", "position": "Инженер", "hours": None},
#     {"fio": "Петров Петр", "rank": "Мастер", "position": "Техник", "hours": None},
#     {"fio": "Малахов Алексей", "rank": "Эксперт", "position": "Аналитик", "hours": None}
# ]

# async def scheduled_task(context: CallbackContext) -> None:
#     chat_id = context.job.data['chat_id']  # Получаем chat_id из данных задачи
#     print(f"Отправка запроса на сотрудников в чат {chat_id}")  # Отладочный вывод
#     buttons = [
#     [InlineKeyboardButton(employee["fio"], callback_data=employee["fio"])]  # Здесь employee["fio"] должен совпадать с query.data
#     for employee in employees
# ]
#     reply_markup = InlineKeyboardMarkup(buttons)
#     await context.bot.send_message(chat_id=chat_id, text="Введите количество часов для сотрудников:", reply_markup=reply_markup)

# async def handle_selection(update: Update, context: CallbackContext) -> None:
#     print("Обработчик нажатия кнопки запущен.")
#     if update.callback_query:
#         print("Callback query получен.")
#     query = update.callback_query
#     await query.answer()
#     print("Обработчик нажатия кнопки запущен.")
#     for employee in employees:
#         if employee["fio"] == query.data:
#             print(f"Выбранный сотрудник: {employee['fio']}")
#             context.user_data['selected_employee'] = employee
#             await query.edit_message_text(f"Введите количество часов для {employee['fio']}:")
#             return
#         print("Сотрудник не найден.")
#     else:
#         print("Callback query отсутствует.")

# async def handle_hours_input(update: Update, context: CallbackContext) -> None:
#     selected_employee = context.user_data.get('selected_employee')
#     if selected_employee is not None:
#         try:
#             hours = int(update.message.text)
#             selected_employee['hours'] = hours
#             await update.message.reply_text(
#                 f"Часы успешно обновлены для {selected_employee['fio']}: {hours} ч."
#             )
#             del context.user_data['selected_employee']
#             await send_table(context.bot, update.effective_chat.id)
#         except ValueError:
#             await update.message.reply_text("Пожалуйста, введите корректное число.")

# async def send_table(bot, chat_id) -> None:
#     buffer = io.BytesIO()
#     create_table_image(employees).save(buffer, format='PNG')
#     buffer.seek(0)
#     await bot.send_photo(chat_id=chat_id, photo=buffer)

# def create_table_image(data):
#     headers = ["ФИО", "Ранг", "Должность", "Часы"]
#     font_size = 16
#     font = ImageFont.truetype("arial.ttf", font_size)

#     row_height = 30
#     padding = 10
#     img_width = 600
#     img_height = (len(data) + 1) * row_height + padding

#     image = Image.new("RGB", (img_width, img_height), "white")
#     draw = ImageDraw.Draw(image)

#     y_position = padding
#     for i, header in enumerate(headers):
#         x_position = i * (img_width // len(headers))
#         draw.text((x_position + padding, y_position), header, fill="black", font=font)

#     y_position += row_height
#     for employee in data:
#         for i, key in enumerate(employee):
#             x_position = i * (img_width // len(headers))
#             value = str(employee[key]) if employee[key] is not None else "-"
#             draw.text((x_position + padding, y_position), value, fill="black", font=font)
#         y_position += row_height

#     return image

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


async def welcome_message(update: Update, context: CallbackContext) -> None:
    global chat_ids
    if update.message.new_chat_members:
        for member in update.message.new_chat_members:
            if member.id == context.bot.id:  # Проверка, что это ваш бот
                group_name = update.message.chat.title
                print(f"Название группы: {group_name}")

                if group_name in chat_ids:
                    if chat_ids[group_name] is None:
                        chat_ids[group_name] = update.message.chat.id
                        save_chat_ids(chat_ids)
                        print(f"Сохранен ID группы '{group_name}': {chat_ids[group_name]}")

                await context.bot.send_message(chat_id=update.message.chat.id, 
                    text=f"Привет {group_name}! Я бот, который поможет вам управлять важными событиями.")


                # Закрепление сообщения
                await pin_message(context, update.message.chat.id)


async def pin_message(context: CallbackContext, chat_id: int, message_id: int):
    attempts = 3
    for attempt in range(attempts):
        try:
            await context.bot.pin_chat_message(chat_id=chat_id, message_id=message_id)
            print("Сообщение успешно закреплено.")
            break
        except Exception as e:
            print(f"Ошибка при закреплении сообщения: {e}")
            if attempt < attempts - 1:
                print("Попытка закрепления сообщения через 1 минуту...")
                await asyncio.sleep(60)


async def start(update: Update, context: CallbackContext) -> None:
    """Отправляет сообщение с кнопкой 'Приступить'."""
    keyboard = [
        [InlineKeyboardButton("Приступить", callback_data='start_process')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text('Добро пожаловать! Нажмите "Приступить", чтобы начать.', reply_markup=reply_markup)


async def show_help(query: Update):
    help_text = (
        'Список доступных действий:\n'
        '1. Нажмите "Добавить событие", чтобы ввести новое событие.\n'
        '2. Нажмите "Показать события", чтобы увидеть все добавленные события.\n'
        '3. Для редактирования события используйте кнопку "Редактировать событие" на выбранном событии.\n'
        '4. Для удаления события используйте кнопку "Удалить".\n'
        '5. Вы можете вернуться в главное меню в любое время с помощью кнопки "Назад".\n'
    )
    keyboard = [
        [InlineKeyboardButton("Назад", callback_data='back_to_menu')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text=help_text, reply_markup=reply_markup)


async def button_handler(update: Update, context: CallbackContext) -> None:
    global selected_chats
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
        context.user_data['current_menu'] = 'main_menu'  # Устанавливаем текущее меню

    elif query.data == 'add_event':
        selected_chats.clear()
        context.user_data['current_menu'] = 'event_selection'  # Устанавливаем текущее меню
        await query.edit_message_text(
            text="Выберите, куда отправлять событие:", 
            reply_markup=await get_chat_selection_keyboard()
        )
        context.user_data['awaiting_event_input'] = True
        
    elif query.data == 'show_events':
        context.user_data['current_menu'] = 'events_list'
        await show_events(query, context)  # Используйте query для обновления сообщения

    elif query.data.startswith('show_event_details_'):
        context.user_data['current_menu'] = 'event_details'  # Устанавливаем текущее меню
        await show_event_details(update, context)  

    elif query.data.startswith('confirm_event'):
        await query.edit_message_text(text="Выбраны чаты: " + ', '.join(selected_chats))
        context.user_data['awaiting_event_input'] = True
        
    elif query.data.startswith('edit_event_'):
        context.user_data['current_menu'] = 'event_edit'  # Устанавливаем текущее меню
        event_index = int(query.data.split('_')[-1])
        event = events[event_index]  # Получаем событие для редактирования

        # Формируем текст для предварительного ввода
        input_text = f"{event['date']} {event['description']} {event['time']} {event['frequency']}"
    
        # Обновляем состояние, чтобы ожидать новый ввод
        context.user_data['awaiting_event_input'] = True
        context.user_data['editing_event_index'] = event_index  # Сохраняем индекс события

        # Сообщаем пользователю о редактировании
        await query.edit_message_text(
            text="Введите новые данные для события (YYYY-MM-DD Описание HH:MM Повторений):",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Отмена редактирования", callback_data='cancel_edit')]])  # Кнопка отмены
        )

    elif query.data == 'cancel_edit':
        # Обработка отмены редактирования
        await query.edit_message_text(
            text="🛑 Редактирование отменено. Выберите действие:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("➕ Добавить событие", callback_data='add_event')],
                [InlineKeyboardButton("📅 Показать события", callback_data='show_events')],
                [InlineKeyboardButton("🆘 Помощь", callback_data='help')]
            ])
        )
        context.user_data['awaiting_event_input'] = False
        del context.user_data['editing_event_index']  # Убираем индекс редактирования
    
    elif query.data.startswith('delete_event_'):
        # Подтверждение удаления события
        event_index = int(query.data.split('_')[-1])
        event = events[event_index]  # Получаем удаляемое событие

        await query.edit_message_text(
            text=f"Вы действительно хотите удалить это событие:\n\n"
                f"Дата: {event['date']}\n"
                f"Описание: {event['description']}\n"
                f"Время: {event['time']}\n"
                f"Частота: {event['frequency']} раз?\n\n"
                 "🗑️ *Выберите действие:*",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("✅ Подтвердить", callback_data=f'confirm_delete_{event_index}'),
                    InlineKeyboardButton("❌ Отмена", callback_data='back_to_menu')
                ]
            ])
        )

    elif query.data.startswith('confirm_delete_'):
        # Код для удаления события
        await delete_event(update, context)

    elif query.data == 'select_all_groups':
        if len(selected_chats) == len(chat_ids):  # Если все группы выбраны, снять выбор
            selected_chats.clear()
        else:
            selected_chats = list(chat_ids.keys())  # Добавить все группы

        current_text = "Выберите, куда отправлять событие:"
        current_markup = await get_chat_selection_keyboard()

        # Проверка, изменился ли текст или разметка
        if query.message.text != current_text or query.message.reply_markup != current_markup:
            await query.edit_message_text(text=current_text, reply_markup=current_markup)

    elif query.data in chat_ids.keys():  # Нажатие на конкретную группу
        if query.data in selected_chats:
            selected_chats.remove(query.data)
        else:
            selected_chats.append(query.data)

        current_text = "Выберите, куда отправлять событие:"
        current_markup = await get_chat_selection_keyboard()

        # Проверка, изменился ли текст или разметка
        if query.message.text != current_text or query.message.reply_markup != current_markup:
            await query.edit_message_text(text=current_text, reply_markup=current_markup)

    elif query.data == 'back_to_menu':
        logging.debug("Кнопка 'Назад' нажата.")
        context.user_data['current_menu'] = 'main_menu'  # Смена на главное меню
        keyboard = [
            [InlineKeyboardButton("Добавить событие", callback_data='add_event')],
            [InlineKeyboardButton("Показать события", callback_data='show_events')],
            [InlineKeyboardButton("Помощь", callback_data='help')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text='Выберите действие:', reply_markup=reply_markup)


async def handle_event_input(update: Update, context: CallbackContext) -> None:
    if context.user_data.get('awaiting_event_input'):
        if 'editing_event_index' in context.user_data:
            await edit_event(update, context)  # Обработка редактирования события
        else:
            # Вызов функции добавления события
            await add_event(update, context)  # Обработка добавления нового события
    else:
        await update.message.reply_text("Пожалуйста, используйте меню для навигации или введите команду /help для получения помощи.")


async def add_event(update: Update, context: CallbackContext) -> None:
    logging.debug('Ожидание ввода для добавления нового события')
    try:
        # Разбор ввода события
        args = update.message.text.split()
        if len(args) < 4:
            raise ValueError("Недостаточно аргументов для создания события")

        # Использование регулярных выражений для валидации даты и времени
        date_str = args[0]
        time_str = args[-2]
        frequency = int(args[-1])
        description = ' '.join(args[1:-2])

        # Проверка формата даты и времени
        if not re.match(r'\d{4}-\d{2}-\d{2}', date_str):
            raise ValueError("Неверный формат даты, ожидается YYYY-MM-DD")
        
        if not re.match(r'\d{1,2}:\d{2}', time_str) and not time_str.upper() == "H":
            raise ValueError("Неверный формат времени, ожидается HH:MM")

        # Проверка на уникальность события
        for event in events:
            if (event['date'] == date_str and 
                event['time'] == time_str and 
                event['description'] == description):
                raise ValueError("Событие с такими данными уже существует")

        # Добавление нового события
        new_event = {
            'date': date_str,
            'description': description,
            'time': time_str,
            'frequency': frequency,
            'chat_id': selected_chats
        }
        events.append(new_event)
        save_events(events)

        # Отправка сообщения об успешном добавлении события и сохранение ссылки на это сообщение
        message = await update.message.reply_text(f'Событие добавлено: {date_str} {time_str} - {description} ({frequency} раз)')

        # Задержка перед удалением сообщения
        await asyncio.sleep(3)
        await context.bot.delete_message(chat_id=update.message.chat.id, message_id=message.message_id)

        if update.callback_query:  # Если это callback_query
            await show_events(update.callback_query, context)
        else:  # Если это текстовое сообщение
            await show_events_as_message(update.message.chat.id, context)

        del context.user_data['awaiting_event_input']  # Убираем флаг ожидания
        logging.debug(f'Событие добавлено: {new_event}')

    except (IndexError, ValueError) as e:
        logging.error(f'Ошибка ввода: {e}')
        await update.message.reply_text('Ошибка! Введите данные в формате: YYYY-MM-DD Описание HH:MM Повторений')


async def show_events_as_message(chat_id, context: CallbackContext):
    logging.debug("Показать события")
    keyboard = []
    
    if events:  # Проверьте наличие событий
        for index, event in enumerate(events):
            keyboard.append([
                InlineKeyboardButton(f"{event['date']} - {event['description']}", callback_data=f'show_event_details_{index}')
            ])
        
        keyboard.append([InlineKeyboardButton("Назад", callback_data='back_to_menu')])
        reply_markup = InlineKeyboardMarkup(keyboard)

        await context.bot.send_message(
            chat_id=chat_id,
            text="Выберите событие:" if events else "Нет добавленных событий.\n\nВыберите действие:",
            reply_markup=reply_markup
        )
    else:
        await context.bot.send_message(
            chat_id=chat_id,
            text="Нет добавленных событий.\n\nВыберите действие:"
        )


async def edit_event(update: Update, context: CallbackContext) -> None:
    event_index = context.user_data['editing_event_index']
    input_text = update.message.text  # Получаем текст, введенный пользователем
    event = events[event_index]
    logging.debug('Редактирование события...')

    try:
        # Проверка формата ввода
        args = input_text.split()
        if len(args) < 4:
            raise ValueError("Недостаточно аргументов для редактирования события")

        # Разбор данных
        date_str = args[0]
        time_str = args[-2]
        frequency = int(args[-1])
        description = ' '.join(args[1:-2])

        # Проверка формата даты и времени
        if not re.match(r'\d{4}-\d{2}-\d{2}', date_str):
            raise ValueError("Неверный формат даты, ожидается YYYY-MM-DD")

        if not re.match(r'\d{1,2}:\d{2}', time_str) and not time_str.upper() == "H":
            raise ValueError("Неверный формат времени, ожидается HH:MM")

        # Обновление события
        events[event_index] = {
            'date': date_str,
            'description': description,
            'time': time_str,
            'frequency': frequency,
            'chat_id': selected_chats
        }
        save_events(events)

        # Отправка сообщения об обновлении
        msg = await update.message.reply_text(f'Событие обновлено: {date_str} {time_str} - {description} ({frequency} раз)')
        await asyncio.sleep(3)
        await context.bot.delete_message(chat_id=update.message.chat.id, message_id=msg.message_id)  # Используйте msg для получения message_id

        # Получаем объект query
        query = update.callback_query  # Получаем объект callback_query, если он существует
        if query:
            await show_events(query, context)  # Здесь передаем query
        else:
            # Обработка случая, когда query отсутствует
            await show_events_as_message(update.message.chat.id, context)  # Отображаем события как сообщения, если нет query

        del context.user_data['editing_event_index']  # Убираем индекс редактирования
        del context.user_data['awaiting_event_input']  # Убираем флаг ожидания
        logging.debug(f'Событие обновлено: {events[event_index]}')

    except (IndexError, ValueError) as e:
        logging.error(f'Ошибка редактирования: {e}')
        await update.message.reply_text('Ошибка! Введите данные в формате: YYYY-MM-DD Описание HH:MM Повторений')


async def delete_event(update: Update, context: CallbackContext) -> None:
    try:
        query = update.callback_query  # Получаем callback_query
        event_index = int(query.data.split('_')[-1])  # Получаем индекс события из callback_data

        if 0 <= event_index < len(events):
            deleted_event = events.pop(event_index)  # Удаляем событие
            save_events(events)  # Сохраняем изменения
            
            await query.answer(f'✅ Событие удалено: {deleted_event["date"]} - {deleted_event["description"]}')  # Уведомляем пользователя
            await show_events(query, context)  # Показываем оставшиеся события после удаления
        else:
            await query.answer("⚠️ Событие не найдено.")  # Уведомление о том, что событие не найдено
    except Exception as e:
        logging.error(f'Ошибка при удалении события: {e}')
        await query.answer("⚠️ Произошла ошибка при удалении события.")


async def show_events(query: CallbackQuery, context: CallbackContext):
    logging.debug("Показать события")
    context.user_data['current_menu'] = 'events_list'

    keyboard = []
    if events:  # Проверьте наличие событий
        for index, event in enumerate(events):
            keyboard.append([
                InlineKeyboardButton(f"{event['date']} - {event['description']}", callback_data=f'show_event_details_{index}')
            ])
        
    keyboard.append([InlineKeyboardButton("Назад", callback_data='back_to_menu')])
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Использовать edit_message_text для обновления существующего сообщения
    await query.edit_message_text(
        text="Выберите событие:" if events else "Нет добавленных событий.\n\nВыберите действие:",
        reply_markup=reply_markup
    )

    await context.bot.answer_callback_query(callback_query_id=query.id)  # Убираем индикатор загрузки
    logging.debug("Отображаем сообщение о событиях.")


async def show_event_details(update: Update, context: CallbackContext) -> None:
    """Показывает детали выбранного события с кнопками редактирования и удаления."""
    query = update.callback_query
    await query.answer()

    # Получаем индекс события от колбек-данных
    event_index = int(query.data.split('_')[-1])
    event = events[event_index]

    text_message = (f"Дата: {event['date']}\n"
                    f"Описание: {event['description']}\n"
                    f"Время: {event['time']}\n"
                    f"Частота: {event['frequency']} раз")

    keyboard = [
        [InlineKeyboardButton("Редактировать", callback_data=f'edit_event_{event_index}')],
        [InlineKeyboardButton("Удалить", callback_data=f'delete_event_{event_index}')],
        [InlineKeyboardButton("Назад", callback_data='show_events')]  # Вызов показывает события
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(text=text_message, reply_markup=reply_markup)


async def get_chat_selection_keyboard():
    keyboard = []
    for chat in chat_ids:
        if chat_ids[chat] is not None:
            button_label = f"✅ {chat}" if chat in selected_chats else chat
            keyboard.append([InlineKeyboardButton(button_label, callback_data=chat)])
    keyboard.append([InlineKeyboardButton("Выбрать все филиалы", callback_data='select_all_groups')])        
    keyboard.append([InlineKeyboardButton("Подтвердить выбор", callback_data='confirm_event')])
    keyboard.append([InlineKeyboardButton("Назад", callback_data='back_to_menu')])  # Кнопка назад
    return InlineKeyboardMarkup(keyboard)


async def check_events(context: CallbackContext) -> None:
    print("Проверка событий...")
    
    krasnoyarsk_tz = pytz.timezone('Asia/Krasnoyarsk')
    now = datetime.now(krasnoyarsk_tz)
    today = now.date().strftime("%Y-%m-%d")
    current_time = now.strftime("%H:%M")

    for event in events:
        if event['date'] == today and event['time'] == current_time:
            for chat_id in event['chat_id']:
                try:
                    if chat_ids.get(chat_id) is not None:
                        print(f"Отправка сообщения в чат ID: {chat_id} с сообщением: {event['description']}")
                        chat = await context.bot.get_chat(chat_ids[chat_id])  # Проверка доступности чата
                        await context.bot.send_message(chat_id=chat_ids[chat_id], text=f'Напоминание: {event["description"]}')
                    else:
                        print(f"Чат ID {chat_id} не найден в chat_ids.")
                except BadRequest as e:
                    print(f"Ошибка при отправке сообщения в чат ID {chat_id}: {e}. Проверьте, верный ли chat_id.")
                except TelegramError as e:
                    print(f"Общая ошибка Telegram для чата ID {chat_id}: {e}.")
                except Exception as e:
                    print(f"Общая ошибка: {e}")


async def handle_message(update: Update, context: CallbackContext) -> None:
    if update.message.text == '/start':
        await start(update, context)
    elif context.user_data.get('awaiting_event_input'):
        await handle_event_input(update, context)
    else:
        await update.message.reply_text("Пожалуйста, используйте меню для навигации или введите команду /help для получения помощи.")


def main() -> None:
    global events, chat_ids
    events = load_events()  # Загрузка событий из файла при старте
    chat_ids = load_chat_ids()  # Загрузка ID групп из файла при старте

    # Создание экземпляра приложения с включенной поддержкой JobQueue
    application = ApplicationBuilder().token("8044750997:AAGsanhJ6VvfEjoJe-zVBqGOgw7bi0TbqKQ").build()

    # JobQueue инициализируется автоматически внутри ApplicationBuilder, поэтому отдельное создание не нужно

    # Добавление обработчиков
    application.add_handler(CallbackQueryHandler(button_handler))
    # application.add_handler(CallbackQueryHandler(handle_selection, pattern='select_employee'))
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome_message))
    # application.add_handler(CallbackQueryHandler(handle_selection))

    # Определение действительного chat_id для планирования
    # chat_id = next((id for id in chat_ids.values() if id is not None), None)
    # if chat_id is None:
    #     print("Чата с действительным идентификатором для планирования задач не найдено. Пожалуйста, сначала инициализируйте chat_ids.")
    #     return

    # Планирование задач
    application.job_queue.run_repeating(check_events, interval=60, first=0)  # Проверка событий каждую минуту
    # application.job_queue.run_daily(
    #     # scheduled_task,
    #     time(hour=8, minute=47, second=0, tzinfo=pytz.timezone('Asia/Krasnoyarsk')),
    #     data={'chat_id': chat_id}
    # )
    print("Бот запущен. Ожидание команд...")
    application.run_polling()


if __name__ == '__main__': 
    main()
