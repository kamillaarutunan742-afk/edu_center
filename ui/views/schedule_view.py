"""Экран «Расписание»: занятия по дням недели с конфликт-контролем."""

import tkinter as tk
from tkinter import messagebox, ttk

from sqlalchemy import select

from database.models import Group
from services.schedule_service import DAYS, ScheduleService
from ui.dialogs.choice_dialog import ChoiceDialog
from ui.dialogs.form_dialog import FormDialog
from ui.theme import make_header


class ScheduleView:
    """Список занятий с добавлением, редактированием и удалением."""

    def __init__(self, parent: tk.Widget, session, user=None) -> None:
        """Инициализирует экран.

        Args:
            parent: родительский виджет.
            session: сессия SQLAlchemy.
            user: вошедший пользователь (у ученика кнопки скрыты).
        """
        self.session = session
        self.service = ScheduleService(session)
        self.is_student = user is not None and getattr(user, "role", "") == "student"

        self.frame = tk.Frame(parent, bg="#f5f6fa")
        self.frame.pack(fill=tk.BOTH, expand=True)
        if not self.is_student:
            make_header(self.frame, "Расписание", "+ Добавить занятие", self._on_add)
        else:
            make_header(self.frame, "Расписание")

        card = tk.Frame(self.frame, bg="white", padx=20, pady=16)
        card.pack(fill=tk.BOTH, expand=True, pady=(14, 0))

        self.table = ttk.Treeview(
            card,
            show="headings",
            selectmode="browse",
            columns=("id", "day", "time", "group", "teacher", "room"),
        )
        for column, text, width in (
            ("id", "№", 50),
            ("day", "День", 130),
            ("time", "Время", 110),
            ("group", "Группа", 170),
            ("teacher", "Преподаватель", 200),
            ("room", "Кабинет", 90),
        ):
            self.table.heading(column, text=text)
            self.table.column(column, width=width, anchor=tk.W)
        scrollbar = ttk.Scrollbar(card, orient=tk.VERTICAL, command=self.table.yview)
        self.table.configure(yscrollcommand=scrollbar.set)
        self.table.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        if not self.is_student:
            buttons = tk.Frame(card, bg="white")
            buttons.pack(fill=tk.X, pady=(10, 0))
            ttk.Button(
                buttons,
                text="✏ Редактировать",
                style="Secondary.TButton",
                command=self._on_edit,
            ).pack(side=tk.LEFT)
            ttk.Button(
                buttons,
                text="🗑 Удалить",
                style="Secondary.TButton",
                command=self._on_delete,
            ).pack(side=tk.LEFT, padx=8)

        self.refresh()

    def refresh(self) -> None:
        """Перезагружает таблицу расписания."""
        self.table.delete(*self.table.get_children())
        for row in self.service.get_table_rows():
            self.table.insert("", tk.END, values=row)

    def _selected_lesson(self):
        """Возвращает выбранное занятие или None с подсказкой."""
        selection = self.table.selection()
        if not selection:
            messagebox.showinfo(
                "Расписание", "Выберите занятие в таблице", parent=self.frame
            )
            return None
        lesson_id = int(self.table.item(selection[0], "values")[0])
        for lesson in self.service.get_all():
            if getattr(lesson, "schedule_id", None) == lesson_id:
                return lesson
        return None

    def _group_options(self) -> list[tuple]:
        """Собирает варианты групп.

        Returns:
            Список кортежей (group_id, название).
        """
        return [
            (group.group_id, group.name)
            for group in self.session.scalars(select(Group))
        ]

    def _lesson_fields(self) -> list:
        """Формирует набор полей формы занятия."""
        return [
            ("group_id", "Группа", "combo", self._group_options()),
            ("day", "День недели", "combo", tuple((d, d) for d in DAYS)),
            ("start", "Начало (ЧЧ:ММ)", "entry", ()),
            ("end", "Окончание (ЧЧ:ММ)", "entry", ()),
            ("room", "Кабинет", "entry", ()),
        ]

    def _on_add(self) -> None:
        """Открывает форму добавления занятия."""
        options = self._group_options()
        if not options:
            messagebox.showinfo(
                "Расписание", "Сначала создайте группу", parent=self.frame
            )
            return
        dialog = FormDialog(self.frame, "Новое занятие", self._lesson_fields())
        self.frame.wait_window(dialog.top)
        if not dialog.result:
            return
        data = dialog.result
        if data.get("group_id") is None:
            return
        try:
            self.service.create_lesson(
                data["group_id"],
                data["day"],
                data["start"],
                end=data["end"],
                room=data["room"],
            )
        except ValueError as error:
            messagebox.showwarning("Конфликт расписания", str(error), parent=self.frame)
        except Exception as error:
            messagebox.showerror("Расписание", str(error), parent=self.frame)
        self.refresh()

    def _on_edit(self) -> None:
        """Удаляет и заново создаёт занятие с новыми параметрами."""
        lesson = self._selected_lesson()
        if lesson is None:
            return
        group = self.session.get(Group, lesson.group_id)
        initial = {
            "group_id": lesson.group_id,
            "day": lesson.day_of_week,
            "start": str(lesson.start_time),
            "end": str(getattr(lesson, "end_time", "") or ""),
            "room": getattr(lesson, "room", None)
            or getattr(lesson, "cabinet", None)
            or "",
        }
        dialog = FormDialog(
            self.frame, "Редактирование занятия", self._lesson_fields(), initial
        )
        self.frame.wait_window(dialog.top)
        if not dialog.result:
            return
        data = dialog.result
        try:
            self.service.delete(lesson)
            self.service.create_lesson(
                data["group_id"],
                data["day"],
                data["start"],
                end=data["end"],
                room=data["room"],
            )
        except ValueError as error:
            messagebox.showwarning("Конфликт расписания", str(error), parent=self.frame)
        except Exception as error:
            messagebox.showerror("Расписание", str(error), parent=self.frame)
        self.refresh()

    def _on_delete(self) -> None:
        """Удаляет выбранное занятие с подтверждением."""
        lesson = self._selected_lesson()
        if lesson is None:
            return
        if not messagebox.askyesno(
            "Удаление", "Удалить это занятие из расписания?", parent=self.frame
        ):
            return
        self.service.delete(lesson)
        self.refresh()
