from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from app.models import CreditEntry, Job, User


def balance(db, user_id):
    return db.scalar(select(func.coalesce(func.sum(CreditEntry.delta), 0)).where(CreditEntry.user_id == user_id)) or 0


def refund(db, job: Job):
    # All ledger mutations serialize on the owner's row. Unique indexes back idempotence.
    db.scalar(select(User).where(User.id == job.user_id).with_for_update())
    db.execute(insert(CreditEntry).values(user_id=job.user_id, delta=job.cost, reason="refund",
               job_id=job.id, reference=f"refund-{job.id}").on_conflict_do_nothing())
