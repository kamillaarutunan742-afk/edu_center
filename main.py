"""Точка входа приложения учебного центра."""
"""Точка входа приложения учебного центра.

Создаёт базу данных (при необходимости), открывает окно входа
и после успешной авторизации передаёт управление главному окну.
"""

from database.db import SessionLocal, init_db
from ui.login_window import LoginWindow
from ui.main_window import MainWindow


def main() -> None:
    """Запускает приложение."""
    init_db()
    session = SessionLocal()

    login_window = LoginWindow(session, on_success=lambda user: MainWindow(
        session, user
    ).run())
    login_window.run()

    session.close()


if __name__ == "__main__":
    main()
