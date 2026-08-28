# TODO: Validate


from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse

from app.auth import service as auth_service
from app.auth.dependencies import SessionDep, get_current_active_superuser

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
    return auth_service.password_reset_email_response(session, email)
