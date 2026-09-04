# TODO: Validate

from sqlmodel import Session, select

from app.files.models import File
from app.files.schemas import FileManifestEntry
from app.plugins.models import Plugin


# TODO: Validate
def _file_keys(session: Session) -> list[tuple[str, str]]:
    statement = select(Plugin.key, File.key).join(File, File.plugin_id == Plugin.id)  # type: ignore[arg-type]
    return list(session.exec(statement))


# TODO: Validate
def file_manifest(session: Session) -> list[FileManifestEntry]:
    return [
        FileManifestEntry(plugin_key=plugin_key, key=file_key)
        for plugin_key, file_key in _file_keys(session)
    ]
