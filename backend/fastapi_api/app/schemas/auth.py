from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=150)
    password: str | None = Field(default=None, min_length=1)
    pin: str | None = Field(default=None, min_length=4, max_length=6)
    device_code: str | None = Field(default=None, max_length=50)


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=10)


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    branch_id: int | None
    roles: list[str]
    permissions: list[str]

    @classmethod
    def from_domain(cls, user) -> "UserResponse":
        return cls(
            id=user.user_id,
            username=user.username,
            email=user.email,
            branch_id=user.branch_id,
            roles=list(user.roles),
            permissions=sorted(user.permissions),
        )


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class LoginResponse(TokenResponse):
    user: UserResponse
