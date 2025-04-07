from pydantic import BaseModel, EmailStr
from typing import Optional

class User(BaseModel):
    username: str
    email: EmailStr

class UpdateUser(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None

class UserOut(BaseModel):
    id: str
    username: str
    email: EmailStr
