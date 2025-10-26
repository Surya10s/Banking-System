from fastapi import HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from datetime import date
import schemas


class TransferService:
    """Handle transfer operations and validations."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def validate_transfer_request(
        self,
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
    
    def execute_transfer(
        self,
        sender: schemas.User,
        receiver: schemas.User,
        amount: float
    ) -> dict:
        """Execute the money transfer."""
        
        # Validate transfer
        self.validate_transfer_request(sender, receiver, amount)
        
        try:
            # Update balances
            sender.Amount -= amount
            sender.daily_used -= amount
            receiver.Amount += amount

            # Create transaction records
            sender_txn = schemas.Transaction(
                user_id=sender.id,
                account_no=sender.AccountNo,
                amount=-amount,
                transaction_type="debit"
            )

            receiver_txn = schemas.Transaction(
                user_id=receiver.id,
                account_no=receiver.AccountNo,
                amount=amount,
                transaction_type="credit"
            )

            self.db.add_all([sender_txn, receiver_txn])
            self.db.commit()
            self.db.refresh(sender)
            self.db.refresh(receiver)

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
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Transaction failed: {str(e)}"
            )