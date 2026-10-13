"""Экран «Абонементы»: продажа ученикам и управление типами."""

import tkinter as tk
from tkinter import messagebox, ttk

from sqlalchemy import select

from database.models import Student, Subscription, SubscriptionType
from services.subscription_service import SubscriptionService
from ui.dialogs.choice_dialog import ChoiceDialog
from ui.dialogs.form_dialog import FormDialog
from ui.theme import make_header


class SubscriptionsView:
    """Список абонементов с продажей и созданием типов."""

    def __init__(self, parent: tk.Widget, session) -> None:
        """Инициализирует экран.

        Args:
            parent: родительский виджет.
            session: сессия SQLAlchemy.
        """
        self.session = session
        self.service = SubscriptionService(session)

        self.frame = tk.Frame(parent, bg="#f5f6fa")
        self.frame.pack(fill=tk.BOTH, expand=True)
        make_header(self.frame, "Абонементы", "+ Продать абонемент", self._on_sell)

        actions = tk.Frame(self.frame, bg="#f5f6fa")
        actions.pack(fill=tk.X, pady=(10, 0))
        ttk.Button(
            actions,
            text="+ Добавить тип абонемента",
            style="Secondary.TButton",
            command=self._on_add_type,
        ).pack(side=tk.LEFT)

        card = tk.Frame(self.frame, bg="white", padx=20, pady=16)
        card.pack(fill=tk.BOTH, expand=True, pady=(12, 0))

        self.table = ttk.Treeview(
            card,
            show="headings",
            selectmode="browse",
            columns=("id", "student", "type", "left", "total", "price", "status"),
        )
        for column, text, width in (
            ("id", "№", 50),
            ("student", "Ученик", 200),
            ("type", "Тип", 120),
            ("left", "Осталось", 80),
            ("total", "Всего", 70),
            ("price", "Цена", 90),
            ("status", "Статус", 110),
        ):
            self.table.heading(column, text=text)
            self.table.column(column, width=width, anchor=tk.W)
        scrollbar = ttk.Scrollbar(card, orient=tk.VERTICAL, command=self.table.yview)
        self.table.configure(yscrollcommand=scrollbar.set)
        self.table.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        types_card = tk.Frame(self.frame, bg="white", padx=20, pady=12)
        types_card.pack(fill=tk.X, pady=(12, 0))
        tk.Label(
            types_card,
            text="Типы абонементов",
            bg="white",
            fg="#6b7590",
            font=("Segoe UI", 9, "bold"),
        ).pack(anchor="w")
        self.types_label = tk.Label(
            types_card,
            text="",
            bg="white",
            fg="#1a1f33",
            font=("Segoe UI", 10),
            justify=tk.LEFT,
            anchor="w",
        )
        self.types_label.pack(anchor="w", pady=(4, 0))

        self.refresh()

    def refresh(self) -> None:
        """Перезагружает таблицу абонементов и список типов."""
        self.table.delete(*self.table.get_children())
        for row in self.service.get_table_rows():
            sub_id, student, type_name, left, total, price, status = row
            status_text = self.service.STATUS_LABELS.get(status, status)
            self.table.insert(
                "",
                tk.END,
                values=(
                    sub_id,
                    student,
                    type_name,
                    left,
                    total,
                    f"{price:.0f} ₽",
                    status_text,
                ),
            )
        types = self.service.get_all_types()
        self.types_label.config(
            text="   ".join(
                f"{item.name}: {item.lessons_count} зан. — {item.price:.0f} ₽"
                for item in types
            )
            or "Типов пока нет — добавьте первый"
        )

    def _on_add_type(self) -> None:
        """Открывает форму создания типа абонемента."""
        dialog = FormDialog(
            self.frame,
            "Новый тип абонемента",
            [
                ("name", "Название", "entry", ()),
                ("lessons", "Количество занятий", "entry", ()),
                ("price", "Цена", "entry", ()),
            ],
        )
        self.frame.wait_window(dialog.top)
        if not dialog.result:
            return
        data = dialog.result
        try:
            self.service.create_type(data["name"], data["lessons"], data["price"])
        except ValueError as error:
            messagebox.showerror("Абонементы", str(error), parent=self.frame)
        self.refresh()

    def _on_sell(self) -> None:
        """Продаёт абонемент: выбор типа, затем ученика."""
        type_options = [
            (item.type_id, f"{item.name} — {item.price:.0f} ₽")
            for item in self.service.get_all_types()
        ]
        if not type_options:
            messagebox.showinfo(
                "Абонементы", "Сначала добавьте тип абонемента", parent=self.frame
            )
            return
        type_dialog = ChoiceDialog(
            self.frame, "Тип абонемента", type_options, "Выберите тип:"
        )
        self.frame.wait_window(type_dialog.top)
        if type_dialog.result is None:
            return
        student_options = [
            (student.student_id, student.full_name)
            for student in self.session.scalars(select(Student))
        ]
        if not student_options:
            messagebox.showinfo(
                "Абонементы", "Сначала добавьте учеников", parent=self.frame
            )
            return
        student_dialog = ChoiceDialog(
            self.frame, "Ученик", student_options, "Выберите ученика:"
        )
        self.frame.wait_window(student_dialog.top)
        if student_dialog.result is None:
            return
        try:
            self.service.sell_subscription(student_dialog.result, type_dialog.result)
        except ValueError as error:
            messagebox.showerror("Абонементы", str(error), parent=self.frame)
        self.refresh()
