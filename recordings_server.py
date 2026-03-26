#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TS3AudioBot 录音回放 Web 服务器
================================
纯标准库实现，无需 pip 安装任何依赖。

配置文件：recordings-web.json（与本脚本放在同一目录，即 Bot 工作目录）
前端页面：recordings-ui/index.html（同上）
录音数据：Recordings/ 目录（插件自动生成）

运行方式：
  python recordings_server.py
"""

import http.server
import json
import os
import sys
import threading
import urllib.error
import urllib.request
import uuid
from pathlib import Path

# ──────────────────────────────────────────────
# 配置（可被 recordings-web.json 覆盖）
# ──────────────────────────────────────────────
CONFIG_FILE    = "recordings-web.json"
RECORDINGS_DIR = Path("Recordings")
UI_FILE        = Path("recordings-ui") / "index.html"

_port       = 8765
_ai_base    = ""
_ai_key     = ""
_ai_model   = "whisper-1"


def load_config():
    global _port, _ai_base, _ai_key, _ai_model
    if not os.path.exists(CONFIG_FILE):
        return
    try:
        with open(CONFIG_FILE, encoding="utf-8") as f:
            cfg = json.load(f)
        _port     = int(cfg.get("port",         _port))
        _ai_base  = cfg.get("ai_base_url",  _ai_base)
        _ai_key   = cfg.get("ai_api_key",   _ai_key)
        _ai_model = cfg.get("ai_model",     _ai_model)
        print("[recordings] 已加载 %s，端口: %s" % (CONFIG_FILE, _port))
    except Exception as e:
        print("[recordings] 读取 %s 失败: %s，使用默认配置" % (CONFIG_FILE, e))


# ──────────────────────────────────────────────
# HTTP 请求处理器
# ──────────────────────────────────────────────
class Handler(http.server.BaseHTTPRequestHandler):

    # 关闭 access log，保持终端整洁
    def log_message(self, fmt, *args):
        pass

    # ── CORS 预检 ──
    def do_OPTIONS(self):
        self.send_response(200)
        self._cors()
        self.end_headers()

    # ── GET ──
    def do_GET(self):
        path = self.path.split("?")[0]
        if path in ("/", "/index.html"):
            self._serve_index()
        elif path == "/api/sessions":
            self._api_sessions()
        elif path.startswith("/api/sessions/"):
            session_id = urllib.parse.unquote(path[len("/api/sessions/"):])
            self._api_session_detail(session_id)
        elif path.startswith("/api/audio/"):
            parts = path.split("/")        # ['', 'api', 'audio', sessionId, filename]
            if len(parts) >= 5:
                session_id = urllib.parse.unquote(parts[3])
                filename   = urllib.parse.unquote(parts[4])
                self._api_audio(session_id, filename)
            else:
                self._respond(400, b"bad request")
        else:
            self._respond(404, b"not found")

    # ── POST ──
    def do_POST(self):
        path = self.path.split("?")[0]
        if path == "/api/transcribe":
            self._api_transcribe()
        else:
            self._respond(404, b"not found")

    # ──────────────────────────────────────────
    # 路由实现
    # ──────────────────────────────────────────

    def _serve_index(self):
        if not UI_FILE.exists():
            self._respond(
                404,
                "找不到 recordings-ui/index.html，请确认文件存在于 Bot 工作目录下。".encode(),
                content_type="text/plain; charset=utf-8",
            )
            return
        data = UI_FILE.read_bytes()
        self._respond(200, data, content_type="text/html; charset=utf-8")

    def _api_sessions(self):
        sessions = []
        if RECORDINGS_DIR.exists():
            dirs = sorted(RECORDINGS_DIR.glob("Session_*"), reverse=True)
            for d in dirs:
                idx = d / "index.json"
                if not idx.exists():
                    continue
                try:
                    entries = json.loads(idx.read_text(encoding="utf-8"))
                    if entries:
                        max_end = max(
                            e.get("StartOffsetMs", 0) + e.get("DurationMs", 0)
                            for e in entries
                        )
                    else:
                        max_end = 0
                    seen = {}
                    speakers = [
                        seen.setdefault(e.get("ClientName", ""), e.get("ClientName", ""))
                        for e in entries
                        if e.get("ClientName", "") not in seen
                    ]
                    sessions.append({
                        "id":             d.name,
                        "startTime":      d.name.replace("Session_", ""),
                        "entryCount":     len(entries),
                        "totalDurationMs": max_end,
                        "speakers":       speakers,
                    })
                except Exception as e:
                    print(f"[recordings] 读取 {d.name} 失败: {e}")
        self._json(sessions)

    def _api_session_detail(self, session_id):
        if not self._safe_id(session_id):
            self._respond(400, b"invalid id")
            return
        idx = RECORDINGS_DIR / session_id / "index.json"
        if not idx.exists():
            self._respond(404, b"session not found")
            return
        self._respond(200, idx.read_bytes(), content_type="application/json")

    def _api_audio(self, session_id, filename):
        if not self._safe_id(session_id) or not self._safe_id(filename):
            self._respond(400, b"invalid path")
            return
        filepath = RECORDINGS_DIR / session_id / filename
        if not filepath.exists():
            self._respond(404, b"file not found")
            return

        file_size   = filepath.stat().st_size
        range_hdr   = self.headers.get("Range", "")
        self.send_response(200)
        self.send_header("Content-Type", "audio/wav")
        self.send_header("Accept-Ranges", "bytes")
        self._cors()

        if range_hdr.startswith("bytes="):
            parts = range_hdr[6:].split("-")
            start = int(parts[0]) if parts[0] else 0
            end   = int(parts[1]) if len(parts) > 1 and parts[1] else file_size - 1
            end   = min(end, file_size - 1)
            length = end - start + 1
            self.send_response(206)          # override
            self.send_header("Content-Range", f"bytes {start}-{end}/{file_size}")
            self.send_header("Content-Length", str(length))
            self.end_headers()
            with open(filepath, "rb") as f:
                f.seek(start)
                self.wfile.write(f.read(length))
        else:
            self.send_header("Content-Length", str(file_size))
            self.end_headers()
            with open(filepath, "rb") as f:
                self.wfile.write(f.read())

    def _api_transcribe(self):
        if not _ai_base or not _ai_key:
            self._json({"error": "AI 服务未配置，请在 recordings-web.json 中填写 ai_base_url 和 ai_api_key"}, 503)
            return

        try:
            length = int(self.headers.get("Content-Length", 0))
            body   = json.loads(self.rfile.read(length))
        except Exception:
            self._json({"error": "无效的 JSON 请求体"}, 400)
            return

        session_id = body.get("sessionId", "")
        filename   = body.get("filename",  "")

        if not session_id or not filename:
            self._json({"error": "需要 sessionId 和 filename"}, 400)
            return
        if not self._safe_id(session_id) or not self._safe_id(filename):
            self._json({"error": "路径非法"}, 400)
            return

        filepath = RECORDINGS_DIR / session_id / filename
        if not filepath.exists():
            self._json({"error": "音频文件不存在"}, 404)
            return

        audio_bytes = filepath.read_bytes()
        boundary    = uuid.uuid4().hex

        # 手动拼接 multipart/form-data
        body_parts = (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="model"\r\n\r\n'
            f"{_ai_model}\r\n"
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
            f"Content-Type: audio/wav\r\n\r\n"
        ).encode() + audio_bytes + f"\r\n--{boundary}--\r\n".encode()

        req = urllib.request.Request(
            f"{_ai_base.rstrip('/')}/audio/transcriptions",
            data=body_parts,
            headers={
                "Authorization":  f"Bearer {_ai_key}",
                "Content-Type":   f"multipart/form-data; boundary={boundary}",
                "Content-Length": str(len(body_parts)),
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                result = resp.read()
            self._respond(200, result, content_type="application/json")
        except urllib.error.HTTPError as e:
            self._respond(e.code, e.read(), content_type="application/json")
        except Exception as e:
            print(f"[recordings] AI 请求失败: {e}")
            self._json({"error": f"AI 服务请求失败: {e}"}, 502)

    # ──────────────────────────────────────────
    # 工具方法
    # ──────────────────────────────────────────

    @staticmethod
    def _safe_id(s: str) -> bool:
        """防止路径穿越攻击"""
        return s and ".." not in s and "/" not in s and "\\" not in s

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin",  "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def _respond(self, code: int, data: bytes, content_type: str = "text/plain"):
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self._cors()
        self.end_headers()
        self.wfile.write(data)

    def _json(self, obj, code: int = 200):
        data = json.dumps(obj, ensure_ascii=False).encode()
        self._respond(code, data, content_type="application/json")


# urllib.parse 需要额外导入
import urllib.parse


# ──────────────────────────────────────────────
# 启动入口
# ──────────────────────────────────────────────
def main():
    load_config()

    server = http.server.ThreadingHTTPServer(("0.0.0.0", _port), Handler)
    print(f"[recordings] 录音 Web 界面启动 → http://localhost:{_port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[recordings] 已停止")
        server.shutdown()


if __name__ == "__main__":
    main()
