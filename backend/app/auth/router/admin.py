# TODO: Validate


from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse

from app.auth.dependencies import SessionDep, get_current_active_superuser
from app.auth.service import password_reset

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
    return password_reset.password_reset_email_response(session, email)
