"""Сервис абонементов: продажа, списание занятий, продление."""

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from database.models import Subscription, SubscriptionType
from repositories.base_repository import BaseRepository


class SubscriptionService:
    """Бизнес-логика абонементов."""

    def __init__(self, session: Session) -> None:
        """Инициализирует сервис.

        Args:
            session: сессия SQLAlchemy.
        """
        self.session = session
        self.repo = BaseRepository(Subscription, session)

    def get_all_types(self) -> list[SubscriptionType]:
        """Возвращает все типы абонементов."""
        return list(self.session.scalars(select(SubscriptionType)))

    def create_type(self, name: str, lessons_count: int, price: float) -> SubscriptionType:
        """Создаёт тип абонемента.

        Args:
            name: название (например, «Абонемент на 8 занятий»).
            lessons_count: количество занятий.
            price: стоимость.

        Returns:
            Созданный объект SubscriptionType.

        Raises:
            ValueError: при некорректном количестве занятий или цене.
        """
        if lessons_count <= 0:
            raise ValueError("Количество занятий должно быть положительным")
        if price < 0:
            raise ValueError("Цена не может быть отрицательной")
        return self.session.merge(
            SubscriptionType(name=name, lessons_count=lessons_count, price=price)
        )

    def sell_subscription(self, student_id: int, type_id: int) -> Subscription:
        """Продаёт абонемент ученику.

        Args:
            student_id: идентификатор ученика.
            type_id: идентификатор типа абонемента.

        Returns:
            Созданный объект Subscription.

        Raises:
            ValueError: если тип абонемента не найден.
        """
        sub_type = self.session.get(SubscriptionType, type_id)
        if sub_type is None:
            raise ValueError("Тип абонемента не найден")
        return self.repo.create(
            student_id=student_id,
            type_id=type_id,
            start_date=date.today(),
            total_lessons=sub_type.lessons_count,
            remaining_lessons=sub_type.lessons_count,
            status="active",
        )

    def spend_lesson(self, subscription: Subscription) -> Subscription:
        """Списывает одно занятие с абонемента.

        При исчерпании занятий статус меняется на «expired».

        Args:
            subscription: объект абонемента.

        Returns:
            Обновлённый абонемент.

        Raises:
            ValueError: если на абонементе не осталось занятий.
        """
        if subscription.remaining_lessons <= 0:
            raise ValueError("На абонементе не осталось занятий")
        subscription.remaining_lessons -= 1
        if subscription.remaining_lessons == 0:
            subscription.status = "expired"
        self.session.commit()
        return subscription

    def get_student_subscriptions(self, student_id: int) -> list[Subscription]:
        """Возвращает все абонементы ученика.

        Args:
            student_id: идентификатор ученика.

        Returns:
            Список абонементов.
        """
        return list(
            self.session.scalars(
                select(Subscription).where(Subscription.student_id == student_id)
            )
        )

    def find_active_subscription(self, student_id: int) -> Subscription | None:
        """Ищет активный абонемент с оставшимися занятиями.

        Используется при отметке посещаемости: занятие списывается
        с первого активного абонемента.

        Args:
            student_id: идентификатор ученика.

        Returns:
            Активный абонемент или None.
        """
        return self.session.scalar(
            select(Subscription).where(
                Subscription.student_id == student_id,
                Subscription.status == "active",
                Subscription.remaining_lessons > 0,
            )
        )
