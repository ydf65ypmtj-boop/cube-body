#!/bin/bash
# Cube「体」起動スクリプト (冪等: 起動済みなら何もしない)
# Xvfb :99 (1280x800x24) + openbox + fcitx5/mozc を D-Bus セッションごと起動する。
# 接続に必要な環境変数は ~/.desktop_env に保存される。
# 依存パッケージが無い環境 (新規 Codespace 等) では初回だけ apt で入れる。
if pgrep -f "Xvfb :99" >/dev/null && pgrep -x openbox >/dev/null; then
  echo "body already running (Xvfb :99 + openbox)"
  exit 0
fi

missing=0
for c in Xvfb openbox xdotool scrot fcitx5 dbus-launch; do
  command -v "$c" >/dev/null 2>&1 || missing=1
done
if [ "$missing" = "1" ]; then
  echo "installing body dependencies (first run only)..."
  sudo apt-get update -qq > /tmp/cs_body_apt.log 2>&1
  sudo apt-get install -y -qq xvfb openbox xdotool scrot fcitx5 fcitx5-mozc dbus-x11 mousepad >> /tmp/cs_body_apt.log 2>&1 \
    || echo "WARNING: apt install failed; see /tmp/cs_body_apt.log"
fi

ENVF=~/.desktop_env
if [ -f "$ENVF" ]; then set -a; . "$ENVF"; set +a; fi
if [ -z "$DBUS_SESSION_BUS_ADDRESS" ] || ! dbus-send --session --dest=org.freedesktop.DBus --type=method_call /org/freedesktop/DBus org.freedesktop.DBus.ListNames >/dev/null 2>&1; then
  eval "$(dbus-launch --sh-syntax)"
  {
    echo "DISPLAY=:99"
    echo "DBUS_SESSION_BUS_ADDRESS=$DBUS_SESSION_BUS_ADDRESS"
    echo "DBUS_SESSION_BUS_PID=$DBUS_SESSION_BUS_PID"
    echo "GTK_IM_MODULE=fcitx"
    echo "QT_IM_MODULE=fcitx"
    echo "XMODIFIERS=@im=fcitx"
  } > "$ENVF"
  export DISPLAY=:99 GTK_IM_MODULE=fcitx QT_IM_MODULE=fcitx XMODIFIERS=@im=fcitx
fi
export DISPLAY=:99
if ! pgrep -f "Xvfb :99" >/dev/null; then
  Xvfb :99 -screen 0 1280x800x24 > /tmp/xvfb.log 2>&1 &
  sleep 2
fi
if ! pgrep -x openbox >/dev/null; then
  openbox > /tmp/openbox.log 2>&1 &
  sleep 1
fi
if ! pgrep -x fcitx5 >/dev/null; then
  fcitx5 -d > /tmp/fcitx.log 2>&1
  sleep 2
fi
echo "desktop ready on :99 (dbus: ${DBUS_SESSION_BUS_ADDRESS:-none})"
