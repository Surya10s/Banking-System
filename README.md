# 💰 Money Transfer API

A robust FastAPI-based money transfer system with support for immediate and scheduled transfers, daily transaction limits, and comprehensive transaction tracking.

## 🚀 Features

- **User Management**: Create and manage user accounts with balance tracking
- **Immediate Transfers**: Real-time money transfers between accounts
- **Scheduled Transfers**: Schedule transfers for future dates using Celery
- **Daily Limits**: Configurable daily transaction limits (default: 2000)
- **Transaction History**: Complete audit trail of all transactions
- **Task Tracking**: Monitor the status of scheduled transfers
- **Data Seeding**: Quick database seeding for testing purposes

## 📋 Table of Contents

- [Installation](#installation)
- [Project Structure](#project-structure)
- [Configuration](#configuration)
- [API Endpoints](#api-endpoints)
- [Usage Examples](#usage-examples)
- [Business Rules](#business-rules)
- [Error Handling](#error-handling)
- [Running the Application](#running-the-application)

## 🛠️ Installation

### Prerequisites

- Python 3.8+
- PostgreSQL/MySQL (or any SQLAlchemy-supported database)
- Redis (for Celery task queue)

### Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd money-transfer-api
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install fastapi uvicorn sqlalchemy celery redis pydantic
```

4. Set up environment variables (create `.env` file):
```env
DATABASE_URL=postgresql://user:password@localhost/money_transfer_db
REDIS_URL=redis://localhost:6379/0
```

5. Initialize the database:
```bash
# Database tables will be created automatically on first run
```

## 📁 Project Structure

```
project/
├── main.py                          # Application entry point
├── db.py                            # Database configuration
├── schemas.py                       # SQLAlchemy models & Pydantic schemas
├── celery_worker.py                 # Celery tasks configuration
├── api/
│   ├── __init__.py
│   ├── dependencies.py              # Shared dependencies
│   └── routes/
│       ├── __init__.py
│       ├── users.py                 # User management endpoints
│       ├── transfers.py             # Transfer endpoints
│       └── tasks.py                 # Task status endpoints
|___test                              # testcase file for all senerio
└── services/
    ├── __init__.py
    └── transfer_service.py          # Transfer business logic
```

## ⚙️ Configuration

### Database Models

**User Model:**
- `id`: Primary key
- `username`: User's username
- `AccountNo`: Unique account number
- `Amount`: Current balance
- `daily_used`: Remaining daily transfer limit
- `last_reset`: Last daily limit reset date

**Transaction Model:**
- `id`: Primary key
- `user_id`: Foreign key to User
- `account_no`: Account number
- `amount`: Transaction amount (negative for debit, positive for credit)
- `transaction_type`: "debit" or "credit"
- `timestamp`: Transaction timestamp

## 🔌 API Endpoints

### Health Check

#### `GET /`
Check if the server is running.

**Response:**
```json
{
  "message": "Server is running successfully"
}
```

---

### User Management

#### `GET /users/`
Fetch all users with their balances.

**Response:**
```json
[
  {
    "id": 1,
    "username": "user1",
    "AccountNo": 1000000001,
    "Amount": 5000,
    "daily_used": 2000
  }
]
```

#### `POST /users/seed`
Seed the database with 10 test users (initial balance: 5000).

**Response:**
```json
{
  "message": "10 users seeded successfully"
}
```

#### `GET /users/{user_id}/transactions`
Get all transactions for a specific user.

**Parameters:**
- `user_id` (path): User ID

**Response:**
```json
[
  {
    "id": 1,
    "user_id": 1,
    "account_no": 1000000001,
    "amount": -500,
    "transaction_type": "debit",
    "timestamp": "2025-10-26T10:30:00"
  }
]
```

---

### Money Transfers

#### `POST /transfers/immediate`
Execute an immediate money transfer.

**Request Body:**
```json
{
  "sender_id": 1,
  "receiver_account": 1000000002,
  "amount": 500
}
```

**Response:**
```json
{
  "message": "Transfer successful",
  "sender": {
    "username": "user1",
    "balance": 4500,
    "daily_limit_remaining": 1500
  },
  "receiver": {
    "username": "user2",
    "balance": 5500
  }
}
```

#### `POST /transfers/scheduled`
Schedule a money transfer for a future date.

**Request Body:**
```json
{
  "sender_id": 1,
  "receiver_account": 1000000002,
  "amount": 500,
  "scheduled_date": "2025-10-30"
}
```

**Response:**
```json
{
  "message": "Transfer scheduled successfully",
  "task_id": "abc123-def456-ghi789",
  "scheduled_date": "2025-10-30",
  "sender_username": "user1",
  "receiver_username": "user2",
  "amount": 500
}
```

---

### Task Management

#### `GET /tasks/status/{task_id}`
Check the status of a scheduled transfer.

**Parameters:**
- `task_id` (path): Celery task ID

**Response:**
```json
{
  "task_id": "abc123-def456-ghi789",
  "status": "pending",
  "message": "Transfer is scheduled and waiting to be executed"
}
```

**Possible Status Values:**
- `pending`: Task is scheduled
- `success`: Task completed successfully
- `failed`: Task failed with error
- `processing`: Task is currently being processed

## 💡 Usage Examples

### Example 1: Setting Up Test Data

```bash
# Seed the database with test users
curl -X POST http://localhost:8000/users/seed
```

### Example 2: Immediate Transfer

```bash
# Transfer 500 from user 1 to user 2
curl -X POST http://localhost:8000/transfers/immediate \
  -H "Content-Type: application/json" \
  -d '{
    "sender_id": 1,
    "receiver_account": 1000000002,
    "amount": 500
  }'
```

### Example 3: Scheduled Transfer

```bash
# Schedule a transfer for tomorrow
curl -X POST http://localhost:8000/transfers/scheduled \
  -H "Content-Type: application/json" \
  -d '{
    "sender_id": 1,
    "receiver_account": 1000000002,
    "amount": 500,
    "scheduled_date": "2025-10-27"
  }'
```

### Example 4: Check Transaction History

```bash
# Get all transactions for user 1
curl http://localhost:8000/users/1/transactions
```

## 📜 Business Rules

### Transfer Validations

1. **Amount Validation**: Amount must be greater than 0
2. **Account Validation**: Cannot transfer to the same account
3. **Balance Check**: Sender must have sufficient funds
4. **Daily Limit**: Transfers cannot exceed daily limit (2000 per day)
5. **Daily Reset**: Daily limit resets automatically at midnight
6. **Scheduled Date**: Scheduled transfers must be for future dates

### Transaction Recording

- Every transfer creates two transaction records:
  - **Debit**: Negative amount for sender
  - **Credit**: Positive amount for receiver
- Transactions include timestamp for audit trail
- All transactions are atomic (all-or-nothing)

### Daily Limits

- Default daily limit: 2000
- Limit automatically resets at midnight
- Remaining limit tracked per user
- Transfers that exceed limit are rejected

## ⚠️ Error Handling

The API returns appropriate HTTP status codes and error messages:

### Common Error Responses

**404 Not Found:**
```json
{
  "detail": "Sender not found"
}
```

**400 Bad Request:**
```json
{
  "detail": "Insufficient funds"
}
```

**500 Internal Server Error:**
```json
{
  "detail": "Transaction failed: <error details>"
}
```

### Error Scenarios

- **User Not Found**: Sender or receiver doesn't exist
- **Insufficient Funds**: Sender doesn't have enough balance
- **Daily Limit Exceeded**: Transfer exceeds remaining daily limit
- **Invalid Amount**: Amount is zero or negative
- **Same Account Transfer**: Attempting to transfer to same account
- **Invalid Date**: Scheduled date is in the past or invalid format
- **Database Error**: Connection or constraint violations

## 🚀 Running the Application

### Start the FastAPI Server

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Start Celery Worker (for scheduled transfers)

```bash
celery -A celery_worker worker --loglevel=info
```

### Start Celery Beat (for scheduled task execution)

```bash
celery -A celery_worker beat --loglevel=info
```

### Access API Documentation

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 🧪 Testing

### Manual Testing with Swagger UI

1. Navigate to http://localhost:8000/docs
2. Use the "Try it out" feature for each endpoint
3. View real-time responses and status codes

### Testing Workflow

1. **Seed data**: POST `/users/seed`
2. **Check users**: GET `/users/`
3. **Transfer money**: POST `/transfers/immediate`
4. **View transactions**: GET `/users/{user_id}/transactions`
5. **Schedule transfer**: POST `/transfers/scheduled`
6. **Check task status**: GET `/tasks/status/{task_id}`

## 🔒 Security Considerations

- Add authentication/authorization middleware
- Implement rate limiting for API endpoints
- Use HTTPS in production
- Validate and sanitize all inputs
- Implement request/response logging
- Add database connection pooling
- Use environment variables for sensitive data

## 🚀 Deployment

### Production Checklist

- [ ] Set up proper database (PostgreSQL recommended)
- [ ] Configure Redis for Celery
- [ ] Set up environment variables
- [ ] Enable CORS if needed
- [ ] Add authentication layer
- [ ] Set up monitoring and logging
- [ ] Configure backup strategy



**Built with ❤️ using FastAPI postgresql python**
