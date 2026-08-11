# TODO: Validate
from sqlmodel import Field, SQLModel


# JSON payload containing access token
# TODO: Validate
class Token(SQLModel):
    access_token: str
    # S105 - This is not a hardcoded password.
    token_type: str = "bearer"  # noqa: S105


# Contents of JWT token
# TODO: Validate
class TokenPayload(SQLModel):
    sub: str | None = None


# TODO: Validate
class NewPassword(SQLModel):
    token: str
    new_password: str = Field(min_length=8, max_length=128)


# TODO: Validate
class UpdatePassword(SQLModel):
    current_password: str = Field(min_length=8, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)
