import pytest
from fastapi import status
from datetime import date, timedelta


class TestImmediateTransfers:
    """Test immediate money transfer functionality."""
    
    def test_successful_transfer(self, client, sample_users):
        """Test a successful money transfer."""
        transfer_data = {
            "sender_id": 1,
            "receiver_account": 1000000002,
            "amount": 500
        }
        
        response = client.post("/transfers/immediate", json=transfer_data)
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert data["message"] == "Transfer successful"
        assert data["sender"]["balance"] == 4500
        assert data["sender"]["daily_limit_remaining"] == 1500
        assert data["receiver"]["balance"] == 3500
    
    def test_transfer_sender_not_found(self, client):
        """Test transfer with non-existent sender."""
        transfer_data = {
            "sender_id": 999,
            "receiver_account": 1000000002,
            "amount": 500
        }
        
        response = client.post("/transfers/immediate", json=transfer_data)
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "Sender not found" in response.json()["detail"]
    
    def test_transfer_receiver_not_found(self, client, sample_users):
        """Test transfer with non-existent receiver."""
        transfer_data = {
            "sender_id": 1,
            "receiver_account": 9999999999,
            "amount": 500
        }
        
        response = client.post("/transfers/immediate", json=transfer_data)
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "Receiver account not found" in response.json()["detail"]
    
    def test_transfer_insufficient_funds(self, client, sample_users):
        """Test transfer with insufficient funds."""
        transfer_data = {
            "sender_id": 3,  # user3 has only 1000
            "receiver_account": 1000000001,
            "amount": 2000
        }
        
        response = client.post("/transfers/immediate", json=transfer_data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Insufficient funds" in response.json()["detail"]
    
    def test_transfer_invalid_amount_zero(self, client, sample_users):
        """Test transfer with zero amount."""
        transfer_data = {
            "sender_id": 1,
            "receiver_account": 1000000002,
            "amount": 0
        }
        
        response = client.post("/transfers/immediate", json=transfer_data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Invalid transfer amount" in response.json()["detail"]
    
    def test_transfer_invalid_amount_negative(self, client, sample_users):
        """Test transfer with negative amount."""
        transfer_data = {
            "sender_id": 1,
            "receiver_account": 1000000002,
            "amount": -500
        }
        
        response = client.post("/transfers/immediate", json=transfer_data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Invalid transfer amount" in response.json()["detail"]
    
    def test_transfer_to_same_account(self, client, sample_users):
        """Test transfer to the same account."""
        transfer_data = {
            "sender_id": 1,
            "receiver_account": 1000000001,  # Same as sender
            "amount": 500
        }
        
        response = client.post("/transfers/immediate", json=transfer_data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Cannot transfer to the same account" in response.json()["detail"]
    
    def test_transfer_exceeds_daily_limit(self, client, sample_users):
        """Test transfer that exceeds daily limit."""
        transfer_data = {
            "sender_id": 1,
            "receiver_account": 1000000002,
            "amount": 2500  # Exceeds daily limit of 2000
        }
        
        response = client.post("/transfers/immediate", json=transfer_data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "exceeds daily limit" in response.json()["detail"]
    
    def test_multiple_transfers_within_limit(self, client, sample_users):
        """Test multiple transfers within daily limit."""
        # First transfer
        transfer1 = {
            "sender_id": 1,
            "receiver_account": 1000000002,
            "amount": 1000
        }
        response1 = client.post("/transfers/immediate", json=transfer1)
        assert response1.status_code == status.HTTP_200_OK
        assert response1.json()["sender"]["daily_limit_remaining"] == 1000
        
        # Second transfer
        transfer2 = {
            "sender_id": 1,
            "receiver_account": 1000000002,
            "amount": 500
        }
        response2 = client.post("/transfers/immediate", json=transfer2)
        assert response2.status_code == status.HTTP_200_OK
        assert response2.json()["sender"]["daily_limit_remaining"] == 500
    
    def test_transfer_after_exceeding_limit(self, client, sample_users):
        """Test that transfer fails after limit is exceeded."""
        # First transfer uses up most of the limit
        transfer1 = {
            "sender_id": 1,
            "receiver_account": 1000000002,
            "amount": 1500
        }
        client.post("/transfers/immediate", json=transfer1)
        
        # Second transfer should fail
        transfer2 = {
            "sender_id": 1,
            "receiver_account": 1000000002,
            "amount": 1000
        }
        response = client.post("/transfers/immediate", json=transfer2)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "exceeds daily limit" in response.json()["detail"]


class TestScheduledTransfers:
    """Test scheduled money transfer functionality."""
    
    def test_schedule_transfer_future_date(self, client, sample_users):
        """Test scheduling a transfer for a future date."""
        future_date = (date.today() + timedelta(days=1)).isoformat()
        transfer_data = {
            "sender_id": 1,
            "receiver_account": 1000000002,
            "amount": 500,
            "scheduled_date": future_date
        }
        
        response = client.post("/transfers/scheduled", json=transfer_data)
        assert response.status_code == status.HTTP_202_ACCEPTED
        
        data = response.json()
        assert "task_id" in data
        assert data["message"] == "Transfer scheduled successfully"
        assert data["scheduled_date"] == future_date
    
    def test_schedule_transfer_past_date(self, client, sample_users):
        """Test scheduling a transfer for a past date."""
        past_date = (date.today() - timedelta(days=1)).isoformat()
        transfer_data = {
            "sender_id": 1,
            "receiver_account": 1000000002,
            "amount": 500,
            "scheduled_date": past_date
        }
        
        response = client.post("/transfers/scheduled", json=transfer_data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "must be in the future" in response.json()["detail"]
    
    def test_schedule_transfer_invalid_sender(self, client, sample_users):
        """Test scheduling transfer with invalid sender."""
        future_date = (date.today() + timedelta(days=1)).isoformat()
        transfer_data = {
            "sender_id": 999,
            "receiver_account": 1000000002,
            "amount": 500,
            "scheduled_date": future_date
        }
        
        response = client.post("/transfers/scheduled", json=transfer_data)
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "Sender not found" in response.json()["detail"]

