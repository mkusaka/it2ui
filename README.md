# it2ui

`it2ui` is a TUI tool to list iTerm2 Window/Tab/Session, search them, and focus (activate) the selected session. It also supports moving focus to an adjacent pane with `Ctrl-h/j/k/l`. It is designed to run inside iTerm2 and connects via the iTerm2 Python API (`iterm2`). Layout save/restore and automated window/pane creation are explicitly out of scope for this repository.

## Prerequisites

- macOS + iTerm2
- iTerm2: enable `Prefs > General > Magic > Enable Python API`
- On the first run, iTerm2 will show a permission prompt; allow it.
  - If connection still fails, enable “Allow all apps to connect” or add your terminal app to the allowed list in iTerm2.

## Install (uv)

```bash
uv sync
```

This repo commits `uv.lock` for reproducible installs. After updating dependencies, run `uv lock` and commit the updated `uv.lock`.

For development (pytest/mypy):

```bash
uv sync --extra dev
```

## Run

```bash
uv run it2ui
```

### Keys

- `/` or `Ctrl-f`: focus search (edit mode)
- Typing while in navigate mode: start search and append typed character
- `Esc`: leave search (back to navigate mode)
- `Up/Down`: move selection (works in both modes)
- `Enter`: activate selected session
- `Ctrl-h/j/k/l`: focus adjacent pane (left/down/up/right)
- `q`: quit

## Tests / Typecheck

```bash
uv run pytest
uv run mypy src/it2ui tests
```

## Troubleshooting

- `iTerm2 is not running` / `Failed to connect`: make sure iTerm2 is running and the Python API is enabled.
- `Permission denied`: check the iTerm2 permission prompt; if you denied it, reset permissions in iTerm2 and try again.

## Future work (optional)

- Layout save/restore
- Pane resizing commands
- Background daemon / global hotkey integration
