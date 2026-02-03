"""
FastAPI main application for KulaPay USSD backend using SQLModel.
"""
from __future__ import annotations

from datetime import datetime, date, time
from random import choice, randint
from typing import Optional

from fastapi import Depends, FastAPI, Form, HTTPException
from fastapi.responses import PlainTextResponse
from sqlmodel import select

from database import get_session, init_db
from models import Transaction, Vendor

app = FastAPI(title="KulaPay API", version="2.0.0")


@app.on_event("startup")
async def on_startup() -> None:
    """Initialize database tables on application startup."""
    await init_db()


@app.get("/")
async def root():
    return {
        "message": "KulaPay API",
        "version": "2.0.0",
        "status": "running",
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


def home_menu(vendor: Vendor) -> str:
    """Main dashboard menu after successful PIN."""
    return (
        "CON Home\n"
        "1. Record New Sale\n"
        "2. View Today's Stats\n"
        "3. My Wallet\n"
        "0. Logout\n"
        "00. Home"
    )


@app.post("/debug/seed-today-transactions")
async def seed_today_transactions(
    phone_number: str,
    count: int = 5,
    session=Depends(get_session),
):
    """
    Create dummy Kenyan sales transactions for *today* for a given vendor.
    This is for local testing of the USSD "Today's Stats" screen.
    """
    # Find vendor
    result = await session.exec(
        select(Vendor).where(Vendor.phone_number == phone_number)
    )
    vendor = result.first()
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")

    # Kenyan-style random sale amounts (KES)
    possible_amounts = [50, 80, 100, 150, 200, 250, 300]

    # Create transactions timestamped for "now" (today)
    created = []
    for _ in range(max(1, count)):
        amount = float(choice(possible_amounts))
        tx = Transaction(
            vendor_id=vendor.id,
            amount=amount,
            transaction_type="SALE",
            created_at=datetime.utcnow(),
        )
        session.add(tx)
        created.append(amount)

    await session.commit()

    return {
        "message": "Dummy transactions created for today",
        "vendor_id": vendor.id,
        "phone_number": vendor.phone_number,
        "count": len(created),
        "amounts": created,
    }


@app.post("/ussd", response_class=PlainTextResponse)
async def ussd_endpoint(
    sessionId: str = Form(...),
    serviceCode: str = Form(...),
    phoneNumber: str = Form(...),
    text: Optional[str] = Form(""),
    session=Depends(get_session),
):
    """
    USSD endpoint to handle Africa's Talking callbacks.

    Parameters (form-encoded):
    - sessionId: Unique session identifier
    - serviceCode: USSD service code
    - phoneNumber: Vendor's phone number
    - text: User input (menu selections separated by '*')
    """
    # Normalize text
    text_value = text or ""
    parts = [p for p in text_value.split("*") if p] if text_value else []
    level = len(parts)

    # Look up vendor by phone number
    result = await session.exec(select(Vendor).where(Vendor.phone_number == phoneNumber))
    vendor = result.first()

    # Scenario A: User NOT in Vendor table (KYC Flow)
    if vendor is None:
        # Level 0: Welcome + ask full name
        if level == 0:
            return (
                "CON Welcome to KulaPay Vendor!\n"
                "To start selling, enter your Full Name:"
            )

        # Level 1: got full name, ask business name
        if level == 1:
            return (
                "CON Great. What is your Business Name?\n"
                "0. Back\n"
                "00. Home"
            )

        # Level 2: got business name, ask PIN
        if level == 2:
            return (
                "CON Set a 4-digit PIN to secure your wallet:\n"
                "0. Back\n"
                "00. Home"
            )

        # Level 3: got PIN, save Vendor to DB
        if level >= 3:
            full_name = parts[0].strip()
            business_name = parts[1].strip()
            pin = parts[2].strip()

            # Basic PIN validation (4 digits)
            if len(pin) != 4 or not pin.isdigit():
                return "END Invalid PIN. Please dial again and use a 4-digit PIN."

            new_vendor = Vendor(
                phone_number=phoneNumber,
                full_name=full_name,
                business_name=business_name,
                pin=pin,
            )
            session.add(new_vendor)
            await session.commit()

            return (
                f"END Account Created!\n"
                f"Biz: {business_name}\n"
                f"Dial again to login."
            )

        # Fallback
        return "END Invalid input. Please dial again."

    # Scenario B: User IS in Vendor table (Dashboard Flow)
    # Level 0: ask for PIN
    if level == 0:
        return f"CON Welcome back, {vendor.business_name}.\nEnter PIN:"

    # Level 1+: PIN entered
    entered_pin = parts[0].strip()
    if entered_pin != vendor.pin:
        return "END Wrong PIN."

    # Level 1 and PIN OK -> show menu
    if level == 1:
        return home_menu(vendor)

    # Level 2 or more: user has selected a menu option
    selection = parts[1].strip()

    # Handle navigation from sub-menus (Back/Home)
    # e.g. PIN*2*0 or PIN*3*00
    if level >= 3:
        nav = parts[2].strip()
        if nav == "0":
            # Back to main dashboard menu
            return home_menu(vendor)
        if nav == "00":
            # "Home" here means restart login (ask for PIN again)
            return f"CON Welcome back, {vendor.business_name}.\nEnter PIN:"

    # Option 1: Record New Sale
    if selection == "1":
        # Flow:
        # level 2: PIN*1              -> ask customer name
        # level 3: PIN*1*Name         -> ask customer phone
        # level 4: PIN*1*Name*Phone   -> ask amount
        # level 5: PIN*1*Name*Phone*Amount -> ask food ordered
        # level 6: PIN*1*Name*Phone*Amount*Food -> save + confirm

        # Step 1: ask for customer name
        if level == 2:
            return (
                "CON Enter Customer Name:\n"
                "0. Back\n"
                "00. Home"
            )

        # Extract fields that may be present
        customer_name = parts[2].strip() if level >= 3 else ""
        customer_phone = parts[3].strip() if level >= 4 else ""
        amount_str = parts[4].strip() if level >= 5 else ""
        food_ordered = parts[5].strip() if level >= 6 else ""

        # Step 2: got name, ask phone
        if level == 3:
            return (
                "CON Enter Customer Phone:\n"
                "0. Back\n"
                "00. Home"
            )

        # Step 3: got phone, ask amount
        if level == 4:
            return (
                "CON Enter Amount (KES):\n"
                "0. Back\n"
                "00. Home"
            )

        # Step 4: got amount, ask food ordered
        if level == 5:
            # Basic amount validation before proceeding
            try:
                float(amount_str)
            except ValueError:
                return (
                    "CON Invalid amount. Enter Amount (KES):\n"
                    "0. Back\n"
                    "00. Home"
                )

            return (
                "CON What food was ordered?:\n"
                "0. Back\n"
                "00. Home"
            )

        # Step 5: got all fields, save transaction
        if level >= 6:
            try:
                amount_val = float(amount_str)
            except ValueError:
                return "END Invalid amount. Please try again."

            # Persist a SALE transaction; for now we just store amount + vendor
            tx = Transaction(
                vendor_id=vendor.id,
                amount=amount_val,
                transaction_type="SALE",
                created_at=datetime.utcnow(),
            )
            session.add(tx)
            await session.commit()

            return (
                "CON Order successful.\n"
                "0. Back\n"
                "00. Home"
            )

        # Any other unexpected level in this branch
        return "END Invalid input. Please try again."

    # Option 2: Today's Stats
    if selection == "2":
        # Compute today's window in UTC
        today: date = datetime.utcnow().date()
        start_dt = datetime.combine(today, time.min)
        end_dt = datetime.combine(today, time.max)

        tx_result = await session.exec(
            select(Transaction)
            .where(Transaction.vendor_id == vendor.id)
            .where(Transaction.created_at >= start_dt)
            .where(Transaction.created_at <= end_dt)
        )
        tx_list = tx_result.all()

        total_sales = sum(t.amount for t in tx_list if t.transaction_type == "SALE")
        count = len([t for t in tx_list if t.transaction_type == "SALE"])

        return (
            "CON Today's Pulse\n"
            f"Sales: KES {total_sales:.2f}\n"
            f"Transactions: {count}\n\n"
            "0. Back\n"
            "00. Home"
        )

    # Option 3: My Wallet (simple wallet view)
    if selection == "3":
        return (
            "CON My Wallet\n"
            f"Balance: KES {vendor.wallet_balance:.2f}\n\n"
            "0. Back\n"
            "00. Home"
        )

    # Unknown option
    return "END Invalid option."


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)

