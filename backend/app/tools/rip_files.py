# TODO: Validate

from app.constants import BACKEND_FOLDER, PROJECT_FOLDER

VENV_PATH = BACKEND_FOLDER / ".venv"
PACKAGES_PATH = VENV_PATH / "Lib" / "site-packages"

GAPI_PLUGINS = [
    "yt-dlapi",
    "not-yt-dlapi",
    "chirashi",
    "diving-board",
]


# TODO: Validate
def main() -> None:
    for dashed_plugin in GAPI_PLUGINS:
        underscored_plugin = dashed_plugin.replace("-", "_")
        files_path = PACKAGES_PATH / underscored_plugin / "_files"
        desintation_files_path = (
            PROJECT_FOLDER.parent
            / dashed_plugin
            / "src"
            / underscored_plugin
            / "_files"
        )
        for source in files_path.rglob("*"):
            if source.is_dir():
                continue
            destination = desintation_files_path / source.relative_to(files_path)
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(source.read_bytes())


if __name__ == "__main__":
    main()
