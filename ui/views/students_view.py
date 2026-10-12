"""Экран «Ученики»: список, добавление, редактирование, удаление, зачисление."""

import tkinter as tk
from tkinter import messagebox, ttk

from sqlalchemy import select

from database.models import Group, Student
from services.group_service import GroupService
from services.student_service import StudentService
from ui.dialogs.choice_dialog import ChoiceDialog
from ui.dialogs.form_dialog import FormDialog
from ui.theme import make_header

LEVEL_LABELS = {
    "beginner": "Начинающий", "elementary": "Элементарный",
    "intermediate": "Средний", "advanced": "Продвинутый",
}
DIRECTION_OPTIONS = tuple(
    (d, d) for d in ("Английский", "Немецкий", "Французский", "Испанский")
)
LEVEL_OPTIONS = tuple((code, label) for code, label in LEVEL_LABELS.items())

STUDENT_FIELDS = (
    ("full_name", "ФИО", "entry", ()),
    ("phone", "Телефон", "entry", ()),
    ("direction", "Направление", "combo", DIRECTION_OPTIONS),
    ("level", "Уровень", "combo", LEVEL_OPTIONS),
    ("parent_name", "Родитель (ФИО)", "entry", ()),
)


class StudentsView:
    """Список учеников с полным управлением записями."""

    def __init__(self, parent: tk.Widget, session) -> None:
        """Инициализирует экран.

        Args:
            parent: родительский виджет.
            session: сессия SQLAlchemy.
        """
        self.session = session
        self.service = StudentService(session)
        self.group_service = GroupService(session)

        self.frame = tk.Frame(parent, bg="#f5f6fa")
        self.frame.pack(fill=tk.BOTH, expand=True)
        make_header(self.frame, "Ученики", "+ Добавить ученика", self._on_add)

        card = tk.Frame(self.frame, bg="white", padx=20, pady=16)
        card.pack(fill=tk.BOTH, expand=True, pady=(14, 0))

        self.table = ttk.Treeview(
            card, show="headings", selectmode="browse",
            columns=("id", "fio", "phone", "direction", "level", "parent"),
        )
        for column, text, width in (
            ("id", "№", 50), ("fio", "ФИО", 220), ("phone", "Телефон", 140),
            ("direction", "Направление", 110), ("level", "Уровень", 110),
            ("parent", "Родитель", 160),
        ):
            self.table.heading(column, text=text)
            self.table.column(column, width=width, anchor=tk.W)
        scrollbar = ttk.Scrollbar(
            card, orient=tk.VERTICAL, command=self.table.yview
        )
        self.table.configure(yscrollcommand=scrollbar.set)
        self.table.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        buttons = tk.Frame(card, bg="white")
        buttons.pack(fill=tk.X, pady=(10, 0))
        ttk.Button(
            buttons, text="✏ Редактировать", style="Secondary.TButton",
            command=self._on_edit,
        ).pack(side=tk.LEFT)
        ttk.Button(
            buttons, text="🗑 Удалить", style="Secondary.TButton",
            command=self._on_delete,
        ).pack(side=tk.LEFT, padx=8)
        ttk.Button(
            buttons, text="👥 Зачислить в группу", style="Secondary.TButton",
            command=self._on_enroll,
        ).pack(side=tk.LEFT)

        self.refresh()

    def refresh(self) -> None:
        """Перезагружает таблицу учеников."""
        self.table.delete(*self.table.get_children())
        for student in self.session.scalars(select(Student)):
            level = getattr(student, "level", "") or ""
            self.table.insert("", tk.END, values=(
                student.student_id, student.full_name,
                getattr(student, "phone", "") or "—",
                getattr(student, "direction", "") or "—",
                LEVEL_LABELS.get(level, level or "—"),
                getattr(student, "parent_name", "") or "—",
            ))

    def _selected_student(self) -> Student | None:
        """Возвращает выбранного ученика или None с подсказкой."""
        selection = self.table.selection()
        if not selection:
            messagebox.showinfo(
                "Ученики", "Выберите ученика в таблице", parent=self.frame
            )
            return None
        return self.session.get(Student, int(self.table.item(selection[0], "values")[0]))

    def _on_add(self) -> None:
        """Открывает форму добавления ученика."""
        dialog = FormDialog(self.frame, "Новый ученик", list(STUDENT_FIELDS))
        self.frame.wait_window(dialog.top)
        if not dialog.result:
            return
        data = dialog.result
        try:
            self.service.create_student(
                data["full_name"], phone=data["phone"],
                direction=data["direction"], level=data["level"],
                parent_name=data["parent_name"],
            )
        except Exception as error:
            messagebox.showerror("Ученики", str(error), parent=self.frame)
        self.refresh()

    def _on_edit(self) -> None:
        """Открывает форму редактирования выбранного ученика."""
        student = self._selected_student()
        if student is None:
            return
        initial = {
            "full_name": student.full_name,
            "phone": getattr(student, "phone", "") or "",
            "direction": getattr(student, "direction", "") or "",
            "level": getattr(student, "level", "") or "",
            "parent_name": getattr(student, "parent_name", "") or "",
        }
        dialog = FormDialog(
            self.frame, "Редактирование ученика", list(STUDENT_FIELDS), initial
        )
        self.frame.wait_window(dialog.top)
        if not dialog.result:
            return
        for key, value in dialog.result.items():
            if hasattr(student, key):
                setattr(student, key, value)
        self.session.commit()
        self.refresh()

    def _on_delete(self) -> None:
        """Удаляет выбранного ученика с подтверждением."""
        student = self._selected_student()
        if student is None:
            return
        if not messagebox.askyesno(
            "Удаление", f"Удалить ученика «{student.full_name}»?", parent=self.frame
        ):
            return
        try:
            self.session.delete(student)
            self.session.commit()
        except Exception as error:
            self.session.rollback()
            messagebox.showerror("Ученики", str(error), parent=self.frame)
        self.refresh()

    def _on_enroll(self) -> None:
        """Зачисляет выбранного ученика в группу."""
        student = self._selected_student()
        if student is None:
            return
        options = [
            (group.group_id, group.name)
            for group in self.session.scalars(select(Group))
        ]
        dialog = ChoiceDialog(
            self.frame, "Зачисление в группу", options, "Выберите группу:"
        )
        self.frame.wait_window(dialog.top)
        if dialog.result is None:
            return
        group = self.session.get(Group, dialog.result)
        if group is None:
            return
        try:
            self.group_service.add_student(group, student.student_id)
        except Exception as error:
            messagebox.showerror("Ученики", str(error), parent=self.frame)
        self.refresh()
