from pydantic import BaseModel, EmailStr, Field


class CitizenCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    email: EmailStr
    nik: str
    password: str


class AdminCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    email: EmailStr
    password: str
    nik: str | None = None
    permissions: list[str] = []


class UserUpdateRequest(BaseModel):
    name: str | None = None
    email: EmailStr | None = None
    nik: str | None = None
    status: str | None = None


class ResetPasswordRequest(BaseModel):
    password: str
    force_reset: bool = True


class PermissionsUpdateRequest(BaseModel):
    permissions: list[str]
