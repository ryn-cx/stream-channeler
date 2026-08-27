# TODO: Validate


from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import HTMLResponse

from app.auth import service as auth_service
from app.auth.dependencies import SessionDep, get_current_active_superuser
from app.users.service import get_user_by_email
from app.utils.service import generate_reset_password_email

router = APIRouter(
    tags=["login"],
    dependencies=[Depends(get_current_active_superuser)],
)


# TODO: Validate
@router.post(
    "/password-recovery-html-content/{email}",
    response_class=HTMLResponse,
)
def recover_password_html_content(email: str, session: SessionDep) -> HTMLResponse:
    """HTML Content for Password Recovery."""
    if not (user := get_user_by_email(session=session, email=email)):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="The user with this username does not exist in the system.",
        )
    password_reset_token = auth_service.generate_password_reset_token(email=email)
    email_data = generate_reset_password_email(
        email_to=user.email,
        email=email,
        token=password_reset_token,
    )

    return HTMLResponse(
        content=email_data.html_content,
        headers={"subject:": email_data.subject},
    )
