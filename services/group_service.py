"""Сервис учебных групп: CRUD и контроль наполненности."""

from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from database.models import Group, GroupStudent
from repositories.base_repository import BaseRepository


class GroupService:
    """Бизнес-логика работы с группами."""

    def __init__(self, session: Session) -> None:
        """Инициализирует сервис.

        Args:
            session: сессия SQLAlchemy.
        """
        self.session = session
        self.repo = BaseRepository(Group, session)

    def create_group(self, name: str, **fields) -> Group:
        """Создаёт группу с валидацией названия.

        Args:
            name: название группы (обязательно).
            **fields: остальные поля модели Group.

        Returns:
            Созданный объект Group.

        Raises:
            ValueError: если название пустое.
        """
        if not name.strip():
            raise ValueError("Название группы не может быть пустым")
        fields.setdefault("start_date", date.today())
        return self.repo.create(name=name.strip(), **fields)

    def get_group(self, group_id: int) -> Group | None:
        """Возвращает группу по идентификатору."""
        return self.repo.get_by_id(group_id)

    def get_all_groups(self) -> list[Group]:
        """Возвращает все группы."""
        return self.repo.get_all()

    def update_group(self, group: Group, **fields) -> Group:
        """Обновляет данные группы."""
        return self.repo.update(group, **fields)

    def delete_group(self, group: Group) -> None:
        """Удаляет группу и связи её учеников."""
        for link in list(group.students):
            self.session.delete(link)
        self.repo.delete(group)

    def get_students_count(self, group: Group) -> int:
        """Возвращает количество учеников в группе.

        Демонстрирует агрегацию средствами ORM (lazy loading по связи).

        Args:
            group: объект группы.

        Returns:
            Число учеников.
        """
        return len(group.students)

    def is_full(self, group: Group) -> bool:
        """Проверяет, заполнена ли группа.

        Args:
            group: объект группы.

        Returns:
            True, если свободных мест нет.
        """
        return self.get_students_count(group) >= (group.capacity or 0)

    def add_student(self, group: Group, student_id: int) -> None:
        """Зачисляет ученика в группу, если есть свободное место.

        Args:
            group: объект группы.
            student_id: идентификатор ученика.

        Raises:
            ValueError: если группа уже заполнена или ученик уже в ней.
        """
        if self.is_full(group):
            raise ValueError(f"Группа «{group.name}» заполнена")
        exists = self.session.scalar(
            select(GroupStudent).where(
                GroupStudent.group_id == group.group_id,
                GroupStudent.student_id == student_id,
            )
        )
        if exists:
            raise ValueError("Ученик уже состоит в этой группе")
        self.session.add(GroupStudent(group_id=group.group_id, student_id=student_id))
        self.session.commit()
