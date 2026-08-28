# TODO: Validate
from typing import Annotated

from fastapi import Depends

from app.comments.models import Comment
from app.media.service import editable_record, readable_record

EditableComment = Annotated[Comment, Depends(editable_record(Comment, "comment_id"))]
ReadableComment = Annotated[Comment, Depends(readable_record(Comment, "comment_id"))]
