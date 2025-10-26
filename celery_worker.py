from celery import Celery
from sqlalchemy.orm import Session
from db import sessionLocal
import schemas
from datetime import date

# Configure Celery
celery_app = Celery(
    "money_transfer_worker",
    broker="redis://localhost:6379/0",  # Use Redis as message broker
    backend="redis://localhost:6379/0"  # Use Redis as result backend
)

# Celery configuration
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
)


def get_db():
    """Get database session."""
    db = sessionLocal()
    try:
        return db
    finally:
        pass  # Don't close here, close in the task


@celery_app.task(bind=True, max_retries=3)
def schedule_money_transfer(self, sender_id: int, receiver_account: int, amount: float):
    """
    Celery task to process scheduled money transfer.
    
    Args:
        sender_id: ID of the sender
        receiver_account: Account number of the receiver
        amount: Amount to transfer
    """
    db = get_db()
    
    try:
        # Fetch sender
        sender = db.query(schemas.User).filter(schemas.User.id == sender_id).first()
        if not sender:
            return {"status": "failed", "error": "Sender not found"}

        # Fetch receiver
        receiver = db.query(schemas.User).filter(schemas.User.AccountNo == receiver_account).first()
        if not receiver:
            return {"status": "failed", "error": "Receiver account not found"}

        # Check if sender has sufficient balance
        if sender.Amount < amount:
            return {"status": "failed", "error": "Insufficient funds"}

        # Reset daily limit if it's a new day
        if sender.last_reset != date.today():
            sender.daily_used = 2000
            sender.last_reset = date.today()

        # Check daily limit
        if amount > sender.daily_used:
            return {"status": "failed", "error": f"Transfer exceeds daily limit of {sender.daily_used}"}

        # Perform the transfer
        sender.Amount -= amount
        sender.daily_used -= amount
        receiver.Amount += amount
        
        db.commit()
        db.refresh(sender)
        db.refresh(receiver)

        return {
            "status": "success",
            "message": "Scheduled transfer completed successfully",
            "sender": {
                "username": sender.username,
                "balance": sender.Amount,
                "daily_limit_remaining": sender.daily_used
            },
            "receiver": {
                "username": receiver.username,
                "balance": receiver.Amount
            },
            "amount": amount
        }

    except Exception as e:
        db.rollback()
        # Retry the task in case of temporary failures
        raise self.retry(exc=e, countdown=60)  # Retry after 60 seconds
    
    finally:
        db.close()