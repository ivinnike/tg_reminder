import logging
from datetime import datetime, timedelta
import sqlite3
import telebot
from telebot import types

# Установка уровня логирования
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

# Создание объекта бота и получение токена
bot = telebot.TeleBot('6358354673:AAHIsFscfwIBnBPhQnfgUYVIApl9ZhkSnwc')

# Подключение к базе данных SQLite
conn = sqlite3.connect('reminder.db', check_same_thread=False)
cursor = conn.cursor()

# Обработчик команды /start
@bot.message_handler(commands=['start'])
def start(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row('Записать 📝')
    markup.row('Посмотреть список 📅')
    markup.row('Удалить 🗑️')
    bot.send_message(chat_id=message.chat.id, text='Что вы хотите сделать?', reply_markup=markup)

# Обработчик нажатия кнопки "Записать"
@bot.message_handler(func=lambda message: message.text == 'Записать 📝')
def add_meeting(message):
    bot.send_message(chat_id=message.chat.id, text='Введите название события')
    bot.register_next_step_handler(message, save_title)

# Обработчик ввода названия события
def save_title(message):
    chat_id = message.chat.id
    title = message.text

    bot.send_message(chat_id=chat_id, text='Введите дату события в формате ДД-ММ-ГГГГ')
    bot.register_next_step_handler(message, save_date, title)

# Обработчик ввода даты
def save_date(message, title):
    chat_id = message.chat.id
    date = message.text

    bot.send_message(chat_id=chat_id, text='Введите время события в формате ЧЧ:ММ')
    bot.register_next_step_handler(message, save_time, title, date)

# Обработчик ввода времени
def save_time(message, title, date):
    chat_id = message.chat.id
    time = message.text

    try:
        meeting_datetime_str = date + ' ' + time
        meeting_datetime = datetime.strptime(meeting_datetime_str, '%d-%m-%Y %H:%M')

        # Сохранение событие в базе данных
        cursor.execute('INSERT INTO reminder (title, datetime) VALUES (?, ?)', (title, meeting_datetime))
        conn.commit()

        # Устанавливаем напоминание за 5 минут до события
        reminder_datetime = meeting_datetime - timedelta(minutes=5)
        bot.send_message(chat_id=chat_id, text='🔔 Напоминание! Событие начнется через 5 минут.')

    except ValueError:
        bot.send_message(chat_id=chat_id, text='Ошибка! Некорректный формат даты и времени.')

# Обработчик нажатия кнопки "Посмотреть список"
@bot.message_handler(func=lambda message: message.text == 'Посмотреть список 📅')
def view_meetings(message):
    cursor.execute('SELECT title, datetime FROM reminder')
    result = cursor.fetchall()

    if result:
        for row in result:
            title, datetime_info = row
            response = f'📌 Название: {title}\n📆 Дата и время: {datetime_info}'
            bot.send_message(chat_id=message.chat.id, text=response)
    else:
        bot.send_message(chat_id=message.chat.id, text='Список событий пуст.')

# Обработчик нажатия кнопки "Удалить"
@bot.message_handler(func=lambda message: message.text == 'Удалить 🗑️')
def delete_meeting(message):
    keyboard = types.InlineKeyboardMarkup()
    cursor.execute('SELECT title, datetime FROM reminder')
    result = cursor.fetchall()

    if result:
        for row in result:
            title, datetime_info = row
            button_text = f'{title} - {datetime_info}'
            button = types.InlineKeyboardButton(button_text, callback_data=title)
            keyboard.add(button)

        bot.send_message(chat_id=message.chat.id, text='Выберите событие для удаления:', reply_markup=keyboard)
    else:
        bot.send_message(chat_id=message.chat.id, text='Список событий пуст.')

# Обработчик нажатия кнопок в InlineKeyboard
@bot.callback_query_handler(func=lambda call: True)
def handle_callback_query(call):
    meeting_title = call.data
    cursor.execute('DELETE FROM reminder WHERE title = ?', (meeting_title,))
    conn.commit()

    if cursor.rowcount > 0:
        bot.send_message(chat_id=call.message.chat.id, text='Событие успешно удалена!')
    else:
        bot.send_message(chat_id=call.message.chat.id, text='Ошибка! Событие не найдена.')

# Запуск бота
bot.polling()