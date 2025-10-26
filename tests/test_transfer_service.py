import pytest
from fastapi import HTTPException
from datetime import date
import schemas
from services.transfer_service import TransferService


class TestTransferService:
    """Test TransferService business logic."""
    
    def test_validate_transfer_success(self, db_session, sample_users):
        """Test successful transfer validation."""
        service = TransferService(db_session)
        sender = sample_users[0]
        receiver = sample_users[1]
        
        # Should not raise any exception
        service.validate_transfer_request(sender, receiver, 500)
    
    def test_validate_transfer_zero_amount(self, db_session, sample_users):
        """Test validation fails for zero amount."""
        service = TransferService(db_session)
        sender = sample_users[0]
        receiver = sample_users[1]
        
        with pytest.raises(HTTPException) as exc_info:
            service.validate_transfer_request(sender, receiver, 0)
        assert exc_info.value.status_code == 400
        assert "Invalid transfer amount" in str(exc_info.value.detail)
    
    def test_validate_transfer_same_account(self, db_session, sample_users):
        """Test validation fails for same account transfer."""
        service = TransferService(db_session)
        sender = sample_users[0]
        
        with pytest.raises(HTTPException) as exc_info:
            service.validate_transfer_request(sender, sender, 500)
        assert exc_info.value.status_code == 400
        assert "Cannot transfer to the same account" in str(exc_info.value.detail)
    
    def test_validate_transfer_insufficient_funds(self, db_session, sample_users):
        """Test validation fails for insufficient funds."""
        service = TransferService(db_session)
        sender = sample_users[2]  # user3 has 1000
        receiver = sample_users[0]
        
        with pytest.raises(HTTPException) as exc_info:
            service.validate_transfer_request(sender, receiver, 2000)
        assert exc_info.value.status_code == 400
        assert "Insufficient funds" in str(exc_info.value.detail)
    
    def test_validate_transfer_exceeds_daily_limit(self, db_session, sample_users):
        """Test validation fails when exceeding daily limit."""
        service = TransferService(db_session)
        sender = sample_users[0]
        receiver = sample_users[1]
        
        with pytest.raises(HTTPException) as exc_info:
            service.validate_transfer_request(sender, receiver, 2500)
        assert exc_info.value.status_code == 400
        assert "exceeds daily limit" in str(exc_info.value.detail)
    
    def test_execute_transfer_success(self, db_session, sample_users):
        """Test successful transfer execution."""
        service = TransferService(db_session)
        sender = sample_users[0]
        receiver = sample_users[1]
        initial_sender_balance = sender.Amount
        initial_receiver_balance = receiver.Amount
        
        result = service.execute_transfer(sender, receiver, 500)
        
        assert result["message"] == "Transfer successful"
        assert result["sender"]["balance"] == initial_sender_balance - 500
        assert result["receiver"]["balance"] == initial_receiver_balance + 500
        
        # Verify transactions were created
        transactions = db_session.query(schemas.Transaction).all()
        assert len(transactions) == 2
