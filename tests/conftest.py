# tests/conftest.py

import os
import sys
import asyncio
import pytest

# === Добавляем корень проекта в sys.path ===
# Файл conftest.py лежит в hh-bot/hh-bot/tests
# Поднимаемся на уровень вверх: hh-bot/hh-bot
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


@pytest.fixture(scope="session")
def event_loop():
    """
    Отдельный event loop для async-тестов.
    pytest-asyncio в strict-режиме требует явного event_loop.
    """
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()
