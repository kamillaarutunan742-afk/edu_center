"""Сервис платежей: регистрация оплат и отчёт по выручке."""

from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from database.models import Payment
from repositories.base_repository import BaseRepository


class PaymentService:
    """Бизнес-логика платежей."""

    def __init__(self, session: Session) -> None:
        """Инициализирует сервис.

        Args:
            session: сессия SQLAlchemy.
        """
        self.session = session
        self.repo = BaseRepository(Payment, session)

    def register_payment(self, student_id: int, amount: float, subscription_id: int | None = None) -> Payment:
        """Регистрирует оплату.

        Args:
            student_id: идентификатор ученика.
            amount: сумма платежа.
            subscription_id: связанный абонемент (если есть).

        Returns:
            Созданный объект Payment.

        Raises:
            ValueError: если сумма не положительная.
        """
        if amount <= 0:
            raise ValueError("Сумма платежа должна быть положительной")
        return self.repo.create(
            student_id=student_id,
            amount=amount,
            subscription_id=subscription_id,
            payment_date=date.today(),
        )

    def get_student_payments(self, student_id: int) -> list[Payment]:
        """Возвращает платежи ученика."""
        return list(
            self.session.scalars(
                select(Payment)
                .where(Payment.student_id == student_id)
                .order_by(Payment.payment_date)
            )
        )

    def get_revenue(self, start: date, end: date) -> float:
        """Считает выручку за период (для отчётов и Dashboard).

        Args:
            start: начало периода (включительно).
            end: конец периода (включительно).

        Returns:
            Сумма платежей за период; 0.0, если платежей нет.
        """
        total = self.session.scalar(
            select(func.sum(Payment.amount)).where(
                Payment.payment_date >= start, Payment.payment_date <= end
            )
        )
        return float(total or 0.0)
