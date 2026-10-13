"""Экран «Дашборд»: показатели, ближайшие занятия, режим ученика."""

import tkinter as tk
from sqlalchemy import select

from database.models import Notification, Student, Subscription
from services.report_service import ReportService
from ui.theme import make_header


class DashboardView:
    """Сводка школы; для ученика — его абонементы и расписание."""

    def __init__(self, parent: tk.Widget, session, user=None) -> None:
        """Инициализирует экран.

        Args:
            parent: родительский виджет.
            session: сессия SQLAlchemy.
            user: вошедший пользователь.
        """
        self.session = session
        self.user = user
        self.service = ReportService(session)

        self.frame = tk.Frame(parent, bg="#f5f6fa")
        self.frame.pack(fill=tk.BOTH, expand=True)
        is_student = user is not None and getattr(user, "role", "") == "student"
        make_header(self.frame, "Дашборд")

        if is_student:
            self._build_student()
        else:
            self._build_manager()

    def _card(self, parent: tk.Widget, title: str, value: str) -> None:
        """Рисует карточку показателя.

        Args:
            parent: контейнер.
            title: подпись.
            value: значение.
        """
        card = tk.Frame(parent, bg="white", padx=16, pady=12)
        card.pack(side=tk.LEFT, padx=(0, 12), fill=tk.X, expand=True)
        tk.Label(card, text=title, bg="white", fg="#6b7590", font=("Segoe UI", 9)).pack(
            anchor="w"
        )
        tk.Label(
            card, text=value, bg="white", fg="#1a1f33", font=("Segoe UI", 15, "bold")
        ).pack(anchor="w")

    def _build_manager(self) -> None:
        """Собирает дашборд менеджера."""
        stats = tk.Frame(self.frame, bg="#f5f6fa")
        stats.pack(fill=tk.X, pady=(14, 0))
        for title, value in self.service.get_dashboard_stats().items():
            self._card(stats, title, str(value))

        columns = tk.Frame(self.frame, bg="#f5f6fa")
        columns.pack(fill=tk.BOTH, expand=True, pady=(14, 0))

        lessons_card = tk.Frame(columns, bg="white", padx=16, pady=14)
        lessons_card.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tk.Label(
            lessons_card,
            text="Ближайшие занятия",
            bg="white",
            fg="#1a1f33",
            font=("Segoe UI", 11, "bold"),
        ).pack(anchor="w")
        lessons = self.service.get_upcoming_lessons()
        if not lessons:
            tk.Label(
                lessons_card,
                text="Занятий пока нет — добавьте их в разделе «Расписание»",
                bg="white",
                fg="#6b7590",
            ).pack(anchor="w", pady=6)
        for day, time_text, name in lessons[:8]:
            tk.Label(
                lessons_card,
                text=f" {day}, {time_text} — {name}",
                bg="white",
                fg="#1a1f33",
                font=("Segoe UI", 10),
            ).pack(anchor="w", pady=2)

        warn_card = tk.Frame(columns, bg="white", padx=16, pady=14)
        warn_card.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tk.Label(
            warn_card,
            text="Требует внимания",
            bg="white",
            fg="#1a1f33",
            font=("Segoe UI", 11, "bold"),
        ).pack(anchor="w")
        items = self.service.get_attention_items()
        if not items:
            tk.Label(warn_card, text="Всё в порядке ✅", bg="white", fg="#6b7590").pack(
                anchor="w", pady=6
            )
        for kind, text in items[:8]:
            color = "#b45309" if kind == "warn" else "#b91c1c"
            tk.Label(
                warn_card, text=f"• {text}", bg="white", fg=color, font=("Segoe UI", 10)
            ).pack(anchor="w", pady=2)

    def _build_student(self) -> None:
        """Собирает дашборд ученика: его абонементы и расписание недели."""
        student = self.session.scalar(
            select(Student).where(Student.full_name == self.user.full_name)
        )

        stats = tk.Frame(self.frame, bg="#f5f6fa")
        stats.pack(fill=tk.X, pady=(14, 0))
        unread = self.session.scalar(
            select(Notification).where(Notification.is_read == False)  # noqa: E712
        )
        unread_note = "есть" if unread is not None else "нет"
        if student is not None:
            subs = list(
                self.session.scalars(
                    select(Subscription).where(
                        Subscription.student_id == student.student_id
                    )
                )
            )
            active = [s for s in subs if s.status == "active"]
            total_left = sum(s.remaining_lessons for s in active)
            self._card(stats, "Активных абонементов", str(len(active)))
            self._card(stats, "Осталось занятий", str(total_left))
        else:
            self._card(stats, "Активных абонементов", "—")
            self._card(stats, "Осталось занятий", "—")
        self._card(stats, "Непрочитанные уведомления", unread_note)

        sub_card = tk.Frame(self.frame, bg="white", padx=16, pady=14)
        sub_card.pack(fill=tk.X, pady=(14, 0))
        tk.Label(
            sub_card,
            text="Мои абонементы",
            bg="white",
            fg="#1a1f33",
            font=("Segoe UI", 11, "bold"),
        ).pack(anchor="w")
        if student is None:
            tk.Label(
                sub_card,
                text="Профиль не найден. Попросите администратора зарегистрировать "
                "вас под ФИО ученика",
                bg="white",
                fg="#6b7590",
                justify=tk.LEFT,
            ).pack(anchor="w", pady=6)
        else:
            subs = list(
                self.session.scalars(
                    select(Subscription).where(
                        Subscription.student_id == student.student_id
                    )
                )
            )
            if not subs:
                tk.Label(
                    sub_card, text="Абонементов пока нет", bg="white", fg="#6b7590"
                ).pack(anchor="w", pady=4)
            for sub in subs:
                type_name = (
                    sub.subscription_type.name if sub.subscription_type else "Абонемент"
                )
                status = self._status_label(sub.status)
                tk.Label(
                    sub_card,
                    text=f"• {type_name} — осталось {sub.remaining_lessons} зан., "
                    f"{status}",
                    bg="white",
                    fg="#1a1f33",
                    font=("Segoe UI", 10),
                ).pack(anchor="w", pady=2)

        schedule_card = tk.Frame(self.frame, bg="white", padx=16, pady=14)
        schedule_card.pack(fill=tk.BOTH, expand=True, pady=(12, 0))
        tk.Label(
            schedule_card,
            text="Расписание занятий",
            bg="white",
            fg="#1a1f33",
            font=("Segoe UI", 11, "bold"),
        ).pack(anchor="w")
        lessons = self.service.get_upcoming_lessons()
        if not lessons:
            tk.Label(
                schedule_card, text="Занятий пока нет", bg="white", fg="#6b7590"
            ).pack(anchor="w", pady=4)
        for day, time_text, name in lessons:
            tk.Label(
                schedule_card,
                text=f" {day}, {time_text} — {name}",
                bg="white",
                fg="#1a1f33",
                font=("Segoe UI", 10),
            ).pack(anchor="w", pady=2)

    @staticmethod
    def _status_label(status: str) -> str:
        """Возвращает русское название статуса абонемента.

        Args:
            status: код статуса.

        Returns:
            Строка для показа.
        """
        return {
            "active": "активен",
            "expired": "закончился",
            "cancelled": "отменён",
        }.get(status, status)
