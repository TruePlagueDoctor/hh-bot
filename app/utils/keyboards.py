# app/utils/keyboards.py

from aiogram.types import ReplyKeyboardMarkup, KeyboardButton


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="🔍 Настроить поиск"),
                KeyboardButton(text="📨 Вакансии"),
            ],
            [
                KeyboardButton(text="📄 Моё резюме"),
                KeyboardButton(text="📜 История"),
            ],
        ],
        resize_keyboard=True,
    )
