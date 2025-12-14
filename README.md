# itwm

iTerm2 の Window / Tab / Session を一覧・検索し、選択した Session にフォーカスするための TUI ツールです。さらに `Ctrl-h/j/k/l` で隣接ペインへフォーカス移動できます。iTerm2 の Python API（`iterm2`）に接続するため、iTerm2 上で実行することが前提です。レイアウト保存/復元や自動分割などは非対応です（本リポジトリのスコープ外）。

## Prerequisites

- macOS + iTerm2
- iTerm2: `Prefs > General > Magic > Enable Python API` を有効化
- 初回接続時に iTerm2 から許可ダイアログが出るので許可
  - うまく接続できない場合は iTerm2 側で “Allow all apps to connect” を有効にするか、接続を許可したアプリ一覧に追加してください

## Install (uv)

```bash
uv sync
```

依存関係を更新した場合は `uv lock` を実行して `uv.lock` を更新してください。

開発（pytest/mypy）を使う場合:

```bash
uv sync --extra dev
```

## Run

```bash
uv run itwm
```

### Keys

- `/` or `Ctrl-f`: focus search
- `Esc`: leave search (and clear query)
- `Enter`: activate selected session
- `Ctrl-h/j/k/l`: focus adjacent pane (left/down/up/right)
- `q`: quit

## Tests / Typecheck

```bash
uv run pytest
uv run mypy src/itwm tests
```

## Troubleshooting

- `iTerm2 is not running` / `Failed to connect`: iTerm2 を起動し、Python API を有効にしているか確認してください。
- `Permission denied`: iTerm2 の許可ダイアログを確認し、拒否してしまった場合は iTerm2 の設定から許可をやり直してください。

## Future work (optional)

- Layout save/restore
- Pane resizing commands
- Background daemon / global hotkey integration
