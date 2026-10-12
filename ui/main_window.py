"""Главное окно приложения с боковой навигацией.

Строится по макету Dashboard из Figma: слева меню разделов,
справа — содержимое выбранного раздела.
"""

import tkinter as tk
from tkinter import ttk

from database.models import User


class MainWindow:
    """Главное окно с навигацией по разделам.

    Attributes:
        session: сессия базы данных.
        user: вошедший пользователь.
    """

    MENU_ITEMS = (
        "Дашборд",
        "Ученики",
        "Группы",
        "Расписание",
        "Посещаемость",
        "Абонементы",
        "Финансы",
        "Отчёты",
    )

    def __init__(self, session, user: User) -> None:
        """Инициализирует главное окно.

        Args:
            session: сессия SQLAlchemy.
            user: пользователь, выполнивший вход.
        """
        self.session = session
        self.user = user

        self.root = tk.Tk()
        self.root.title("Учебный центр")
        self.root.geometry("900x600")

        self._build_layout()

    def _build_layout(self) -> None:
        """Создаёт боковое меню и область содержимого."""
        menu = tk.Frame(self.root, width=180, bg="#2c3e50")
        menu.pack(side=tk.LEFT, fill=tk.Y)

        greeting = tk.Label(
            menu,
            text=f"Привет,\n{self.user.full_name}",
            bg="#2c3e50",
            fg="white",
            font=("Segoe UI", 10, "bold"),
            pady=10,
        )
        greeting.pack(fill=tk.X)

        for item in self.MENU_ITEMS:
            button = tk.Button(
                menu,
                text=item,
                anchor="w",
                relief=tk.FLAT,
                bg="#2c3e50",
                fg="white",
                padx=20,
                pady=8,
                command=lambda name=item: self._show_section(name),
            )
            button.pack(fill=tk.X)

        self.content = ttk.Frame(self.root, padding=15)
        self.content.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        self._show_section("Дашборд")

    def _show_section(self, name: str) -> None:
        """Отображает выбранный раздел в области содержимого.

        Args:
            name: название раздела из меню.
        """
        for widget in self.content.winfo_children():
            widget.destroy()

        ttk.Label(
            self.content, text=name, font=("Segoe UI", 18, "bold")
        ).pack(anchor=tk.W)
        ttk.Label(
            self.content,
            text="Экран будет реализован на следующем шаге разработки",
        ).pack(anchor=tk.W, pady=10)

    def run(self) -> None:
        """Запускает цикл событий главного окна."""
        self.root.mainloop()
