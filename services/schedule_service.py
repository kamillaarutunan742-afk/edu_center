"""Сервис расписания: занятия, проверка конфликтов."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from database.models import Group, Schedule
from repositories.base_repository import BaseRepository

DAYS = (
    "Понедельник",
    "Вторник",
    "Среда",
    "Четверг",
    "Пятница",
    "Суббота",
    "Воскресенье",
)


class ScheduleService:
    """Бизнес-логика расписания."""

    def __init__(self, session: Session) -> None:
        """Инициализирует сервис.

        Args:
            session: сессия SQLAlchemy.
        """
        self.session = session
        self.repo = BaseRepository(Schedule, session)

    def get_all(self) -> list[Schedule]:
        """Возвращает все занятия."""
        return list(self.session.scalars(select(Schedule)))

    def _norm_time(self, value: str) -> str:
        """Приводит время к формату ЧЧ:ММ.

        Args:
            value: время строкой («18:00», «18.30», «6:00pm» и т. п.).

        Returns:
            Строка «ЧЧ:ММ» или исходная строка, если разобрать не удалось.
        """
        text = str(value).strip().replace(".", ":").replace("-", ":")
        parts = text.split(":")
        try:
            hours, minutes = int(parts[0]), int(parts[1])
            return f"{hours:02d}:{minutes:02d}"
        except (IndexError, ValueError):
            return str(value)

    def find_conflict(self, group_id: int, day: str, start: str, place: str):
        """Ищет конфликтующее занятие по кабинету или преподавателю.

        Args:
            group_id: идентификатор группы нового занятия.
            day: день недели.
            start: время начала.
            place: кабинет.

        Returns:
            Конфликтующий объект Schedule или None.

        Raises:
            ValueError: если группа не найдена.
        """
        group = self.session.get(Group, group_id)
        if group is None:
            raise ValueError("Группа не найдена")
        start_norm = self._norm_time(start)
        for item in self.session.scalars(
            select(Schedule).where(Schedule.day_of_week == day)
        ):
            if self._norm_time(item.start_time) != start_norm:
                continue
            item_room = getattr(item, "room", "") or getattr(item, "cabinet", "") or ""
            if place and item_room and item_room == place:
                return item
            item_group = self.session.get(Group, item.group_id)
            if (
                group.teacher_id is not None
                and item_group is not None
                and item_group.teacher_id == group.teacher_id
                and item.group_id != group_id
            ):
                return item
        return None

    def create_lesson(
        self, group_id: int, day: str, start: str, end: str = "", room: str = ""
    ) -> Schedule:
        """Создаёт занятие с проверкой конфликта.

        Args:
            group_id: идентификатор группы.
            day: день недели.
            start: время начала.
            end: время окончания (опционально).
            room: кабинет (опционально).

        Returns:
            Созданный объект Schedule.

        Raises:
            ValueError: при пустых полях или конфликте расписания.
        """
        if not day or not start:
            raise ValueError("Выберите день и укажите время начала")
        conflict = self.find_conflict(group_id, day, start, room)
        if conflict is not None:
            group = self.session.get(Group, conflict.group_id)
            name = group.name if group else "другой группой"
            raise ValueError(
                f"Конфликт расписания: в {day} в {self._norm_time(start)} "
                f"занято ({name})"
            )
        kwargs = {
            "group_id": group_id,
            "day_of_week": day,
            "start_time": self._norm_time(start),
        }
        if end and hasattr(Schedule, "end_time"):
            kwargs["end_time"] = self._norm_time(end)
        if room:
            if hasattr(Schedule, "room"):
                kwargs["room"] = room
            elif hasattr(Schedule, "cabinet"):
                kwargs["cabinet"] = room
        return self.repo.create(**kwargs)

    def delete(self, lesson: Schedule) -> None:
        """Удаляет занятие.

        Args:
            lesson: объект Schedule.
        """
        self.session.delete(lesson)
        self.session.commit()

    def get_table_rows(self) -> list[tuple]:
        """Собирает строки для таблицы расписания.

        Returns:
            Кортежи (id, день, время, группа, преподаватель, кабинет).
        """
        rows = []
        for item in self.get_all():
            group = self.session.get(Group, item.group_id)
            name = group.name if group else "—"
            teacher = (
                group.teacher.full_name
                if (group is not None and group.teacher is not None)
                else "—"
            )
            room = getattr(item, "room", None) or getattr(item, "cabinet", None) or "—"
            end = getattr(item, "end_time", None)
            time_text = self._norm_time(item.start_time)
            if end:
                time_text = f"{time_text}–{self._norm_time(end)}"
            rows.append(
                (
                    getattr(item, "schedule_id", 0),
                    item.day_of_week,
                    time_text,
                    name,
                    teacher,
                    room,
                )
            )
        rows.sort(key=lambda r: (DAYS.index(r[1]) if r[1] in DAYS else 99, r[2]))
        return rows
