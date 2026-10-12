"""Сервис посещаемости: отметка занятий и списание абонементов."""

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from database.models import Attendance, Subscription
from repositories.base_repository import BaseRepository
from services.subscription_service import SubscriptionService

PRESENT = "present"
ABSENT = "absent"


class AttendanceService:
    """Бизнес-логика журнала посещаемости."""

    VALID_STATUSES = (PRESENT, ABSENT)

    def __init__(self, session: Session) -> None:
        """Инициализирует сервис.

        Args:
            session: сессия SQLAlchemy.
        """
        self.session = session
        self.repo = BaseRepository(Attendance, session)
        self.subscriptions = SubscriptionService(session)

    def mark(
        self,
        student_id: int,
        group_id: int,
        lesson_date: date,
        schedule_id: int | None = None,
        status: str = PRESENT,
        spend_lesson: bool = True,
    ) -> Attendance:
        """Отмечает посещаемость ученика на занятии.

        При статусе «present» списывает занятие с активного абонемента,
        если списание разрешено (spend_lesson).

        Args:
            student_id: идентификатор ученика.
            group_id: идентификатор группы.
            lesson_date: дата занятия.
            schedule_id: идентификатор строки расписания.
            status: «present» или «absent».
            spend_lesson: списывать ли занятие с абонемента.

        Returns:
            Созданная запись Attendance.

        Raises:
            ValueError: при некорректном статусе или нехватке занятий.
        """
        if status not in self.VALID_STATUSES:
            raise ValueError(f"Недопустимый статус посещения: {status}")

        subscription_id = None
        if status == PRESENT and spend_lesson:
            subscription = self.subscriptions.find_active_subscription(student_id)
            if subscription is None:
                raise ValueError("У ученика нет активного абонемента с занятиями")
            self.subscriptions.spend_lesson(subscription)
            subscription_id = subscription.subscription_id

        existing = self.session.scalar(
            select(Attendance).where(
                Attendance.student_id == student_id,
                Attendance.lesson_date == lesson_date,
                Attendance.group_id == group_id,
            )
        )
        if existing:
            return self.repo.update(
                existing, status=status, subscription_id=subscription_id
            )

        return self.repo.create(
            student_id=student_id,
            group_id=group_id,
            schedule_id=schedule_id,
            subscription_id=subscription_id,
            lesson_date=lesson_date,
            status=status,
        )

    def get_group_journal(self, group_id: int) -> list[Attendance]:
        """Возвращает все отметки посещаемости группы.

        Args:
            group_id: идентификатор группы.

        Returns:
            Список записей Attendance.
        """
        return list(
            self.session.scalars(
                select(Attendance)
                .where(Attendance.group_id == group_id)
                .order_by(Attendance.lesson_date)
            )
        )
