from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from typing import List
import schemas
from api.dependencies import get_db

router = APIRouter()


@router.get("/", response_model=List[schemas.UserResponse])
def get_all_users(db: Session = Depends(get_db)):
    """Fetch all users with balances."""
    users = db.query(schemas.User).all()
    return users


@router.post("/seed", status_code=status.HTTP_201_CREATED)
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


@router.get("/{user_id}/transactions")
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

