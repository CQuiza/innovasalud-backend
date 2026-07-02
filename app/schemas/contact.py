from pydantic import BaseModel, EmailStr


class ContactForm(BaseModel):
    name: str
    email: EmailStr
    program: str
    message: str
