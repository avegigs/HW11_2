# app/main.py
from fastapi import FastAPI, HTTPException, Query, Depends
from pydantic import BaseModel, validator
from database.models import Contact, Base
from typing import List, Optional
from sqlalchemy import or_, and_, extract
from database.database import get_db, SessionLocal
from sqlalchemy.orm import Session
from datetime import date, datetime

app = FastAPI()

class ContactBase(BaseModel):
    first_name: str
    last_name: str
    email: str
    phone_number: str
    birthdate: date
    additional_info: str = None

class ContactCreate(BaseModel):
    first_name: str
    last_name: str
    email: str
    phone_number: str
    birthdate: str  # Змінили тип на str для зручності вводу
    additional_info: str = None
    @validator('birthdate')
    def validate_birthdate_format(cls, value):
        try:
            # Парсимо дату зі строки в форматі "dd.mm.yyyy"
            parsed_date = datetime.strptime(value, '%d.%m.%Y').date()
            return parsed_date
        except ValueError:
            raise ValueError('Invalid date format. Please use "dd.mm.yyyy" format.')

class ContactResponse(BaseModel):
    first_name: str
    last_name: str
    email: str
    phone_number: str
    birthdate: date
    additional_info: Optional[str] 

class ContactUpdate(ContactBase):
    pass

@app.post("/contacts/", response_model=ContactResponse)
def create_contact(contact: ContactCreate, db: Session = Depends(get_db)):
    contact.birthdate = contact.birthdate.strftime('%Y-%m-%d')
    db_contact = Contact(**contact.dict())
    db.add(db_contact)
    db.commit()
    db.refresh(db_contact)
    db.close()
    return db_contact

@app.get("/contacts/", response_model=List[ContactResponse])
def read_contacts(skip: int = Query(0, description="Skip N contacts", ge=0), limit: int = Query(100, le=100), db: Session = Depends(get_db)):
    contacts = db.query(Contact).offset(skip).limit(limit).all()
    return contacts

@app.get("/contacts/{contact_id}", response_model=ContactResponse)
def read_contact(contact_id: int, db: Session = Depends(get_db)):
    contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if contact is None:
        raise HTTPException(status_code=404, detail="Contact not found")
    return contact

@app.put("/contacts/{contact_id}", response_model=ContactResponse)
def update_contact(contact_id: int, contact: ContactUpdate, db: Session = Depends(get_db)):
    db_contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if db_contact is None:
        raise HTTPException(status_code=404, detail="Contact not found")
    for key, value in contact.dict().items():
        setattr(db_contact, key, value)
    db.commit()
    db.refresh(db_contact)
    return db_contact

@app.delete("/contacts/{contact_id}", response_model=ContactResponse)
def delete_contact(contact_id: int, db: Session = Depends(get_db)):
    db_contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if db_contact is None:
        raise HTTPException(status_code=404, detail="Contact not found")
    db.delete(db_contact)
    db.commit()
    return db_contact

@app.get("/contacts/search/", response_model=List[ContactResponse])
def search_contacts(
    query: str = Query(..., description="Пошук контакту за іменем, прізвищем або email"),
    db: Session = Depends(get_db)
):
    contacts = db.query(Contact).filter(
        or_(
            Contact.first_name.ilike(f"%{query}%"),
            Contact.last_name.ilike(f"%{query}%"),
            Contact.email.ilike(f"%{query}%")
        )
    ).all()
    return contacts

from datetime import date, timedelta

@app.get("/contacts/birthday/", response_model=List[ContactResponse])
def upcoming_birthdays(db: Session = Depends(get_db)):
    current_date = datetime.now().date()
    seven_days_from_now = current_date + timedelta(days=7)
    contacts = db.query(Contact).filter(
        and_(
            extract('month', Contact.birthdate) == current_date.month,
            extract('day', Contact.birthdate) >= current_date.day,
            extract('day', Contact.birthdate) <= seven_days_from_now.day
        )
    ).all()

    return contacts