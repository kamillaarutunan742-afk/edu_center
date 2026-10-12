"""ORM-модели базы данных учебного центра.

Каждый класс соответствует таблице из ER-диаграммы ТЗ.
Используется SQLAlchemy 2.0: декларативный стиль, связи через
relationship (ленивая загрузка связанных объектов по умолчанию).
"""

from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    Time,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Базовый класс для всех ORM-моделей проекта."""


class User(Base):
    """Пользователь системы (администратор, администратор и т.д.)."""

    __tablename__ = "users"

    user_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    login: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    full_name: Mapped[str] = mapped_column(String(150), nullable=False)
    email: Mapped[str] = mapped_column(String(100))
    last_login: Mapped[datetime | None] = mapped_column(DateTime)

    teacher: Mapped["Teacher | None"] = relationship(
        back_populates="user", uselist=False
    )

    def __repr__(self) -> str:
        """Строковое представление для отладки."""
        return f"<User {self.login} ({self.role})>"


class Teacher(Base):
    """Преподаватель учебного центра."""

    __tablename__ = "teachers"

    teacher_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.user_id"))
    full_name: Mapped[str] = mapped_column(String(150), nullable=False)
    phone: Mapped[str] = mapped_column(String(20))
    subjects: Mapped[str] = mapped_column(String(255))
    hire_date: Mapped[date | None] = mapped_column(Date)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    user: Mapped["User | None"] = relationship(back_populates="teacher")
    groups: Mapped[list["Group"]] = relationship(back_populates="teacher")
    schedule: Mapped[list["Schedule"]] = relationship(back_populates="teacher")

    def __repr__(self) -> str:
        """Строковое представление для отладки."""
        return f"<Teacher {self.full_name}>"


class Group(Base):
    """Учебная группа."""

    __tablename__ = "groups"

    group_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    teacher_id: Mapped[int | None] = mapped_column(ForeignKey("teachers.teacher_id"))
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    direction: Mapped[str] = mapped_column(String(100))
    age_category: Mapped[str] = mapped_column(String(20))
    level: Mapped[str] = mapped_column(String(20))
    capacity: Mapped[int] = mapped_column(Integer, default=15)
    start_date: Mapped[date | None] = mapped_column(Date)

    teacher: Mapped["Teacher | None"] = relationship(back_populates="groups")
    students: Mapped[list["GroupStudent"]] = relationship(back_populates="group")
    schedule: Mapped[list["Schedule"]] = relationship(back_populates="group")

    def __repr__(self) -> str:
        """Строковое представление для отладки."""
        return f"<Group {self.name}>"


class Student(Base):
    """Ученик учебного центра."""

    __tablename__ = "students"

    student_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    full_name: Mapped[str] = mapped_column(String(150), nullable=False)
    birth_date: Mapped[date | None] = mapped_column(Date)
    phone: Mapped[str] = mapped_column(String(20))
    email: Mapped[str] = mapped_column(String(100))
    direction: Mapped[str] = mapped_column(String(100))
    level: Mapped[str] = mapped_column(String(20))
    enroll_date: Mapped[date | None] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(20), default="active")
    parent_name: Mapped[str] = mapped_column(String(150))

    groups: Mapped[list["GroupStudent"]] = relationship(back_populates="student")
    subscriptions: Mapped[list["Subscription"]] = relationship(
        back_populates="student"
    )
    payments: Mapped[list["Payment"]] = relationship(back_populates="student")
    notifications: Mapped[list["Notification"]] = relationship(
        back_populates="student"
    )

    def __repr__(self) -> str:
        """Строковое представление для отладки."""
        return f"<Student {self.full_name}>"


class GroupStudent(Base):
    """Связующая таблица «ученик — группа» (многие ко многим)."""

    __tablename__ = "group_students"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    group_id: Mapped[int] = mapped_column(
        ForeignKey("groups.group_id"), nullable=False
    )
    student_id: Mapped[int] = mapped_column(
        ForeignKey("students.student_id"), nullable=False
    )
    joined_date: Mapped[date | None] = mapped_column(Date)

    group: Mapped["Group"] = relationship(back_populates="students")
    student: Mapped["Student"] = relationship(back_populates="groups")

    def __repr__(self) -> str:
        """Строковое представление для отладки."""
        return f"<GroupStudent group={self.group_id} student={self.student_id}>"


class Schedule(Base):
    """Расписание занятий группы."""

    __tablename__ = "schedule"

    schedule_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    group_id: Mapped[int] = mapped_column(
        ForeignKey("groups.group_id"), nullable=False
    )
    teacher_id: Mapped[int | None] = mapped_column(ForeignKey("teachers.teacher_id"))
    day_of_week: Mapped[str] = mapped_column(String(15), nullable=False)
    start_time: Mapped[str] = mapped_column(Time, nullable=False)
    end_time: Mapped[str] = mapped_column(Time, nullable=False)

    group: Mapped["Group"] = relationship(back_populates="schedule")
    teacher: Mapped["Teacher | None"] = relationship(back_populates="schedule")
    attendance: Mapped[list["Attendance"]] = relationship(back_populates="schedule")

    def __repr__(self) -> str:
        """Строковое представление для отладки."""
        return f"<Schedule {self.day_of_week} {self.start_time}>"


class SubscriptionType(Base):
    """Тип абонемента (например, «8 занятий», «16 занятий»)."""

    __tablename__ = "subscription_types"

    type_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    lessons_count: Mapped[int] = mapped_column(Integer, nullable=False)
    price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)

    subscriptions: Mapped[list["Subscription"]] = relationship(
        back_populates="subscription_type"
    )

    def __repr__(self) -> str:
        """Строковое представление для отладки."""
        return f"<SubscriptionType {self.name}>"


class Subscription(Base):
    """Абонемент, купленный учеником."""

    __tablename__ = "subscriptions"

    subscription_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    student_id: Mapped[int] = mapped_column(
        ForeignKey("students.student_id"), nullable=False
    )
    type_id: Mapped[int] = mapped_column(
        ForeignKey("subscription_types.type_id"), nullable=False
    )
    start_date: Mapped[date | None] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)
    total_lessons: Mapped[int] = mapped_column(Integer, nullable=False)
    remaining_lessons: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="active")

    student: Mapped["Student"] = relationship(back_populates="subscriptions")
    subscription_type: Mapped["SubscriptionType"] = relationship(
        back_populates="subscriptions"
    )
    payments: Mapped[list["Payment"]] = relationship(back_populates="subscription")
    attendance: Mapped[list["Attendance"]] = relationship(
        back_populates="subscription"
    )
    notifications: Mapped[list["Notification"]] = relationship(
        back_populates="subscription"
    )

    def __repr__(self) -> str:
        """Строковое представление для отладки."""
        return f"<Subscription #{self.subscription_id} {self.remaining_lessons} lessons>"


class Attendance(Base):
    """Отметка посещаемости ученика на конкретном занятии."""

    __tablename__ = "attendance"

    attendance_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    student_id: Mapped[int] = mapped_column(
        ForeignKey("students.student_id"), nullable=False
    )
    group_id: Mapped[int] = mapped_column(
        ForeignKey("groups.group_id"), nullable=False
    )
    schedule_id: Mapped[int | None] = mapped_column(
        ForeignKey("schedule.schedule_id")
    )
    subscription_id: Mapped[int | None] = mapped_column(
        ForeignKey("subscriptions.subscription_id")
    )
    lesson_date: Mapped[date | None] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(20), default="present")

    schedule: Mapped["Schedule | None"] = relationship(back_populates="attendance")
    subscription: Mapped["Subscription | None"] = relationship(
        back_populates="attendance"
    )

    def __repr__(self) -> str:
        """Строковое представление для отладки."""
        return f"<Attendance student={self.student_id} {self.lesson_date} {self.status}>"


class Payment(Base):
    """Платёж за абонемент."""

    __tablename__ = "payments"

    payment_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    subscription_id: Mapped[int | None] = mapped_column(
        ForeignKey("subscriptions.subscription_id")
    )
    student_id: Mapped[int] = mapped_column(
        ForeignKey("students.student_id"), nullable=False
    )
    amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    payment_date: Mapped[date | None] = mapped_column(Date)

    subscription: Mapped["Subscription | None"] = relationship(
        back_populates="payments"
    )
    student: Mapped["Student"] = relationship(back_populates="payments")

    def __repr__(self) -> str:
        """Строковое представление для отладки."""
        return f"<Payment {self.amount} от {self.payment_date}>"


class Notification(Base):
    """Уведомление (например, «абонемент заканчивается»)."""

    __tablename__ = "notifications"

    notification_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    subscription_id: Mapped[int | None] = mapped_column(
        ForeignKey("subscriptions.subscription_id")
    )
    type: Mapped[str] = mapped_column(String(50))
    message: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime, default=datetime.now
    )

    subscription: Mapped["Subscription | None"] = relationship(
        back_populates="notifications"
    )

    def __repr__(self) -> str:
        """Строковое представление для отладки."""
        return f"<Notification {self.type}: {self.message[:30]}>"
