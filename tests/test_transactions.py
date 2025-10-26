import pytest
from fastapi import status


class TestTransactionEndpoints:
    """Test transaction-related endpoints."""
    
    def test_get_transactions_for_nonexistent_user(self, client):
        """Test getting transactions for a user that doesn't exist."""
        response = client.get("/users/999/transactions")
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "User not found" in response.json()["detail"]
    
    def test_get_transactions_empty(self, client, sample_users):
        """Test getting transactions when user has no transactions."""
        response = client.get("/users/1/transactions")
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == []
    
    def test_get_transactions_after_transfer(self, client, sample_users):
        """Test getting transactions after making a transfer."""
        # Make a transfer
        transfer_data = {
            "sender_id": 1,
            "receiver_account": 1000000002,
            "amount": 500
        }
        client.post("/transfers/immediate", json=transfer_data)
        
        # Check sender transactions
        response = client.get("/users/1/transactions")
        assert response.status_code == status.HTTP_200_OK
        transactions = response.json()
        assert len(transactions) == 1
        assert transactions[0]["transaction_type"] == "debit"
        assert transactions[0]["amount"] == -500
        
        # Check receiver transactions
        response = client.get("/users/2/transactions")
        transactions = response.json()
        assert len(transactions) == 1
        assert transactions[0]["transaction_type"] == "credit"
        assert transactions[0]["amount"] == 500
