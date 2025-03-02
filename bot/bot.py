import asyncio
import random
import sqlite3
import os

from aiogram import Bot, Dispatcher, F
from aiogram.filters.command import CommandStart
from aiogram.types import Message


BOT_TOKEN = os.environ.get("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("Отсутствует токен бота. Установите переменную окружения BOT_TOKEN.")

def get_row_by_index(index: int) -> str:
    conn = sqlite3.connect("./decisions.db")
    cursor = conn.cursor()

    query = "SELECT * FROM decisions WHERE id = ?"
    cursor.execute(query, (index,))
    row = cursor.fetchone()

    cursor.close()
    conn.close()

    if row is None:
        return f"Запись с индексом {index} не найдена."
    
    return f"ID: {row[0]}, Дата: {row[1]}, Долг: {row[2]}, Штраф: {row[3]}"

async def start_command(message: Message):
    """
    Обработчик /start:
    1. Генерирует 5 случайных индексов [1..10].
    2. Делает выборку из таблицы decisions.
    3. Отправляет результат пользователю.
    """
    random_indices = random.sample(range(1, 11), 5)

    conn = sqlite3.connect("./decisions.db")
    cursor = conn.cursor()

    placeholders = ",".join("?" for _ in random_indices)
    query = f"SELECT * FROM decisions WHERE id IN ({placeholders})"
    cursor.execute(query, random_indices)
    rows = cursor.fetchall()

    cursor.close()
    conn.close()

    if rows:
        lines = []
        for row in rows:
            lines.append(f"ID: {row[0]}, Дата: {row[1]}, Долг: {row[2]}, Штраф: {row[3]}")
        answer_text = "\n\n".join(lines)
    else:
        answer_text = "По указанным индексам записи не найдены."

    await message.answer(answer_text)

async def handle_index_message(message: Message):
    """
    Хендлер на сообщения, состоящие только из цифр:
    1. Преобразует строку в int.
    2. Вызывает get_row_by_index().
    3. Отправляет ответ пользователю.
    """
    index = int(message.text)
    result_text = get_row_by_index(index)
    await message.answer(result_text)

async def main():
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()

    dp.message.register(start_command, CommandStart())
    dp.message.register(handle_index_message, F.text.regexp(r"^\d+$"))

    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
