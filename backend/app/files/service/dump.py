# TODO: Validate
import json
import uuid
from collections import defaultdict

from fastapi import HTTPException, UploadFile
from sqlmodel import Session, col, select

from app.files.models import File
from app.files.schemas import FileExport, FileImportResult, FileManifestEntry
from app.files.service.manifest import _file_keys
from app.plugins.models import Plugin


# TODO: Validate
def _plugin_ids(session: Session) -> dict[str, uuid.UUID]:
    return {plugin.key: plugin.id for plugin in session.exec(select(Plugin)).all()}


# TODO: Validate
def _load_json(upload: UploadFile) -> list[dict[str, object]]:
    try:
        payload = json.load(upload.file)
    except json.JSONDecodeError as error:
        raise HTTPException(
            status_code=422,
            detail=f"Uploaded file is not valid JSON: {error}",
        ) from error

    if not isinstance(payload, list):
        raise HTTPException(
            status_code=422,
            detail="Uploaded file must contain a list of records",
        )

    return payload


# TODO: Validate
def missing_file_dump(session: Session, upload: UploadFile) -> list[FileExport]:
    known = {
        (entry.plugin_key, entry.key)
        for entry in (
            FileManifestEntry.model_validate(record) for record in _load_json(upload)
        )
    }

    missing: dict[str, list[str]] = defaultdict(list)
    for plugin_key, file_key in _file_keys(session):
        if (plugin_key, file_key) not in known:
            missing[plugin_key].append(file_key)

    plugin_ids = _plugin_ids(session)
    dump: list[FileExport] = []
    for plugin_key, file_keys in missing.items():
        plugin_id = plugin_ids[plugin_key]
        for start in range(0, len(file_keys), 500):
            statement = select(File).where(
                File.plugin_id == plugin_id,
                col(File.key).in_(file_keys[start : start + 500]),
            )
            dump.extend(
                FileExport(
                    plugin_key=plugin_key,
                    key=file.key,
                    data_timestamp=file.data_timestamp,
                    content=file.content,
                    update_at=file.update_at,
                    deleted_at=file.deleted_at,
                    status=file.status,
                    extra=file.extra,
                )
                for file in session.exec(statement).all()
            )
            session.expunge_all()

    return dump


# TODO: Validate
def import_file_dump(session: Session, upload: UploadFile) -> FileImportResult:
    entries = [FileExport.model_validate(record) for record in _load_json(upload)]

    plugin_ids = _plugin_ids(session)
    existing = set(_file_keys(session))

    imported = 0
    skipped = 0
    for entry in entries:
        plugin_id = plugin_ids.get(entry.plugin_key)
        if plugin_id is None:
            raise HTTPException(
                status_code=404,
                detail=f"Plugin with key {entry.plugin_key} does not exist",
            )

        if (entry.plugin_key, entry.key) in existing:
            skipped += 1
            continue

        session.add(
            File(
                plugin_id=plugin_id,
                key=entry.key,
                data_timestamp=entry.data_timestamp,
                content=entry.content,
                update_at=entry.update_at,
                deleted_at=entry.deleted_at,
                status=entry.status,
                extra=entry.extra or {},
            ),
        )
        existing.add((entry.plugin_key, entry.key))
        imported += 1

    session.commit()
    return FileImportResult(imported=imported, skipped=skipped)
