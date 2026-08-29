# TODO: Validate
"""The store every file a test reads is kept in, and how a test reads it."""

from collections.abc import Callable, Generator, Sequence
from contextlib import ExitStack, contextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from unittest.mock import patch
from uuid import UUID

from loguru import logger
from pydantic import BaseModel

from app.constants import ALL_TEST_FILES_FOLDER, ALL_TEST_FILES_METADATA_FOLDER
from app.files.models import File
from app.seasons.models import Season
from app.shows.models import Show
from app.utils import tz_datetime
from plugins.utils.base_plugin import BaseFile, BasePlugin
from plugins.utils.manage_plugins import import_plugins

IMPORT_TIME = datetime(2026, 1, 1, tzinfo=UTC)
"""When every import is taken to have happened, and every file arrived."""

UPDATE_TIME = datetime(2026, 1, 2, tzinfo=UTC)
"""When every update is taken to have happened, the day after the import."""

ESCAPE_PREFIX = "%"
"""What marks a character that a file name cannot hold as it is."""

# The characters Windows will not put in a file name, along with the prefix
# itself so that escaping can be undone, and the control characters no file
# system takes. `/` is left out because it separates a key into folders.
_ESCAPED_CHARACTERS = frozenset('<>:"\\|?*' + ESCAPE_PREFIX) | {
    chr(code) for code in range(32)
}
# Windows drops a trailing dot or space from a name without saying so, which
# would leave a name that no longer reads back as the key it was built from.
_ESCAPED_ENDINGS = (".", " ")


# TODO: Validate
def _owner_key(file: BaseFile[Any]) -> str:
    """Return the plugin a file class belongs to.

    Read off where the class is declared rather than off the plugin the file is
    being downloaded for, because a plugin downloads files belonging to another
    one (TMDB's, to fill in what its own website leaves out) and both have to
    reach the same stored copy.
    """
    return type(file).__module__.split(".")[1]


# TODO: Validate
def _escape(character: str) -> str:
    return f"{ESCAPE_PREFIX}{ord(character):02X}"


# TODO: Validate
def encode_name(segment: str) -> str:
    """Return one part of a key as a name the file system will take."""
    encoded = "".join(
        _escape(character) if character in _ESCAPED_CHARACTERS else character
        for character in segment
    )
    if encoded.endswith(_ESCAPED_ENDINGS):
        encoded = encoded[:-1] + _escape(encoded[-1])
    return encoded


# TODO: Validate
def _encoded_path(owner_key: str, file_key: str) -> Path:
    """Return where the file `file_key` names sits under a store's folder."""
    encoded = "/".join(encode_name(part) for part in file_key.split("/"))
    return Path(encode_name(owner_key)) / encoded


# TODO: Validate
def stored_path(owner_key: str, file_key: str) -> Path:
    """Return where the content of the file `file_key` names is kept."""
    return ALL_TEST_FILES_FOLDER / _encoded_path(owner_key, file_key)


# TODO: Validate
def stored_metadata_path(owner_key: str, file_key: str) -> Path:
    """Return where what the file `file_key` names was in the table is kept."""
    return ALL_TEST_FILES_METADATA_FOLDER / _encoded_path(owner_key, file_key)


# TODO: Validate
def decode_name(segment: str) -> str:
    """Return the part of a key that `encode_name` built `segment` from."""
    characters: list[str] = []
    index = 0
    while index < len(segment):
        if segment[index] != ESCAPE_PREFIX:
            characters.append(segment[index])
            index += 1
            continue
        characters.append(chr(int(segment[index + 1 : index + 3], 16)))
        index += 3
    return "".join(characters)


# TODO: Validate
def stored_key(path: Path) -> tuple[str, str]:
    """Return the owning plugin and file key that `path` was stored for."""
    owner, *rest = path.relative_to(ALL_TEST_FILES_FOLDER).parts
    return decode_name(owner), "/".join(decode_name(part) for part in rest)


# TODO: Validate
def stored_file_path(file: BaseFile[Any]) -> Path:
    """Return where `file` is kept among the stored test files."""
    return stored_path(_owner_key(file), file.file_key())


# TODO: Validate
def _exists(path: Path) -> bool:
    """Report whether `path` is stored, counting one it could not be as not stored.

    A key the file system will not take was never stored under it, and asking
    about such a path raises rather than answering on some systems, so the
    question is answered here instead of at the call.
    """
    try:
        return path.exists()
    except OSError:
        return False


# TODO: Validate
class StoredFileMetadata(BaseModel):
    """What a stored file was in the `File` table when it was downloaded."""

    id: UUID
    key: str
    created_at: datetime
    modified_at: datetime
    data_timestamp: datetime
    update_at: datetime | None = None
    deleted_at: datetime | None = None
    extra: str | None = None


# TODO: Validate
def read_stored_metadata(owner_key: str, file_key: str) -> StoredFileMetadata | None:
    """Return what `file_key` was in the table, or None when it was not stored."""
    path = stored_metadata_path(owner_key, file_key)
    if not _exists(path):
        return None
    return StoredFileMetadata.model_validate_json(path.read_text(encoding="utf-8"))


# TODO: Validate
def write_stored_metadata(owner_key: str, file_key: str, record: File) -> None:
    """Store what `record` is in the table beside the content it was stored for."""
    path = stored_metadata_path(owner_key, file_key)
    path.parent.mkdir(parents=True, exist_ok=True)
    metadata = StoredFileMetadata.model_validate(record, from_attributes=True)
    path.write_text(metadata.model_dump_json(indent=2), encoding="utf-8")


# TODO: Validate
def date_at_import_time(record: File, import_time: datetime = IMPORT_TIME) -> None:
    """Date `record` as though it had been downloaded at `IMPORT_TIME`.

    A stored file is dated by when it was really downloaded, which is whenever
    the store was last topped up and never the same twice, and everything a
    plugin works out from a file is dated from the file. Reading every file as
    though it arrived at the moment the test is frozen to is what leaves the
    records built from it the same on every run.

    It is also what keeps a plugin doing what it does in production. A file left
    at the day it was really downloaded is a file the frozen clock is years past,
    so every record read out of it is due a refresh the moment it is written, and
    an import ends up walking the paths that only a stale record reaches.

    How long the file was good for is carried over as the gap it was stored with,
    so a file is still refreshed when the plugin says it should be rather than
    being made to look fresh forever. The gap survives the shift, which leaves
    dating a record that has already been dated a no-op.
    """
    refresh_gap = record.update_at - record.data_timestamp if record.update_at else None
    record.created_at = import_time
    record.modified_at = import_time
    record.data_timestamp = import_time
    record.update_at = import_time + refresh_gap if refresh_gap else None


# TODO: Validate
def _stored_data_timestamp(path: Path) -> datetime:
    """Date a file stored before its metadata was kept by the stored file itself.

    The stored file moves only when it is refreshed, so its own date says the
    same thing a timestamp read off the data would have.
    """
    return tz_datetime.fromtimestamp(path.stat().st_mtime)


# TODO: Validate
def stored_file_record(owner_key: str, file_key: str, path: Path) -> File:
    """Return the `File` the stored copy of `file_key` describes, dated at the import."""
    content = path.read_text(encoding="utf-8") or None
    metadata = read_stored_metadata(owner_key, file_key)
    if metadata is None:
        record = File(
            key=file_key,
            content=content,
            data_timestamp=_stored_data_timestamp(path),
        )
        date_at_import_time(record)
        return record

    stored = metadata.model_dump()
    record = File(**stored, content=content)
    date_at_import_time(record)
    return record


# TODO: Validate
def restore_stored_metadata(record: File, owner_key: str, path: Path) -> None:
    """Put back what `record` was when it was stored, dated at the import.

    A file stored before its metadata was kept has one written for it out of the
    stored file, so the store fills itself in as it is read rather than having
    to be recorded from nothing again.
    """
    metadata = read_stored_metadata(owner_key, record.key)
    if metadata is None:
        record.data_timestamp = _stored_data_timestamp(path)
        write_stored_metadata(owner_key, record.key, record)
        date_at_import_time(record)
        return
    stored = metadata.model_dump()
    for field, value in stored.items():
        setattr(record, field, value)
    date_at_import_time(record)


# TODO: Validate
@contextmanager
def serve_downloads_from_disk() -> Generator[list[str]]:
    """Serve every download from the stored test files, downloading what is missing.

    A file that has been stored is written straight from disk, so a test runs
    without reaching the network. A file that has not been stored yet is
    downloaded for real and then stored, which is how a test records what it
    needs the first time it is run.

    Yields the keys of the files that had to be downloaded, which is empty on
    every run after the first.

    Raises:
        OSError: at the end of the run, naming every file whose key the file
            system would not take. It is raised once everything is done so that
            one unstorable file does not keep the rest from being stored.

    """
    downloaded: list[str] = []
    unstorable: list[str] = []
    original_download_if_outdated = BaseFile[Any].download_if_outdated

    # Patched on `download_if_outdated` rather than on `_download`, because a
    # file class is free to download however it likes and most of them override
    # `_download` to do it. Only `download_if_outdated` is every file's way in.
    # TODO: Validate
    def _download_if_outdated(
        self: BaseFile[Any],
        update_at: datetime | None = None,
    ) -> None:
        if not self.is_outdated(update_at):
            return

        owner_key = _owner_key(self)
        path = stored_file_path(self)
        if _exists(path):
            logger.debug(f"Serving {self.file_key()} from {path}")
            self.write(path.read_text(encoding="utf-8") or None)
            # `write` stamps the record with the current time, so what the file
            # was in the table when it was stored is put back over it. Without
            # that a recording run records the time it ran while every run after
            # it reads the stored value, which is a mismatch in every test.
            restore_stored_metadata(self.database_record, owner_key, path)
            return

        original_download_if_outdated(self, update_at)
        downloaded.append(self.file_key())
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(self.database_record.content or "", encoding="utf-8")
            write_stored_metadata(owner_key, self.file_key(), self.database_record)
        except OSError as error:
            # Held until the run is over so the rest of the files are still
            # stored, and the report names every key at fault rather than only
            # the first one reached.
            unstorable.append(f"{self.file_key()} ({error})")
            return
        # Logged as it is stored rather than counted up once the test is over,
        # so a run that fails part way through still says what it downloaded.
        logger.info(f"Stored {self.file_key()}")

    with patch.object(BaseFile, "download_if_outdated", _download_if_outdated):
        yield downloaded

    if unstorable:
        keys = "\n".join(unstorable)
        msg = f"The file system would not store these file keys:\n{keys}"
        raise OSError(msg)


_GROUPED_DOWNLOAD = "_download_all_episode_files"


# TODO: Validate
def _grouped_download_overrides() -> list[type[BasePlugin]]:
    """Return every plugin that downloads a season's episodes as a group.

    A plugin that keeps the one-file-at-a-time download it inherits is left out,
    since it already reaches for each episode on its own.
    """
    import_plugins()
    remaining: list[type[BasePlugin]] = [BasePlugin]
    overrides: list[type[BasePlugin]] = []
    while remaining:
        plugin_class = remaining.pop()
        remaining.extend(plugin_class.__subclasses__())
        if _GROUPED_DOWNLOAD in plugin_class.__dict__:
            overrides.append(plugin_class)
    return overrides


# TODO: Validate
def _serve_before_grouping(
    grouped_download: Callable[..., list[File]],
) -> Callable[..., list[File]]:
    """Wrap a grouped download so each episode is served on its own first."""

    # TODO: Validate
    def _download_all_episode_files(
        self: BasePlugin,
        season: str | Season,
        show: str | Show | None = None,
        preloaded_files: Sequence[File] | None = None,
    ) -> list[File]:
        season_key = self._get_key(season)
        show_key = self._get_show_key(season, show)
        episode_keys = self._episode_keys_from_file(season_key, show_key)
        # Held for as long as the files are being reached for, because a preload
        # only warms the session and what it warmed is dropped once it is let go.
        _cache = self._preload_episode_files(
            episode_keys,
            season_key,
            show_key,
            preloaded_files,
        )
        for episode_key in episode_keys:
            self._download_outdated_files(
                self._episode_files(episode_key, season_key, show_key),
            )
        return grouped_download(self, season, show, preloaded_files)

    return _download_all_episode_files


# TODO: Validate
@contextmanager
def check_episodes_before_grouped_download() -> Generator[None]:
    """Reach for each episode on its own before a plugin downloads them as a group.

    A plugin that fetches a season's episodes in one request goes around
    `download_if_outdated`, which is what serves a file out of the store, so a
    whole group is downloaded again when a single episode of it is missing.
    Asking for each episode first leaves the group download only the episodes
    that really are missing, and the run that records a test's data downloads
    the one new video rather than the season it belongs to.
    """
    with ExitStack() as stack:
        for plugin_class in _grouped_download_overrides():
            stack.enter_context(
                patch.object(
                    plugin_class,
                    _GROUPED_DOWNLOAD,
                    _serve_before_grouping(plugin_class.__dict__[_GROUPED_DOWNLOAD]),
                ),
            )
        yield


# TODO: Validate
@contextmanager
def mock_update() -> Generator[None]:
    """Mock updates by incrementing `data_timestamp`."""

    # TODO: Validate
    def _mock(self: BaseFile[Any], update_at: datetime | None = None) -> None:
        if not self.is_outdated(update_at):
            return
        record = self._existing_database_record
        if record is None:
            return
        logger.debug(f"Mock Updating {record.key}")
        record.data_timestamp += timedelta(minutes=1)

    with patch.object(BaseFile, "download_if_outdated", _mock):
        yield
