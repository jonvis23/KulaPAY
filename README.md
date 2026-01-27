# KulaPay - USSD-based POS for Food Vendors

MVP backend for KulaPay, a USSD-based Point of Sale system for food vendors using Africa's Talking APIs.

## Tech Stack

- **Framework**: FastAPI
- **Database**: PostgreSQL (with SQLAlchemy ORM)
- **Communication**: Africa's Talking API (USSD & SMS)

## Project Structure

```
.
├── main.py              # FastAPI application and endpoints
├── models.py            # SQLAlchemy database models
├── database.py          # Database configuration and session management
├── ussd_logic.py        # USSD menu flow handling
├── whatsapp_logic.py     # WhatsApp conversational interface
├── messaging_service.py  # Unified messaging service (SMS/WhatsApp)
├── messaging_handler.py # Message processing and transaction handler
├── services.py           # Business logic (loyalty, credit eligibility)
├── at_utils.py          # Africa's Talking API utilities
├── requirements.txt     # Python dependencies
├── .env.example         # Environment variables template
└── README.md            # This file
```

## Setup Instructions

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Copy `.env.example` to `.env` and fill in your credentials:

```bash
cp .env.example .env
```

Edit `.env` with your:
- PostgreSQL database URL
- Africa's Talking username and API key

### 3. Set Up PostgreSQL Database

Create a PostgreSQL database:

```sql
CREATE DATABASE kulapay;
```

### 4. Run the Application

```bash
uvicorn main:app --reload
```

The API will be available at `http://localhost:8000`

## API Endpoints

### USSD Endpoint

**POST** `/ussd`

Handles Africa's Talking USSD callbacks. Receives:
- `sessionId`: Unique session identifier
- `serviceCode`: USSD service code
- `phoneNumber`: Vendor's phone number
- `text`: User input (menu selections separated by '*')

### Unified Messaging Callback Endpoint

**POST** `/messaging/callback`

Unified endpoint for SMS and WhatsApp messages. Automatically detects content type:
- **SMS**: `application/x-www-form-urlencoded` (Form Data)
- **WhatsApp**: `application/json` (JSON)

**Message Format:** `KULA [CustomerPhone] [Item] [Amount]`

**Example:** `KULA 0712345678 Chapati 50`

**Request Fields:**
- `from`: Sender phone number (vendor)
- `to`: Recipient (shortcode for SMS, WhatsApp number for WhatsApp)
- `text` or `message`: Message content

**Response:** Sends confirmation message via appropriate channel (SMS or WhatsApp)

### WhatsApp Endpoint

**POST** `/whatsapp`

Handles WhatsApp chat messages. Receives:
- `phoneNumber`: Vendor's phone number
- `message`: User's message text

### Other Endpoints

- **GET** `/` - Root endpoint
- **GET** `/health` - Health check
- **GET** `/transactions` - Get all transactions (for testing)
- **POST** `/vendors` - Create a new vendor (for testing)

## USSD Menu Flow

1. **Root Menu**: "Welcome to KulaPay. 1. New Sale 2. Check Points 3. Credit"
2. **New Sale Flow**:
   - Select 1 → Enter Customer Phone
   - Enter phone → Enter Amount
   - Enter amount → Select Payment (1. Cash 2. M-Pesa)
   - Select payment → Success message + SMS notification + Points awarded
3. **Check Points Flow**:
   - Select 2 → Enter Customer Phone
   - Shows points and Mandazi reward progress
4. **Credit Flow (ENPL)**:
   - Select 3 → Enter Customer Phone
   - If eligible: Shows credit limit and options (1. Accept Loan 2. Back)
   - If not eligible: Shows progress message
   - Accept loan → Creates credit transaction + initiates repayment

## WhatsApp Interface

**POST** `/whatsapp`

Conversational chat interface (no numbering). Commands:
- `hi` / `hello` / `help` - Show menu
- `sale <phone> <amount> <cash|mpesa>` - Process sale
- `points <phone>` - Check customer points
- `credit <phone>` - Check credit eligibility
- `credit <phone> accept` - Accept loan

## Database Models

### Vendor
- `id`: Primary key
- `phone_number`: Unique vendor phone number
- `business_name`: Vendor business name
- `created_at`: Timestamp

### Customer
- `id`: Primary key
- `phone_number`: Unique customer phone number
- `kula_points`: Customer loyalty points (1 point per 10 KES)
- `credit_limit`: Credit limit (auto-calculated based on eligibility)

### Transaction
- `id`: Primary key
- `vendor_id`: Foreign key to Vendor
- `customer_phone`: Foreign key to Customer
- `amount`: Transaction amount
- `payment_type`: Cash, M-Pesa, or Credit
- `timestamp`: Transaction timestamp

## Business Logic (services.py)

### Loyalty Points
- **Rule**: 1 point per 10 KES spent
- **Reward**: 50 points = Free Mandazi
- Points are automatically awarded on each transaction

### Credit Eligibility
- **Requirements**:
  - Minimum 5 transactions
  - Minimum 500 KES total spend
- **Credit Limit**: 20% of total historical spend, capped at 300 KES
- Credit limit is automatically calculated and updated when eligibility is checked

## Features

### Day 1 (Basic USSD & DB)
- ✅ USSD menu navigation with nested levels
- ✅ Transaction processing with Cash/M-Pesa support
- ✅ Customer points system (auto-created on first transaction)
- ✅ SMS notifications via Africa's Talking
- ✅ Modular code structure
- ✅ Environment-based configuration

### Day 2 (Intelligence Layer)
- ✅ **Loyalty Points System**: 1 point per 10 KES spent
- ✅ **Micro-Credit Eligibility Engine**: 
  - Eligibility: 5+ transactions AND 500+ KES total spend
  - Credit limit: 20% of total spend (capped at 300 KES)
- ✅ **Enhanced USSD Menu**:
  - Check Points: Shows points and Mandazi reward progress
  - Credit: Full ENPL (Eat Now, Pay Later) flow
- ✅ **Africa's Talking Payments Integration**: Mock loan repayment function
- ✅ **WhatsApp Integration**: Conversational chat interface

### Day 3 (Unified Chat POS)
- ✅ **Unified Messaging Callback**: Single endpoint for SMS and WhatsApp
- ✅ **KULA Command Parser**: Parses "KULA [Phone] [Item] [Amount]" format
- ✅ **Dynamic Content-Type Detection**: Handles both form data and JSON
- ✅ **Smart Response Routing**: Sends replies via appropriate channel
- ✅ **MessagingService Class**: Centralized SMS/WhatsApp API handling
- ✅ **Automatic Transaction Processing**: Records sales, awards points, checks credit

## Notes

- Vendors must be registered before processing transactions
- Customers are auto-created on first transaction
- SMS notifications are sent after successful sales
- Points are calculated as 1 point per 10 KES (updated from Day 1)
- Credit eligibility is checked automatically after transactions
- Loan repayment uses mock function (integrate AT Payments API in production)
- In production, use a task queue (like Celery) for SMS sending and async operations

## Testing

1. Create a vendor first:
```bash
curl -X POST "http://localhost:8000/vendors?phone_number=+254712345678&business_name=Test%20Vendor"
```

2. Test USSD flow using Africa's Talking simulator or actual USSD service

