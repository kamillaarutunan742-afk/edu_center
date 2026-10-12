"""Окно авторизации пользователя.

Реализует макет Login из Figma: серый фон, белая карточка входа
по центру, поля логина и пароля с подписями сверху, кнопка «Войти»,
ссылки «Зарегистрироваться» и «Забыли пароль?». UI не содержит
бизнес-логики — проверка пароля выполняется через сервис
аутентификации.
"""

import tkinter as tk
from tkinter import messagebox, ttk

from services.auth_service import authenticate
from sqlalchemy.orm import Session

# Цвета макета из Figma
BG_COLOR = "#f2f2f2"
CARD_COLOR = "#ffffff"


class LoginWindow:
    """Окно входа в систему.

    Attributes:
        session: сессия базы данных.
        on_success: колбэк, вызываемый после успешного входа
            (принимает объект User).
    """

    def __init__(self, session: Session, on_success) -> None:
        """Инициализирует окно входа.

        Args:
            session: сессия SQLAlchemy для доступа к данным.
            on_success: функция, вызываемая после успешного входа.
        """
        self.session = session
        self.on_success = on_success

        self.root = tk.Tk()
        self.root.title("Учебный центр — Вход")
        self.root.geometry("900x620")
        self.root.configure(bg=BG_COLOR)

        self._build_form()
        self.root.bind("<Return>", lambda event: self._on_login())

    def _build_form(self) -> None:
        """Создаёт белую карточку с формой входа по центру окна."""
        # Белая карточка
        card = tk.Frame(self.root, bg=CARD_COLOR, padx=40, pady=30)
        card.place(relx=0.5, rely=0.22, anchor=tk.N)

        title = tk.Label(
            card,
            text="Вход в систему",
            font=("Segoe UI", 13),
            bg=CARD_COLOR,
        )
        title.pack(pady=(0, 15))

        ttk.Label(card, text="Логин").pack(anchor=tk.W)
        self.login_entry = ttk.Entry(card, width=36)
        self.login_entry.pack(pady=(2, 12), ipady=3)
        self.login_entry.focus()

        ttk.Label(card, text="Пароль").pack(anchor=tk.W)
        self.password_entry = ttk.Entry(card, width=36, show="•")
        self.password_entry.pack(pady=(2, 12), ipady=3)

        login_button = ttk.Button(
            card, text="Войти", command=self._on_login, width=14
        )
        login_button.pack(pady=(8, 15))

        register_link = tk.Label(
            card,
            text="Зарегистрироваться",
            font=("Segoe UI", 9),
            bg=CARD_COLOR,
            cursor="hand2",
        )
        register_link.pack()
        register_link.bind("<Button-1>", lambda event: self._on_register())

        forgot_link = tk.Label(
            card,
            text="Забыли пароль?",
            font=("Segoe UI", 8),
            bg=CARD_COLOR,
            fg="#555555",
            cursor="hand2",
        )
        forgot_link.pack(pady=(4, 0))
        forgot_link.bind("<Button-1>", lambda event: self._on_forgot())

    def _on_login(self) -> None:
        """Обрабатывает нажатие кнопки «Войти».

        Проверяет данные через сервис аутентификации; при успехе
        закрывает окно и передаёт управление главному окну.
        """
        login = self.login_entry.get().strip()
        password = self.password_entry.get()

        if not login or not password:
            messagebox.showwarning(
                "Вход", "Введите логин и пароль", parent=self.root
            )
            return

        user = authenticate(self.session, login, password)
        if user is None:
            messagebox.showerror(
                "Вход", "Неверный логин или пароль", parent=self.root
            )
            return

        self.root.destroy()
        self.on_success(user)

    def _on_register(self) -> None:
        """Открывает регистрацию (заглушка до реализации экрана)."""
        messagebox.showinfo(
            "Регистрация",
            "Экран регистрации будет реализован на следующем шаге разработки.",
            parent=self.root,
        )

    def _on_forgot(self) -> None:
        """Открывает восстановление пароля (заглушка до реализации)."""
        messagebox.showinfo(
            "Восстановление пароля",
            "Обратитесь к администратору для сброса пароля.",
            parent=self.root,
        )

    def run(self) -> None:
        """Запускает цикл событий окна."""
        self.root.mainloop()

