from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from datetime import datetime
import schemas
from api.dependencies import get_db
from services.transfer_service import TransferService
from celery_worker import schedule_money_transfer

router = APIRouter()


@router.post("/immediate", status_code=status.HTTP_200_OK)
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

    # Validate and execute transfer
    transfer_service = TransferService(db)
    return transfer_service.execute_transfer(sender, receiver, request.amount)


@router.post("/scheduled", status_code=status.HTTP_202_ACCEPTED)
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

    # Validate transfer request
    transfer_service = TransferService(db)
    transfer_service.validate_transfer_request(
        sender, receiver, request.amount
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

