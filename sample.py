from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from db import engine, sessionLocal
import schemas
from typing import List
from datetime import date, datetime
from celery_worker import schedule_money_transfer, celery_app

app = FastAPI(
    title="Money Transfer API",
    description="API for managing user accounts and money transfers",
    version="1.0.0"
)

# Create all tables
schemas.Base.metadata.create_all(bind=engine)


# Dependency for DB session
def get_db():
    """Database session dependency."""
    db = sessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get("/")
def home():
    """Health check endpoint."""
    return {"message": "Server is running successfully"}


@app.get("/users", response_model=List[schemas.UserResponse])
def get_all_users(db: Session = Depends(get_db)):
    """Fetch all users with balances."""
    users = db.query(schemas.User).all()
    return users


@app.post("/seed", status_code=status.HTTP_201_CREATED)
def seed_data(db: Session = Depends(get_db)):
    """Seed 10 users into the database with initial balance."""
    try:
        db.query(schemas.User).delete()
        users = [
            schemas.User(
                Amount=5000,
                username=f"user{i}",
                AccountNo=1000000000 + i
            )
            for i in range(1, 11)
        ]
        db.add_all(users)
        db.commit()
        return {"message": "10 users seeded successfully"}
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}"
        )


@app.get("/transactions/{user_id}")
def get_user_transactions(
    user_id: int,
    db: Session = Depends(get_db)
):
    """Get all transactions for a specific user."""
    user = db.query(schemas.User).filter(schemas.User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    transactions = (
        db.query(schemas.Transaction)
        .filter(schemas.Transaction.user_id == user_id)
        .order_by(schemas.Transaction.timestamp.desc())
        .all()
    )
    return transactions


def validate_transfer(
    sender: schemas.User,
    receiver: schemas.User,
    amount: float
) -> None:
    """Validate transfer constraints."""
    if amount <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid transfer amount"
        )
    
    if sender.AccountNo == receiver.AccountNo:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot transfer to the same account"
        )
    
    if sender.Amount < amount:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Insufficient funds"
        )
    
    # Reset daily limit if needed
    if sender.last_reset != date.today():
        sender.daily_used = 2000
        sender.last_reset = date.today()
    
    if amount > sender.daily_used:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Transfer exceeds daily limit of {sender.daily_used}"
        )


@app.post("/money-transfer", status_code=status.HTTP_200_OK)
def money_transfer(
    request: schemas.TransferRequest,
    db: Session = Depends(get_db)
):
    """Immediate money transfer between accounts."""
    
    # Fetch sender
    sender = db.query(schemas.User).filter(
        schemas.User.id == request.sender_id
    ).first()
    if not sender:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sender not found"
        )

    # Fetch receiver
    receiver = db.query(schemas.User).filter(
        schemas.User.AccountNo == request.receiver_account
    ).first()
    if not receiver:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Receiver account not found"
        )

    # Validate transfer
    validate_transfer(sender, receiver, request.amount)

    try:
        # Update balances
        sender.Amount -= request.amount
        sender.daily_used -= request.amount
        receiver.Amount += request.amount

        # Create transaction records
        sender_txn = schemas.Transaction(
            user_id=sender.id,
            account_no=sender.AccountNo,
            amount=-request.amount,
            transaction_type="debit"
        )

        receiver_txn = schemas.Transaction(
            user_id=receiver.id,
            account_no=receiver.AccountNo,
            amount=request.amount,
            transaction_type="credit"
        )

        db.add_all([sender_txn, receiver_txn])
        db.commit()
        db.refresh(sender)
        db.refresh(receiver)

        return {
            "message": "Transfer successful",
            "sender": {
                "username": sender.username,
                "balance": sender.Amount,
                "daily_limit_remaining": sender.daily_used
            },
            "receiver": {
                "username": receiver.username,
                "balance": receiver.Amount
            }
        }

    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Transaction failed: {str(e)}"
        )


@app.post("/scheduled-money-transfer", status_code=status.HTTP_202_ACCEPTED)
def scheduled_money_transfer(
    request: schemas.ScheduledTransferRequest,
    db: Session = Depends(get_db)
):
    """Schedule a money transfer for a future date."""
    
    # Validate sender exists
    sender = db.query(schemas.User).filter(
        schemas.User.id == request.sender_id
    ).first()
    if not sender:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sender not found"
        )

    # Validate receiver exists
    receiver = db.query(schemas.User).filter(
        schemas.User.AccountNo == request.receiver_account
    ).first()
    if not receiver:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Receiver account not found"
        )

    # Validate amount
    if request.amount <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid transfer amount"
        )
    
    # Validate accounts are different
    if sender.AccountNo == receiver.AccountNo:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot transfer to the same account"
        )
    
    # Validate scheduled date
    try:
        scheduled_datetime = datetime.combine(
            request.scheduled_date,
            datetime.min.time()
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid date format: {str(e)}"
        )
    
    if scheduled_datetime < datetime.now():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Scheduled date must be in the future"
        )
    
    # Schedule the transfer using Celery
    try:
        task = schedule_money_transfer.apply_async(
            args=[request.sender_id, request.receiver_account, request.amount],
            eta=scheduled_datetime
        )
        
        return {
            "message": "Transfer scheduled successfully",
            "task_id": task.id,
            "scheduled_date": request.scheduled_date.isoformat(),
            "sender_username": sender.username,
            "receiver_username": receiver.username,
            "amount": request.amount
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to schedule transfer: {str(e)}"
        )


@app.get("/task-status/{task_id}")
def get_task_status(task_id: str):
    """Check the status of a scheduled transfer task."""
    task = celery_app.AsyncResult(task_id)
    
    response = {
        "task_id": task_id,
        "status": task.state.lower()
    }
    
    if task.state == 'PENDING':
        response["message"] = "Transfer is scheduled and waiting to be executed"
    elif task.state == 'SUCCESS':
        response["result"] = task.result
    elif task.state == 'FAILURE':
        response["error"] = str(task.info)
    
    return response