"""Экран «Группы»: список, добавление, редактирование, удаление."""

import tkinter as tk
from tkinter import messagebox, ttk

from sqlalchemy import select

from database.models import Group
from services.group_service import GroupService
from ui.dialogs.form_dialog import FormDialog
from ui.theme import make_header

DIRECTION_OPTIONS = tuple(
    (d, d) for d in ("Английский", "Немецкий", "Французский", "Испанский")
)
LEVEL_OPTIONS = (
    ("beginner", "Начинающий"), ("elementary", "Элементарный"),
    ("intermediate", "Средний"), ("advanced", "Продвинутый"),
)


class GroupsView:
    """Список групп с управлением записями."""

    def __init__(self, parent: tk.Widget, session) -> None:
        """Инициализирует экран.

        Args:
            parent: родительский виджет.
            session: сессия SQLAlchemy.
        """
        self.session = session
        self.service = GroupService(session)

        self.frame = tk.Frame(parent, bg="#f5f6fa")
        self.frame.pack(fill=tk.BOTH, expand=True)
        make_header(self.frame, "Группы", "+ Добавить группу", self._on_add)

        card = tk.Frame(self.frame, bg="white", padx=20, pady=16)
        card.pack(fill=tk.BOTH, expand=True, pady=(14, 0))

        self.table = ttk.Treeview(
            card, show="headings", selectmode="browse",
            columns=("id", "name", "direction", "age", "level", "teacher", "count"),
        )
        for column, text, width in (
            ("id", "№", 50), ("name", "Название", 160),
            ("direction", "Направление", 110), ("age", "Возраст", 90),
            ("level", "Уровень", 110), ("teacher", "Преподаватель", 180),
            ("count", "Учеников", 90),
        ):
            self.table.heading(column, text=text)
            self.table.column(column, width=width, anchor=tk.W)
        scrollbar = ttk.Scrollbar(card, orient=tk.VERTICAL, command=self.table.yview)
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

        self.refresh()

    def refresh(self) -> None:
        """Перезагружает таблицу групп."""
        self.table.delete(*self.table.get_children())
        for group in self.session.scalars(select(Group)):
            level = getattr(group, "level", "") or ""
            teacher = getattr(group, "teacher", None)
            teacher_name = teacher.full_name if teacher is not None else "—"
            self.table.insert("", tk.END, values=(
                group.group_id, group.name,
                getattr(group, "direction", "") or "—",
                getattr(group, "age_range", "") or "—",
                dict(LEVEL_OPTIONS).get(level, level or "—"),
                teacher_name, len(getattr(group, "students", [])),
            ))

    def _selected_group(self) -> Group | None:
        """Возвращает выбранную группу или None с подсказкой."""
        selection = self.table.selection()
        if not selection:
            messagebox.showinfo(
                "Группы", "Выберите группу в таблице", parent=self.frame
            )
            return None
        return self.session.get(Group, int(self.table.item(selection[0], "values")[0]))

    def _teacher_options(self) -> list[tuple]:
        """Собирает варианты преподавателей для выпадающего списка.

        Returns:
            Список кортежей (teacher_id, ФИО).
        """
        from database.models import Teacher
        return [
            (teacher.teacher_id, teacher.full_name)
            for teacher in self.session.scalars(select(Teacher))
        ]

    def _on_add(self) -> None:
        """Открывает форму добавления группы."""
        teacher_options = self._teacher_options()
        fields = [
            ("name", "Название", "entry", ()),
            ("direction", "Направление", "combo", DIRECTION_OPTIONS),
            ("age", "Возраст (например 7-10)", "entry", ()),
            ("level", "Уровень", "combo", LEVEL_OPTIONS),
            ("lessons", "Занятий в неделю", "entry", ()),
        ]
        if teacher_options:
            fields.append(("teacher_id", "Преподаватель", "combo", teacher_options))
        dialog = FormDialog(self.frame, "Новая группа", fields)
        self.frame.wait_window(dialog.top)
        if not dialog.result:
            return
        data = dialog.result
        try:
            self.service.create_group(
                data["name"], data["direction"], data["age"], data["level"],
                int(data["lessons"] or 2),
                teacher_id=data.get("teacher_id"),
            )
        except Exception as error:
            messagebox.showerror("Группы", str(error), parent=self.frame)
        self.refresh()

    def _on_edit(self) -> None:
        """Открывает форму редактирования группы."""
        group = self._selected_group()
        if group is None:
            return
        teacher_options = self._teacher_options()
        fields = [("name", "Название", "entry", ())]
        if teacher_options:
            fields.append(("teacher_id", "Преподаватель", "combo", teacher_options))
        initial = {"name": group.name}
        if teacher_options and group.teacher is not None:
            initial["teacher_id"] = group.teacher.teacher_id
        dialog = FormDialog(self.frame, "Редактирование группы", fields, initial)
        self.frame.wait_window(dialog.top)
        if not dialog.result:
            return
        data = dialog.result
        if data.get("name"):
            group.name = data["name"]
        if data.get("teacher_id") and hasattr(group, "teacher_id"):
            group.teacher_id = data["teacher_id"]
        self.session.commit()
        self.refresh()

    def _on_delete(self) -> None:
        """Удаляет выбранную группу с подтверждением."""
        group = self._selected_group()
        if group is None:
            return
        if not messagebox.askyesno(
            "Удаление", f"Удалить группу «{group.name}»?", parent=self.frame
        ):
            return
        try:
            self.session.delete(group)
            self.session.commit()
        except Exception as error:
            self.session.rollback()
            messagebox.showerror("Группы", str(error), parent=self.frame)
        self.refresh()
