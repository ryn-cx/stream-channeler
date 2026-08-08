# TODO: Validate
"""Context managers for PluginValidator."""

from collections.abc import Generator
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from unittest.mock import patch

from loguru import logger

from app.constants import ALL_TEST_FILES_FOLDER
from plugins.utils.base_plugin import BaseFile


def _owner_key(file: BaseFile[Any]) -> str:
    """Return the plugin a file class belongs to.

    Read off where the class is declared rather than off the plugin the file is
    being downloaded for, because a plugin downloads files belonging to another
    one (TMDB's, to fill in what its own website leaves out) and both have to
    reach the same stored copy.
    """
    return type(file).__module__.split(".")[1]


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


def _escape(character: str) -> str:
    return f"{ESCAPE_PREFIX}{ord(character):02X}"


def encode_name(segment: str) -> str:
    """Return one part of a key as a name the file system will take.

    Every character it will not hold becomes the prefix followed by the
    character's code, which `decode_name` reads back, so a key survives being
    stored and loaded as exactly the key it was.
    """
    encoded = "".join(
        _escape(character) if character in _ESCAPED_CHARACTERS else character
        for character in segment
    )
    if encoded.endswith(_ESCAPED_ENDINGS):
        encoded = encoded[:-1] + _escape(encoded[-1])
    return encoded


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


def stored_path(owner_key: str, file_key: str) -> Path:
    """Return where the file `file_key` names is kept among the stored test files.

    A file is stored under the plugin that owns it, at the path its own key
    describes, so the stored files are laid out the way the plugins name them
    and the same file is stored once no matter how many tests reach for it. Each
    part of the key is encoded on its own, leaving the separators between them
    as the folders they describe.
    """
    encoded = "/".join(encode_name(part) for part in file_key.split("/"))
    return ALL_TEST_FILES_FOLDER / encode_name(owner_key) / encoded


def stored_key(path: Path) -> tuple[str, str]:
    """Return the owning plugin and file key that `path` was stored for."""
    owner, *rest = path.relative_to(ALL_TEST_FILES_FOLDER).parts
    return decode_name(owner), "/".join(decode_name(part) for part in rest)


def stored_file_path(file: BaseFile[Any]) -> Path:
    """Return where `file` is kept among the stored test files."""
    return stored_path(_owner_key(file), file.file_key())


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
    def _download_if_outdated(
        self: BaseFile[Any],
        update_at: datetime | None = None,
    ) -> None:
        if not self.is_outdated(update_at):
            return

        path = stored_file_path(self)
        if _exists(path):
            logger.debug(f"Serving {self.file_key()} from {path}")
            self.write(path.read_text(encoding="utf-8") or None)
            return

        original_download_if_outdated(self, update_at)
        downloaded.append(self.file_key())
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(self.database_record.content or "", encoding="utf-8")
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


@contextmanager
def track_requested_files() -> Generator[list[str]]:
    """Record the key of every file that was asked for.

    Every file a test needs is stored before it runs, so asking for one does not
    download it. What a test can check is therefore which files a plugin reached
    for, which is what this records, rather than which ones came over the
    network.
    """
    requested: list[str] = []
    original_download_if_outdated = BaseFile[Any].download_if_outdated

    def _download_if_outdated(
        self: BaseFile[Any],
        update_at: datetime | None = None,
    ) -> None:
        requested.append(self.file_key())
        original_download_if_outdated(self, update_at)

    with patch.object(BaseFile, "download_if_outdated", _download_if_outdated):
        yield requested


@contextmanager
def mock_update() -> Generator[None]:
    """Mock updates by incrementing `data_timestamp`."""

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
