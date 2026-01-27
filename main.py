"""
FastAPI main application for KulaPay
"""
from fastapi import FastAPI, Request, Depends, HTTPException, Form
from fastapi.responses import PlainTextResponse, JSONResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
import os
import json
from dotenv import load_dotenv

from database import get_db, init_db
from ussd_logic import handle_ussd_request
from whatsapp_logic import handle_whatsapp_message
from at_utils import send_sale_notification
from models import Transaction, PaymentType
from messaging_service import messaging_service
from messaging_handler import process_kula_sale

load_dotenv()

app = FastAPI(title="KulaPay API", version="1.0.0")


# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    """Initialize database tables on application startup"""
    init_db()


# Pydantic models for request validation
class WhatsAppRequest(BaseModel):
    """WhatsApp webhook request model"""
    phoneNumber: str
    message: str


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "KulaPay API",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


@app.post("/ussd", response_class=PlainTextResponse)
async def ussd_endpoint(
    sessionId: str = Form(...),
    serviceCode: str = Form(...),
    phoneNumber: str = Form(...),
    text: Optional[str] = Form(""),
    db: Session = Depends(get_db)
):
    """
    USSD endpoint to handle Africa's Talking callbacks
    
    This endpoint receives form-encoded data:
    - sessionId: Unique session identifier
    - serviceCode: USSD service code
    - phoneNumber: Vendor's phone number
    - text: User input (menu selections separated by '*')
    """
    try:
        # Fast path for root menu - no database needed
        text_value = text or ""
        if not text_value or text_value == "":
            return "END Welcome to KulaPay!"
        
        # Handle USSD request for non-root menus
        response = handle_ussd_request(
            text=text_value,
            phone_number=phoneNumber,
            session_id=sessionId,
            db=db
        )

        # If transaction was successful, send SMS notification
        # Check if response indicates success
        if "Sale successful" in response and text_value:
            menu_selections = text_value.split("*")
            if len(menu_selections) >= 4:
                try:
                    customer_phone = menu_selections[1]
                    amount = float(menu_selections[2])
                    # Calculate points (1 point per 10 KES) - points already awarded in ussd_logic
                    points_earned = amount * 0.1  # 1 point per 10 KES
                    
                    # Send SMS notification (async in background)
                    # In production, use a task queue like Celery
                    send_sale_notification(customer_phone, amount, points_earned)
                except (ValueError, IndexError):
                    pass  # Silently fail SMS if there's an error

        return response

    except Exception as e:
        return f"END An error occurred. Please try again later. Error: {str(e)}"


@app.get("/transactions")
async def get_transactions(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Get all transactions (for testing/debugging)"""
    transactions = db.query(Transaction).offset(skip).limit(limit).all()
    return {
        "transactions": [
            {
                "id": t.id,
                "vendor_id": t.vendor_id,
                "customer_phone": t.customer_phone,
                "amount": t.amount,
                "payment_type": t.payment_type.value,
                "timestamp": t.timestamp.isoformat()
            }
            for t in transactions
        ]
    }


@app.post("/whatsapp", response_class=PlainTextResponse)
async def whatsapp_endpoint(request: WhatsAppRequest, db: Session = Depends(get_db)):
    """
    WhatsApp endpoint to handle chat messages
    
    This endpoint receives:
    - phoneNumber: Vendor's phone number
    - message: User's message text
    """
    try:
        response = handle_whatsapp_message(
            message=request.message,
            phone_number=request.phoneNumber,
            db=db
        )
        return response
    except Exception as e:
        return f"❌ An error occurred. Please try again later. Error: {str(e)}"


@app.post("/messaging/callback")
async def messaging_callback(request: Request, db: Session = Depends(get_db)):
    """
    Unified callback endpoint for SMS and WhatsApp messages
    
    Handles both:
    - SMS: application/x-www-form-urlencoded (Form Data)
    - WhatsApp: application/json (JSON)
    
    Expected message format: "KULA [CustomerPhone] [Item] [Amount]"
    Example: "KULA 0712345678 Chapati 50"
    """
    try:
        # Detect content type
        content_type = request.headers.get("content-type", "").lower()
        
        # Extract message data based on content type
        if "application/json" in content_type:
            # WhatsApp - JSON format
            data = await request.json()
            sender = data.get("from", "")
            recipient = data.get("to", "")
            text = data.get("text", "") or data.get("message", "")
            channel = "whatsapp"
        elif "application/x-www-form-urlencoded" in content_type or "form-data" in content_type:
            # SMS - Form data format
            form_data = await request.form()
            sender = form_data.get("from", "")
            recipient = form_data.get("to", "")
            text = form_data.get("text", "") or form_data.get("message", "")
            channel = "sms"
        else:
            # Try to parse as form data (default for SMS)
            try:
                form_data = await request.form()
                sender = form_data.get("from", "")
                recipient = form_data.get("to", "")
                text = form_data.get("text", "") or form_data.get("message", "")
                channel = "sms"
            except:
                # Fallback to JSON
                try:
                    data = await request.json()
                    sender = data.get("from", "")
                    recipient = data.get("to", "")
                    text = data.get("text", "") or data.get("message", "")
                    channel = "whatsapp"
                except:
                    return JSONResponse(
                        status_code=400,
                        content={"error": "Invalid request format"}
                    )
        
        # Validate required fields
        if not sender or not text:
            error_msg = "Invalid Format: Missing 'from' or 'text' field"
            if sender:
                if channel == "sms":
                    messaging_service.send_sms(sender, error_msg)
                else:
                    messaging_service.send_whatsapp(sender, error_msg)
            return JSONResponse(
                status_code=400,
                content={"error": error_msg}
            )
        
        # Parse KULA command
        action, customer_phone, item, amount = messaging_service.parse_kula_command(text)
        
        if not action or not customer_phone or not amount:
            error_msg = "Invalid Format: Use 'KULA [CustomerPhone] [Item] [Amount]'"
            if sender:
                if channel == "sms":
                    messaging_service.send_sms(sender, error_msg)
                else:
                    messaging_service.send_whatsapp(sender, error_msg)
            return JSONResponse(
                status_code=400,
                content={"error": error_msg}
            )
        
        # Process the sale
        result = process_kula_sale(
            vendor_phone=sender,
            customer_phone=customer_phone,
            item=item,
            amount=amount,
            db=db
        )
        
        # Send response via appropriate channel
        if result['success']:
            if channel == "sms":
                messaging_service.send_sms(sender, result['message'])
            else:
                messaging_service.send_whatsapp(sender, result['message'])
        else:
            # Send error message
            if channel == "sms":
                messaging_service.send_sms(sender, result['message'])
            else:
                messaging_service.send_whatsapp(sender, result['message'])
        
        return JSONResponse(
            status_code=200,
            content={
                "status": "processed",
                "success": result['success'],
                "message": result['message'],
                "channel": channel
            }
        )
    
    except Exception as e:
        error_msg = f"Error processing message: {str(e)}"
        try:
            # Try to send error message if we have sender info
            if 'sender' in locals():
                if channel == "sms":
                    messaging_service.send_sms(sender, error_msg)
                else:
                    messaging_service.send_whatsapp(sender, error_msg)
        except:
            pass
        
        return JSONResponse(
            status_code=500,
            content={"error": error_msg}
        )


@app.post("/vendors")
async def create_vendor(phone_number: str, business_name: str, db: Session = Depends(get_db)):
    """Create a new vendor (for testing/setup)"""
    from models import Vendor
    
    # Check if vendor exists
    existing = db.query(Vendor).filter(Vendor.phone_number == phone_number).first()
    if existing:
        raise HTTPException(status_code=400, detail="Vendor already exists")
    
    vendor = Vendor(phone_number=phone_number, business_name=business_name)
    db.add(vendor)
    db.commit()
    db.refresh(vendor)
    
    return {
        "id": vendor.id,
        "phone_number": vendor.phone_number,
        "business_name": vendor.business_name,
        "created_at": vendor.created_at.isoformat()
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

