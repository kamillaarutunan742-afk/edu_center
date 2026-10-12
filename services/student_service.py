"""Сервис учеников: CRUD и поиск.

Содержит бизнес-правила работы с учениками: валидацию данных,
перевод в другой статус и т.д. UI не работает с БД напрямую —
только через сервисы.
"""

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from database.models import GroupStudent, Student
from repositories.base_repository import BaseRepository


class StudentService:
    """Бизнес-логика работы с учениками."""

    VALID_STATUSES = ("active", "frozen", "archived")

    def __init__(self, session: Session) -> None:
        """Инициализирует сервис.

        Args:
            session: сессия SQLAlchemy.
        """
        self.session = session
        self.repo = BaseRepository(Student, session)

    def create_student(self, full_name: str, phone: str, **fields) -> Student:
        """Создаёт ученика с валидацией обязательных полей.

        Args:
            full_name: полное имя (обязательно).
            phone: телефон (обязательно).
            **fields: остальные поля модели Student.

        Returns:
            Созданный объект Student.

        Raises:
            ValueError: если имя или телефон пустые, либо статус некорректен.
        """
        if not full_name.strip():
            raise ValueError("ФИО ученика не может быть пустым")
        if not phone.strip():
            raise ValueError("Телефон ученика не может быть пустым")
        status = fields.get("status", "active")
        if status not in self.VALID_STATUSES:
            raise ValueError(f"Недопустимый статус: {status}")
        fields.setdefault("enroll_date", date.today())
        return self.repo.create(
            full_name=full_name.strip(), phone=phone.strip(), **fields
        )

    def get_student(self, student_id: int) -> Student | None:
        """Возвращает ученика по идентификатору.

        Args:
            student_id: первичный ключ ученика.

        Returns:
            Объект Student или None.
        """
        return self.repo.get_by_id(student_id)

    def get_all_students(self) -> list[Student]:
        """Возвращает всех учеников."""
        return self.repo.get_all()

    def search_students(self, query: str) -> list[Student]:
        """Ищет учеников по подстроке в ФИО.

        Args:
            query: поисковая строка.

        Returns:
            Список подходящих учеников (пустой, если запрос пустой).
        """
        if not query.strip():
            return self.get_all_students()
        pattern = f"%{query.strip()}%"
        return list(
            self.session.scalars(
                select(Student).where(Student.full_name.like(pattern))
            )
        )

    def update_student(self, student: Student, **fields) -> Student:
        """Обновляет данные ученика.

        Args:
            student: объект ученика.
            **fields: новые значения полей.

        Returns:
            Обновлённый объект Student.

        Raises:
            ValueError: если попытка установить недопустимый статус.
        """
        if "status" in fields and fields["status"] not in self.VALID_STATUSES:
            raise ValueError(f"Недопустимый статус: {fields['status']}")
        return self.repo.update(student, **fields)

    def delete_student(self, student: Student) -> None:
        """Удаляет ученика вместе со связями с группами.

        Args:
            student: объект ученика.
        """
        for link in list(student.groups):
            self.session.delete(link)
        self.repo.delete(student)

    def add_to_group(self, student: Student, group_id: int) -> GroupStudent:
        """Зачисляет ученика в группу.

        Args:
            student: объект ученика.
            group_id: идентификатор группы.

        Returns:
            Созданная запись GroupStudent.
        """
        link = GroupStudent(
            group_id=group_id, student_id=student.student_id, joined_date=date.today()
        )
        self.session.add(link)
        self.session.commit()
        return link
