# TODO: Validate
from pydantic import BaseModel


# TODO: Validate
class PrivateUserCreate(BaseModel):
    email: str
    password: str
    username: str
    is_verified: bool = False
