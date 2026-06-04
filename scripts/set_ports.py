from collections.abc import Mapping
from pathlib import Path

from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = ROOT / ".env"
FRONTEND_ENV_PATH = ROOT / "frontend" / ".env"

BASE_PORTS = {
    "PROXY_HTTP_PORT": 80,
    "PROXY_DASHBOARD_PORT": 8090,
    "DB_PORT": 5432,
    "ADMINER_PORT": 8080,
    "BACKEND_PORT": 8000,
    "BACKEND_TEST_PORT": 8100,
    "MAILCATCHER_WEB_PORT": 1080,
    "MAILCATCHER_SMTP_PORT": 1025,
    "FRONTEND_PORT": 5173,
    "FRONTEND_TEST_PORT": 5273,
    "PLAYWRIGHT_PORT": 9323,
}


def read_project_number() -> int:
    raw = dotenv_values(ENV_PATH).get("PROJECT_NUMBER")
    if not raw:
        raise ValueError("PROJECT_NUMBER not found in .env or is empty")
    return int(raw)


def calculate_offset(project_number: int) -> int:
    if project_number < 0:
        raise ValueError("PROJECT_NUMBER must be a non-negative integer")

    used: set[int] = set()
    offset = 0
    for i in range(project_number + 1):
        offset = i
        while any(base + offset in used for base in BASE_PORTS.values()):
            offset += 1
        used.update(base + offset for base in BASE_PORTS.values())
    return offset


def get_urls(ports: dict[str, int]) -> dict[str, str]:
    # Host-side test tooling (playwright privateApi, mailcatcher reader) targets
    # the test stack so frontend tests don't touch the dev `app` database.
    return {
        "VITE_API_URL": f"http://localhost:{ports['BACKEND_TEST_PORT']}",
        "MAILCATCHER_HOST": f"http://localhost:{ports['MAILCATCHER_WEB_PORT']}",
        "FRONTEND_TEST_URL": f"http://localhost:{ports['FRONTEND_TEST_PORT']}",
    }


def render_block(pairs: Mapping[str, object]) -> str:
    return "\n".join(f"{name}={value}" for name, value in pairs.items())


def strip_managed(text: str, managed_keys: set[str]) -> str:
    return "\n".join(
        line
        for line in text.splitlines()
        if line.split("=", 1)[0].strip() not in managed_keys
    )


def upsert_block(path: Path, block: str, managed_keys: set[str]) -> None:
    text = path.read_text() if path.exists() else ""
    before = strip_managed(text, managed_keys).rstrip("\n")
    new_text = f"{before}\n\n{block}\n" if before else f"{block}\n"
    path.write_text(new_text)


if __name__ == "__main__":
    offset = calculate_offset(read_project_number())
    ports = {name: base + offset for name, base in BASE_PORTS.items()}
    urls = get_urls(ports)

    root_block = render_block({**ports, **urls})
    upsert_block(ENV_PATH, root_block, set(ports) | set(urls))

    # Vite (host `bun run dev`) needs VITE_API_URL pointing at the DEV backend.
    frontend_urls = {
        "VITE_API_URL": f"http://localhost:{ports['BACKEND_PORT']}",
        "MAILCATCHER_HOST": f"http://localhost:{ports['MAILCATCHER_WEB_PORT']}",
    }
    frontend_block = render_block(frontend_urls)
    upsert_block(FRONTEND_ENV_PATH, frontend_block, set(urls))

    print(f"Wrote {ENV_PATH}:\n{root_block}\n")
    print(f"Wrote {FRONTEND_ENV_PATH}:\n{frontend_block}")
