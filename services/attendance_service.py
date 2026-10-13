"""Сервис посещаемости: отметки занятий и списание абонементов."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from database.models import (
    Attendance,
    Group,
    GroupStudent,
    Student,
    Subscription,
    SubscriptionType,
)
from repositories.base_repository import BaseRepository
from services.subscription_service import SubscriptionService


class AttendanceService:
    """Бизнес-логика посещаемости."""

    STATUS_LABELS = {
        "present": "Присутствовал",
        "absent": "Отсутствовал",
        "sick": "Болел",
    }

    def __init__(self, session: Session) -> None:
        """Инициализирует сервис.

        Args:
            session: сессия SQLAlchemy.
        """
        self.session = session
        self.repo = BaseRepository(Attendance, session)
        self.subscriptions = SubscriptionService(session)

    def get_all_attendance(self) -> list[Attendance]:
        """Возвращает все отметки.

        Returns:
            Список объектов Attendance.
        """
        return self.repo.get_all()

    def _resolve_students(self, group: Group) -> list[Student]:
        """Превращает связи группы в объекты Student.

        Args:
            group: объект группы.

        Returns:
            Список учеников группы.
        """
        students: list[Student] = []
        for item in group.students:
            if hasattr(item, "full_name"):
                students.append(item)
                continue
            student = self.session.get(Student, item.student_id)
            if student is not None:
                students.append(student)
        return students

    def mark_lesson(self, group: Group, lesson_date, statuses: dict[int, str]) -> None:
        """Отмечает посещаемость группы на дату; присутствующим списывает занятие.

        Args:
            group: объект группы.
            lesson_date: дата занятия.
            statuses: словарь {student_id: статус}.

        Raises:
            ValueError: если у группы нет учеников.
        """
        students = self._resolve_students(group)
        if not students:
            raise ValueError("В этой группе нет учеников")
        for student in students:
            status = statuses.get(student.student_id, "absent")
            record = self.session.scalar(
                select(Attendance).where(
                    Attendance.student_id == student.student_id,
                    Attendance.lesson_date == lesson_date,
                )
            )
            if record is not None:
                record.status = status
                if record.group_id is None:
                    record.group_id = group.group_id
            else:
                self.repo.create(
                    student_id=student.student_id,
                    group_id=group.group_id,
                    lesson_date=lesson_date,
                    status=status,
                )
            if status == "present":
                subscription = self.session.scalars(
                    select(Subscription).where(
                        Subscription.student_id == student.student_id,
                        Subscription.status == "active",
                    )
                ).first()
                if subscription is not None:
                    try:
                        self.subscriptions.spend_lesson(subscription)
                    except ValueError:
                        pass
        self.session.commit()

    def get_table_rows(self, group_id: int | None = None) -> list[tuple]:
        """Собирает строки для таблицы посещаемости.

        Args:
            group_id: фильтр по группе (None — все группы).

        Returns:
            Кортежи (id, дата, группа, ученик, статус, абонемент, списано).
        """
        student_ids = None
        if group_id is not None:
            student_ids = {
                link.student_id
                for link in self.session.scalars(
                    select(GroupStudent).where(GroupStudent.group_id == group_id)
                )
            }
        rows = []
        records = sorted(self.repo.get_all(), key=lambda r: r.lesson_date, reverse=True)
        for record in records:
            if student_ids is not None and record.student_id not in student_ids:
                continue
            student = self.session.get(Student, record.student_id)
            if student is None:
                continue
            group_name = "—"
            if getattr(record, "group_id", None):
                group = self.session.get(Group, record.group_id)
                if group is not None:
                    group_name = group.name
            if group_name == "—":
                for link in self.session.scalars(
                    select(GroupStudent).where(
                        GroupStudent.student_id == student.student_id
                    )
                ):
                    group = self.session.get(Group, link.group_id)
                    if group is not None:
                        group_name = group.name
                        break

            sub_name = "—"
            latest_sub = self.session.scalars(
                select(Subscription)
                .where(Subscription.student_id == student.student_id)
                .order_by(Subscription.subscription_id.desc())
            ).first()
            if latest_sub is not None:
                sub_type = latest_sub.subscription_type
                if sub_type is None and getattr(latest_sub, "type_id", None):
                    sub_type = self.session.get(SubscriptionType, latest_sub.type_id)
                if sub_type is not None:
                    sub_name = sub_type.name

            spent = "-1" if record.status == "present" else "—"
            rows.append(
                (
                    record.attendance_id,
                    str(record.lesson_date),
                    group_name,
                    student.full_name,
                    self.STATUS_LABELS.get(record.status, record.status),
                    sub_name,
                    spent,
                )
            )
        return rows
