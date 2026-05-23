from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    portal: str = Field(pattern="^(citizen|admin)$")


class RegisterRequest(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    nik: str
    email: EmailStr
    password: str
    password_confirmation: str


class OtpVerifyRequest(BaseModel):
    email: EmailStr
    otp: str = Field(min_length=6, max_length=6)


class ResendOtpRequest(BaseModel):
    email: EmailStr


class EmailOtpVerifyRequest(BaseModel):
    otp: str = Field(min_length=6, max_length=6)
