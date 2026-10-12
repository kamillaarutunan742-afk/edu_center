"""Наполнение базы тестовыми данными для разработки и демонстрации."""

import sys
from pathlib import Path

# Добавляем корень проекта в путь поиска модулей,
# чтобы скрипт можно было запускать из любого места
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from database.db import SessionLocal, init_db
from database.models import Student, SubscriptionType, Teacher, User
from services.auth_service import hash_password
from services.group_service import GroupService
from services.student_service import StudentService
from services.subscription_service import SubscriptionService

"""Наполнение базы тестовыми данными для разработки и демонстрации."""

from database.db import SessionLocal, init_db
from database.models import Student, SubscriptionType, Teacher
from services.auth_service import hash_password
from services.group_service import GroupService
from services.student_service import StudentService
from services.subscription_service import SubscriptionService


def main() -> None:
    """Создаёт тестовые преподавателей, группы, учеников и абонементы."""
    init_db()
    session = SessionLocal()

    if session.query(Student).count() > 0:
        print("База уже содержит данные — сид пропущен")
        return

    # Администратор (логин admin, пароль admin)
    from database.models import User

    session.add(
        User(
            login="admin",
            password_hash=hash_password("admin"),
            role="admin",
            full_name="Администратор",
        )
    )
    session.commit()

    # Преподаватель
    session.add(Teacher(full_name="Иванова Мария Петровна", phone="+7-900-100-20-30", subjects="Математика"))
    session.commit()

    # Группы
    groups = GroupService(session)
    groups.create_group(name="Математика 7А", direction="Математика", age_category="12-14", level="beginner", capacity=10)

    # Ученики
    students = StudentService(session)
    s1 = students.create_student(full_name="Пётр Смирнов", phone="+7-900-111-22-33", birth_date=None)
    s2 = students.create_student(full_name="Анна Козлова", phone="+7-900-222-33-44")
    groups.add_student(groups.get_all_groups()[0], s1.student_id)
    groups.add_student(groups.get_all_groups()[0], s2.student_id)

    # Типы абонементов и продажи
    subs = SubscriptionService(session)
    t8 = subs.create_type("Абонемент на 8 занятий", 8, 4000)
    subs.sell_subscription(s1.student_id, t8.type_id)
    subs.sell_subscription(s2.student_id, t8.type_id)

    print("Тестовые данные добавлены!")
    session.close()


if __name__ == "__main__":
    main()
