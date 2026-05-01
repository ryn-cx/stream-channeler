"""Plugin dependencies."""

from typing import Annotated

from fastapi import Depends

from app.media.service import owned_record, readable_record
from app.plugins.models import Plugin

ReadablePlugin = Annotated[Plugin, Depends(readable_record(Plugin, "plugin_id"))]
OwnedPlugin = Annotated[Plugin, Depends(owned_record(Plugin, "plugin_id"))]
