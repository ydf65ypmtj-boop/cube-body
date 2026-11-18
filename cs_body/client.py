#!/usr/bin/env python3
"""Codespace body client: Simular Box MCP クライアントと同じ CLI・出力契約で、
Codespace 上の仮想デスクトップ (Xvfb :99 + openbox) を体として駆動する。

契約 (agent.py の box_call / iMac 版 box_client と同一):
  client.py call-tool --name <tool> --arguments-file <json>
  → stdout に {"content": [{"type":"text","text":...} |
                           {"type":"image","data":<base64>,"mimeType":"image/png"}],
               "isError": bool} を出し、isError なら終了コード 1。

対応ツール:
  screenshot    {box, max_edge}                 scrot で PNG を返す
  computer_act  {box, action, x, y, text, key, keys, direction, amount}
                action: click / double_click / right_click / type / key /
                        hotkey / scroll (xdotool)
  shell         {box, command, timeout_s}       bash 実行、出力テキストを返す
  browser_tabs  {box}                           Chrome のタブ (DevTools 9222 が
                                                あれば URL+title、無ければ
                                                ウィンドウタイトルのみ)
  browser_snapshot {box}                        同上のテキスト化 (簡易版)
  computer_state {box, query, max_edge}         ウィンドウ一覧テキスト (簡易版)
"""
import argparse
import base64
import json
import os
import subprocess
import sys
import time
import urllib.request

HOME = os.path.expanduser("~")
SHOT_PATH = "/tmp/cs_body_shot.png"

KEYMAP = {
    "return": "Return", "enter": "Return", "escape": "Escape", "esc": "Escape",
    "tab": "Tab", "backspace": "BackSpace", "delete": "Delete", "del": "Delete",
    "up": "Up", "down": "Down", "left": "Left", "right": "Right",
    "space": "space", "home": "Home", "end": "End",
    "pageup": "Page_Up", "pagedown": "Page_Down",
    "ctrl": "ctrl", "control": "ctrl", "alt": "alt", "shift": "shift",
    "super": "super", "meta": "super", "cmd": "super", "win": "super",
}


def load_env() -> dict:
    env = dict(os.environ)
    env["DISPLAY"] = ":99"
    try:
        with open(os.path.join(HOME, ".desktop_env")) as f:
            for line in f:
                line = line.strip()
                if "=" in line and not line.startswith("#"):
                    k, v = line.split("=", 1)
                    env[k] = v
    except FileNotFoundError:
        pass
    env["DISPLAY"] = ":99"
    return env


ENV = load_env()


def run(cmd, timeout=60, env=None):
    return subprocess.run(cmd, env=env or ENV, capture_output=True,
                          text=True, timeout=timeout)


def ensure_desktop() -> None:
    """Xvfb :99 が応答しなければ start_body.sh で起動する (冪等)。"""
    p = run(["xdotool", "getdisplaygeometry"], timeout=10)
    if p.returncode == 0:
        return
    start = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "start_body.sh")
    subprocess.run(["bash", start], capture_output=True, text=True,
                   timeout=60)
    global ENV
    ENV = load_env()
    p = run(["xdotool", "getdisplaygeometry"], timeout=10)
    if p.returncode != 0:
        raise RuntimeError("desktop :99 is not responding after start_body.sh")


def xdotool(*args, timeout=60):
    p = run(["xdotool", *args], timeout=timeout)
    if p.returncode != 0:
        raise RuntimeError(f"xdotool {args[0]} failed: {p.stderr[:200]}")
    return p.stdout.strip()


def map_key(k: str) -> str:
    return KEYMAP.get(k.strip().lower(), k.strip())


# ---------------------------------------------------------------- tools
def tool_screenshot(args: dict) -> list:
    ensure_desktop()
    p = run(["scrot", "-o", SHOT_PATH], timeout=30)
    if p.returncode != 0 or not os.path.exists(SHOT_PATH):
        raise RuntimeError(f"scrot failed: {p.stderr[:200]}")
    with open(SHOT_PATH, "rb") as f:
        data = base64.b64encode(f.read()).decode()
    return [{"type": "image", "data": data, "mimeType": "image/png"}]


def tool_computer_act(args: dict) -> list:
    ensure_desktop()
    action = args.get("action", "")
    x, y = args.get("x"), args.get("y")
    if action in ("click", "double_click", "right_click"):
        xdotool("mousemove", str(int(x)), str(int(y)))
        btn = "3" if action == "right_click" else "1"
        if action == "double_click":
            xdotool("click", "--repeat", "2", "--delay", "80", btn)
        else:
            xdotool("click", btn)
        return [{"type": "text", "text": f"{action} at ({x},{y})"}]
    if action == "move":
        xdotool("mousemove", str(int(x)), str(int(y)))
        return [{"type": "text", "text": f"moved to ({x},{y})"}]
    if action == "type":
        text = args.get("text", "")
        p = run(["xdotool", "type", "--delay", "12", "--", text], timeout=120)
        if p.returncode != 0:
            raise RuntimeError(f"xdotool type failed: {p.stderr[:200]}")
        return [{"type": "text", "text": f"typed {len(text)} chars"}]
    if action == "key":
        key = map_key(str(args.get("key", "")))
        xdotool("key", key)
        return [{"type": "text", "text": f"key {key}"}]
    if action == "hotkey":
        keys = [map_key(str(k)) for k in args.get("keys", [])]
        combo = "+".join(keys)
        xdotool("key", combo)
        return [{"type": "text", "text": f"hotkey {combo}"}]
    if action == "scroll":
        if x is not None and y is not None:
            xdotool("mousemove", str(int(x)), str(int(y)))
        direction = args.get("direction", "down")
        amount = max(1, int(args.get("amount", 3)))
        btn = "5" if direction == "down" else "4"
        xdotool("click", "--repeat", str(amount), btn)
        return [{"type": "text", "text": f"scrolled {direction} {amount}"}]
    raise ValueError(f"unsupported action: {action}")


def tool_shell(args: dict) -> list:
    command = args.get("command", "")
    timeout_s = int(args.get("timeout_s", 30))
    p = subprocess.run(["bash", "-lc", command], env=load_env(),
                       capture_output=True, text=True,
                       timeout=max(timeout_s + 10, 30))
    out = p.stdout
    if p.stderr:
        out += ("\n" if out else "") + p.stderr
    if p.returncode != 0:
        raise ToolError(out.strip() or f"exit code {p.returncode}")
    return [{"type": "text", "text": out}]


def _chrome_targets() -> list | None:
    try:
        req = urllib.request.Request("http://127.0.0.1:9222/json/list")
        with urllib.request.urlopen(req, timeout=3) as r:
            return json.loads(r.read())
    except Exception:
        return None


def tool_browser_tabs(args: dict) -> list:
    targets = _chrome_targets()
    if targets:
        lines = [f"{t.get('title','')} {t.get('url','')}"
                 for t in targets if t.get("type") == "page"]
        return [{"type": "text", "text": "\n".join(lines)}]
    ensure_desktop()
    names = xdotool("search", "--onlyvisible", "--class", "google-chrome",
                    "getwindowname", "%@", timeout=15) \
        if _has_chrome_window() else ""
    return [{"type": "text", "text": names}]


def _has_chrome_window() -> bool:
    p = run(["xdotool", "search", "--class", "google-chrome"], timeout=15)
    return p.returncode == 0 and bool(p.stdout.strip())


def tool_browser_snapshot(args: dict) -> list:
    targets = _chrome_targets()
    if targets:
        lines = [f"{t.get('title','')} {t.get('url','')}"
                 for t in targets if t.get("type") == "page"]
        return [{"type": "text", "text": "\n".join(lines)}]
    return tool_browser_tabs(args)


def tool_computer_state(args: dict) -> list:
    ensure_desktop()
    p = run(["xdotool", "search", "--onlyvisible", "getwindowname", "%@"],
            timeout=15)
    names = p.stdout.strip()
    active = run(["xdotool", "getactivewindow", "getwindowname"], timeout=15)
    text = f"active: {active.stdout.strip()}\nwindows:\n{names}"
    return [{"type": "text", "text": text}]


TOOLS = {
    "screenshot": tool_screenshot,
    "computer_act": tool_computer_act,
    "shell": tool_shell,
    "browser_tabs": tool_browser_tabs,
    "browser_snapshot": tool_browser_snapshot,
    "computer_state": tool_computer_state,
}


class ToolError(RuntimeError):
    """isError=True でテキストとして返すための例外 (shell の非0終了など)。"""


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    ct = sub.add_parser("call-tool")
    ct.add_argument("--name", required=True)
    ct.add_argument("--arguments-file", required=True)
    sub.add_parser("list-tools")
    a = ap.parse_args()

    if a.cmd == "list-tools":
        print(json.dumps({"tools": [{"name": n} for n in TOOLS]}))
        return 0

    with open(a.arguments_file) as f:
        args = json.load(f)
    fn = TOOLS.get(a.name)
    try:
        if fn is None:
            raise ToolError(f"unknown tool: {a.name}")
        content = fn(args)
        print(json.dumps({"content": content, "isError": False}))
        return 0
    except ToolError as e:
        print(json.dumps({"content": [{"type": "text", "text": str(e)}],
                          "isError": True}))
        return 1
    except Exception as e:
        print(json.dumps({"content": [{"type": "text",
                                       "text": f"{type(e).__name__}: {e}"}],
                          "isError": True}))
        return 1


if __name__ == "__main__":
    sys.exit(main())
