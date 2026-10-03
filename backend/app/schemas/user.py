from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, EmailStr


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    tenant_id: str
    email: EmailStr
    full_name: Optional[str]
    role: str
    is_active: bool
    is_verified: bool
    created_at: datetime
