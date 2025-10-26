import pytest
from fastapi import status


class TestUserEndpoints:
    """Test user management endpoints."""
    
    def test_home_endpoint(self, client):
        """Test the home/health check endpoint."""
        response = client.get("/")
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {"message": "Server is running successfully"}
    
    def test_get_all_users_empty(self, client):
        """Test getting users when database is empty."""
        response = client.get("/users/")
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == []
    
    def test_get_all_users_with_data(self, client, sample_users):
        """Test getting all users with existing data."""
        response = client.get("/users/")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 3
        assert data[0]["username"] == "user1"
        assert data[0]["Amount"] == 5000
    
    def test_seed_data(self, client):
        """Test seeding the database."""
        response = client.post("/users/seed")
        assert response.status_code == status.HTTP_201_CREATED
        assert response.json() == {"message": "10 users seeded successfully"}
        
        # Verify users were created
        users_response = client.get("/users/")
        assert len(users_response.json()) == 10
    
    def test_seed_data_overwrites_existing(self, client, sample_users):
        """Test that seeding overwrites existing data."""
        # Verify initial users exist
        response = client.get("/users/")
        assert len(response.json()) == 3
        
        # Seed new data
        seed_response = client.post("/users/seed")
        assert seed_response.status_code == status.HTTP_201_CREATED
        
        # Verify old data was replaced
        users_response = client.get("/users/")
        assert len(users_response.json()) == 10