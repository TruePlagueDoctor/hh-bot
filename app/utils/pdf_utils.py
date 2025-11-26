# app/utils/pdf_utils.py

from io import BytesIO
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4

# Регистрируем кириллический шрифт один раз при импорте модуля
try:
    pdfmetrics.registerFont(TTFont("DejaVu", "app/fonts/DejaVuLGCSans.ttf"))
except Exception:
    print("⚠️ WARNING: DejaVuSans.ttf not found — PDF will not support Cyrillic!")


def render_text_to_pdf(text: str, title: str | None = None) -> bytes:
    """
    Генерация PDF с поддержкой русского языка.
    Использует шрифт DejaVuSans (TrueType), который полностью поддерживает Unicode.
    """
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    left_margin = 40
    right_margin = 40
    top_margin = 40
    bottom_margin = 40

    max_width = width - left_margin - right_margin
    y = height - top_margin

    # Шрифты
    title_font = ("DejaVu", 14)
    text_font = ("DejaVu", 11)

    def new_page():
        nonlocal y
        c.showPage()
        c.setFont(text_font[0], text_font[1])
        y = height - top_margin

    # Заголовок
    if title:
        c.setFont(title_font[0], title_font[1])
        c.drawString(left_margin, y, title)
        y -= 24

    c.setFont(text_font[0], text_font[1])

    # Рисуем текст по словам
    for paragraph in text.split("\n"):
        if not paragraph.strip():
            y -= 16
            if y < bottom_margin:
                new_page()
            continue

        line = ""
        for word in paragraph.split():
            test = (line + " " + word).strip()
            if c.stringWidth(test, text_font[0], text_font[1]) <= max_width:
                line = test
            else:
                c.drawString(left_margin, y, line)
                y -= 14
                if y < bottom_margin:
                    new_page()
                line = word

        if line:
            c.drawString(left_margin, y, line)
            y -= 14
            if y < bottom_margin:
                new_page()

        y -= 6
        if y < bottom_margin:
            new_page()

    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer.read()
