# cube-body

Cube の PC操作エージェントの「体」になる GitHub Codespace 用リポジトリ。

## 使い方

1. このリポジトリから Codespace を作る（Code → Codespaces → Create codespace on main）
2. 起動時に `.devcontainer/start-tailscale.sh` が自動で走り、Tailscale SSH が有効になる
   - **初回だけ**：新しい Codespace は Tailscale に未登録のため、`tailscale up` がログイン URL を出すことがある。その場合は Codespace のターミナルで `cat /tmp/tailscale-autostart.log` を見て URL を開き、GitHub で承認する。2回目以降の起動では不要
3. 仮想デスクトップ（Xvfb :99 + openbox）は、最初のスクリーンショット呼び出しで `cs_body/start_body.sh` が自動起動する（依存パッケージも初回だけ自動で入る）

## 中身

- `cs_body/client.py` — 体ドライバ。Simular Box クライアントと同じ CLI・出力契約（`call-tool --name <tool> --arguments-file <json>`）で、screenshot / computer_act / shell / browser_tabs 等を scrot・xdotool で実行する
- `cs_body/start_body.sh` — 仮想デスクトップの冪等な起動スクリプト
- `.devcontainer/` — Codespace 起動時の Tailscale 自動接続
