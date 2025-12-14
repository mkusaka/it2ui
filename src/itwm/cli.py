from __future__ import annotations

import sys
from dataclasses import dataclass


@dataclass(frozen=True)
class CliResult:
    ok: bool
    message: str = ""


def _print_error(message: str) -> None:
    print(f"itwm: {message}", file=sys.stderr)


def main() -> None:
    try:
        import iterm2
    except Exception:
        _print_error(
            "Missing dependency 'iterm2'. Run `uv sync` and ensure you're on macOS with iTerm2 installed."
        )
        raise SystemExit(2)

    async def _amain(connection: object) -> None:
        from itwm.backend.iterm2_backend import Iterm2Backend
        from itwm.tui.app import ItwmApp

        backend = Iterm2Backend(connection)

        try:
            snapshot = await backend.snapshot()
        except Exception as e:
            _print_error(str(e))
            raise SystemExit(1)

        app = ItwmApp(backend=backend, initial_snapshot=snapshot)
        await app.run_async()

    try:
        iterm2.run_until_complete(_amain)  # type: ignore[attr-defined]
    except KeyboardInterrupt:
        raise SystemExit(130)
