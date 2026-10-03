# TODO: Validate


from sqlmodel import Session

from app.schemas import DELETABLE_MODELS, Message


# TODO: Validate
def delete_record(
    session: Session,
    existing_record: DELETABLE_MODELS,
) -> Message:
    """Delete the record and return a success message."""
    session.delete(existing_record)
    session.commit()
    return Message(message=f"{type(existing_record).__name__} deleted successfully")
