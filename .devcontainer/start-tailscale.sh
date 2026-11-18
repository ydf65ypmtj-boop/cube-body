#!/bin/bash
# Codespace 起動のたびに Tailscale SSH を自動で立ち上げる (postStartCommand)。
# tailscale が入っていない環境では先に公式スクリプトで入れる。
# バックグラウンドで実行し、起動をブロックしない。ログは /tmp/tailscale-autostart.log
nohup bash -c '
  if ! command -v tailscale >/dev/null 2>&1; then
    echo "tailscale not found; installing..."
    curl -fsSL https://tailscale.com/install.sh | sh
  fi
  sudo tailscaled --tun=userspace-networking --socks5-server=localhost:1055 &
  sleep 3
  sudo tailscale up --ssh
' > /tmp/tailscale-autostart.log 2>&1 &
echo "tailscale autostart launched (log: /tmp/tailscale-autostart.log)"
