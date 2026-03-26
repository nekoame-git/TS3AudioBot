#!/usr/bin/env python3
"""
TS3AudioBot 录音回放 + 权限配置 Web 服务器
=========================================
纯标准库实现，无需 pip 安装任何依赖。
"""

import base64
import http.server
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    import tomllib
except Exception:
    tomllib = None

CONFIG_FILE = "recordings-web.json"
RECORDINGS_DIR = Path("Recordings")
UI_FILE = Path("recordings-ui") / "index.html"
TEMPLATE_RIGHTS_FILE = Path("rights.toml")

_port = 8765
_ai_base = ""
_ai_key = ""
_ai_model = "whisper-1"

_rights_path = ""
_ts3ab_api_base = ""
_ts3ab_api_user = ""
_ts3ab_api_token = ""


def load_config() -> None:
    global _port, _ai_base, _ai_key, _ai_model
    global _rights_path, _ts3ab_api_base, _ts3ab_api_user, _ts3ab_api_token

    if not os.path.exists(CONFIG_FILE):
        return

    try:
        with open(CONFIG_FILE, encoding="utf-8") as f:
            cfg = json.load(f)
        _port = int(cfg.get("port", _port))
        _ai_base = str(cfg.get("ai_base_url", _ai_base or "")).strip()
        _ai_key = str(cfg.get("ai_api_key", _ai_key or "")).strip()
        _ai_model = str(cfg.get("ai_model", _ai_model or "")).strip()

        _rights_path = str(cfg.get("rights_file", _rights_path or "")).strip()
        _ts3ab_api_base = str(cfg.get("ts3ab_api_base", _ts3ab_api_base or "")).strip()
        _ts3ab_api_user = str(cfg.get("ts3ab_api_user", _ts3ab_api_user or "")).strip()
        _ts3ab_api_token = str(cfg.get("ts3ab_api_token", _ts3ab_api_token or "")).strip()

        print(f"[recordings] 已加载 {CONFIG_FILE}，端口: {_port}")
    except Exception as e:
        print(f"[recordings] 读取 {CONFIG_FILE} 失败: {e}，使用默认配置")


def _ensure_list(v: Any) -> List[Any]:
    if v is None:
        return []
    if isinstance(v, list):
        return v
    return [v]


def _normalize_string_list(v: Any) -> List[str]:
    return [str(x) for x in _ensure_list(v) if str(x).strip()]


def _is_bare_key(k: str) -> bool:
    return bool(re.match(r"^[A-Za-z0-9_-]+$", k))


def _toml_key(k: str) -> str:
    return k if _is_bare_key(k) else json.dumps(k, ensure_ascii=False)


def _toml_value(v: Any) -> str:
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return str(v)
    if isinstance(v, list):
        return "[ " + ", ".join(_toml_value(x) for x in v) + " ]"
    if isinstance(v, dict):
        parts = [f"{_toml_key(str(k))} = {_toml_value(val)}" for k, val in v.items()]
        return "{ " + ", ".join(parts) + " }"
    return json.dumps(str(v), ensure_ascii=False)


def _table_to_model(table: Dict[str, Any]) -> Dict[str, Any]:
    reserved = {"+", "-", "include", "rule", "groups"}

    block: Dict[str, Any] = {
        "plus": _normalize_string_list(table.get("+")),
        "minus": _normalize_string_list(table.get("-")),
        "include": _normalize_string_list(table.get("include")),
        "matchers": {},
        "rules": [],
        "groups": [],
    }

    for k, v in table.items():
        if k in reserved:
            continue
        if k.startswith("$"):
            if isinstance(v, dict):
                group = _table_to_model(v)
            else:
                group = {
                    "plus": [],
                    "minus": [],
                    "include": [],
                    "matchers": {},
                    "rules": [],
                    "groups": [],
                }
            group["name"] = k
            block["groups"].append(group)
            continue
        block["matchers"][k] = v

    if isinstance(table.get("rule"), list):
        block["rules"] = [_table_to_model(r) for r in table["rule"] if isinstance(r, dict)]

    return block


def parse_rights_toml(content: str) -> Tuple[bool, Dict[str, Any], str]:
    if tomllib is None:
        return False, {}, "当前 Python 环境不支持 tomllib（需要 Python 3.11+）"

    try:
        parsed = tomllib.loads(content)
    except Exception as e:
        return False, {}, str(e)

    if not isinstance(parsed, dict):
        return False, {}, "TOML 根节点必须是 table"

    model = {"top": _table_to_model(parsed)}
    return True, model, ""


def _emit_block(lines: List[str], block: Dict[str, Any], indent: int = 0) -> None:
    pad = " " * indent

    matchers = block.get("matchers", {})
    if isinstance(matchers, dict):
        for key, val in matchers.items():
            lines.append(f"{pad}{_toml_key(str(key))} = {_toml_value(val)}")

    include_vals = _normalize_string_list(block.get("include"))
    if include_vals:
        lines.append(f"{pad}include = {_toml_value(include_vals)}")

    plus_vals = _normalize_string_list(block.get("plus"))
    if plus_vals:
        lines.append(f"{pad}\"+\" = {_toml_value(plus_vals)}")

    minus_vals = _normalize_string_list(block.get("minus"))
    if minus_vals:
        lines.append(f"{pad}\"-\" = {_toml_value(minus_vals)}")


def model_to_rights_toml(model: Dict[str, Any]) -> str:
    top = model.get("top", {}) if isinstance(model, dict) else {}
    if not isinstance(top, dict):
        top = {}

    lines: List[str] = [
        "# Auto-generated by recordings_server rights webui",
        "# Review before applying in production",
        "",
    ]

    _emit_block(lines, top)

    groups = top.get("groups", [])
    if isinstance(groups, list):
        for g in groups:
            if not isinstance(g, dict):
                continue
            name = str(g.get("name", "")).strip()
            if not name:
                continue
            if not name.startswith("$"):
                name = "$" + name
            lines.append("")
            lines.append(f"[{_toml_key(name)}]")
            _emit_block(lines, g, indent=4)

    def emit_rules(rules: List[Dict[str, Any]], depth: int) -> None:
        header = "rule" + ".rule" * depth
        for rule in rules:
            if not isinstance(rule, dict):
                continue
            lines.append("")
            lines.append(f"[[{header}]]")
            _emit_block(lines, rule, indent=4)

            nested_groups = rule.get("groups", [])
            if isinstance(nested_groups, list) and nested_groups:
                lines.append("")
                lines.append("# Nested groups are not emitted in visual mode.")
                lines.append("# Use raw TOML mode for advanced scoped group declarations.")

            child = rule.get("rules", [])
            if isinstance(child, list) and child:
                emit_rules(child, depth + 1)

    top_rules = top.get("rules", [])
    if isinstance(top_rules, list):
        emit_rules(top_rules, 0)

    return "\n".join(lines).rstrip() + "\n"


class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, fmt: str, *args: Any) -> None:
        return

    def do_OPTIONS(self) -> None:
        self.send_response(200)
        self._cors()
        self.end_headers()

    def do_GET(self) -> None:
        path = self.path.split("?")[0]
        if path in ("/", "/index.html"):
            self._serve_index()
        elif path == "/api/sessions":
            self._api_sessions()
        elif path.startswith("/api/sessions/"):
            session_id = urllib.parse.unquote(path[len("/api/sessions/"):])
            self._api_session_detail(session_id)
        elif path.startswith("/api/audio/"):
            parts = path.split("/")
            if len(parts) >= 5:
                session_id = urllib.parse.unquote(parts[3])
                filename = urllib.parse.unquote(parts[4])
                self._api_audio(session_id, filename)
            else:
                self._respond(400, b"bad request")
        elif path == "/api/rights/file":
            self._api_rights_file()
        elif path == "/api/rights/model":
            self._api_rights_model()
        elif path == "/api/rights/files":
            self._api_rights_files()
        elif path == "/api/rights/template":
            self._api_rights_template()
        else:
            self._respond(404, b"not found")

    def do_POST(self) -> None:
        path = self.path.split("?")[0]
        if path == "/api/transcribe":
            self._api_transcribe()
        elif path == "/api/rights/validate":
            self._api_rights_validate()
        elif path == "/api/rights/save":
            self._api_rights_save()
        elif path == "/api/rights/reload":
            self._api_rights_reload()
        elif path == "/api/rights/compile":
            self._api_rights_compile()
        elif path == "/api/rights/decompile":
            self._api_rights_decompile()
        elif path == "/api/rights/template/init":
            self._api_rights_template_init()
        else:
            self._respond(404, b"not found")

    def _serve_index(self) -> None:
        if not UI_FILE.exists():
            self._respond(
                404,
                "找不到 recordings-ui/index.html，请确认文件存在于 Bot 工作目录下。".encode("utf-8"),
                content_type="text/plain; charset=utf-8",
            )
            return
        self._respond(200, UI_FILE.read_bytes(), content_type="text/html; charset=utf-8")

    def _api_sessions(self) -> None:
        sessions: List[Dict[str, Any]] = []
        if RECORDINGS_DIR.exists():
            dirs = sorted(RECORDINGS_DIR.glob("Session_*"), reverse=True)
            for d in dirs:
                idx = d / "index.json"
                if not idx.exists():
                    continue
                try:
                    entries = json.loads(idx.read_text(encoding="utf-8"))
                    max_end = 0
                    if entries:
                        max_end = max((e.get("StartOffsetMs", 0) + e.get("DurationMs", 0)) for e in entries)
                    seen = {}
                    speakers = [
                        seen.setdefault(e.get("ClientName", ""), e.get("ClientName", ""))
                        for e in entries
                        if e.get("ClientName", "") not in seen
                    ]
                    sessions.append({
                        "id": d.name,
                        "startTime": d.name.replace("Session_", ""),
                        "entryCount": len(entries),
                        "totalDurationMs": max_end,
                        "speakers": speakers,
                    })
                except Exception as e:
                    print(f"[recordings] 读取 {d.name} 失败: {e}")
        self._json(sessions)

    def _api_session_detail(self, session_id: str) -> None:
        if not self._safe_id(session_id):
            self._respond(400, b"invalid id")
            return
        idx = RECORDINGS_DIR / session_id / "index.json"
        if not idx.exists():
            self._respond(404, b"session not found")
            return
        self._respond(200, idx.read_bytes(), content_type="application/json")

    def _api_audio(self, session_id: str, filename: str) -> None:
        if not self._safe_id(session_id) or not self._safe_id(filename):
            self._respond(400, b"invalid path")
            return

        filepath = RECORDINGS_DIR / session_id / filename
        if not filepath.exists():
            self._respond(404, b"file not found")
            return

        file_size = filepath.stat().st_size
        range_hdr = self.headers.get("Range", "")

        if range_hdr.startswith("bytes="):
            parts = range_hdr[6:].split("-", 1)
            try:
                start = int(parts[0]) if parts[0] else 0
                end = int(parts[1]) if len(parts) > 1 and parts[1] else file_size - 1
            except ValueError:
                self._respond(416, b"invalid range")
                return

            if start < 0 or end < start or start >= file_size:
                self._respond(416, b"invalid range")
                return

            end = min(end, file_size - 1)
            length = end - start + 1

            self.send_response(206)
            self.send_header("Content-Type", "audio/wav")
            self.send_header("Accept-Ranges", "bytes")
            self.send_header("Content-Range", f"bytes {start}-{end}/{file_size}")
            self.send_header("Content-Length", str(length))
            self._cors()
            self.end_headers()

            with open(filepath, "rb") as f:
                f.seek(start)
                self.wfile.write(f.read(length))
            return

        self.send_response(200)
        self.send_header("Content-Type", "audio/wav")
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Length", str(file_size))
        self._cors()
        self.end_headers()
        with open(filepath, "rb") as f:
            self.wfile.write(f.read())

    def _api_transcribe(self) -> None:
        if not _ai_base or not _ai_key:
            self._json({"error": "未配置 ai_base_url / ai_api_key"}, 503)
            return

        body, err = self._read_json_body()
        if err:
            self._json({"error": err}, 400)
            return

        session_id = str(body.get("sessionId", "")).strip()
        filename = str(body.get("filename", "")).strip()

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
        boundary = uuid.uuid4().hex

        body_parts = (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="model"\r\n\r\n'
            f"{_ai_model}\r\n"
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
            f"Content-Type: audio/wav\r\n\r\n"
        ).encode("utf-8") + audio_bytes + f"\r\n--{boundary}--\r\n".encode("utf-8")

        req = urllib.request.Request(
            f"{_ai_base.rstrip('/')}/audio/transcriptions",
            data=body_parts,
            headers={
                "Authorization": f"Bearer {_ai_key}",
                "Content-Type": f"multipart/form-data; boundary={boundary}",
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

    def _api_rights_file(self) -> None:
        requested = self._query_param("path")
        path = self._resolve_rights_path(requested_path=requested)
        if not path:
            self._json({"error": "未找到 rights.toml 文件"}, 404)
            return
        try:
            content = path.read_text(encoding="utf-8")
            self._json({"path": str(path.resolve()), "content": content})
        except Exception as e:
            self._json({"error": f"读取 rights 文件失败: {e}"}, 500)

    def _api_rights_model(self) -> None:
        requested = self._query_param("path")
        path = self._resolve_rights_path(requested_path=requested)
        if not path:
            self._json({"error": "未找到 rights.toml 文件"}, 404)
            return

        try:
            content = path.read_text(encoding="utf-8")
        except Exception as e:
            self._json({"error": f"读取 rights 文件失败: {e}"}, 500)
            return

        ok, model, parse_error = parse_rights_toml(content)
        if not ok:
            self._json({
                "path": str(path.resolve()),
                "content": content,
                "warning": f"TOML 解析失败，建议切换原文模式: {parse_error}",
            }, 200)
            return

        self._json({"path": str(path.resolve()), "content": content, "model": model})

    def _api_rights_files(self) -> None:
        files = self._discover_toml_files()
        self._json({"files": files})

    def _api_rights_template(self) -> None:
        template_path = self._resolve_template_path()
        if not template_path:
            self._json({"error": "未找到模板文件 rights.toml"}, 404)
            return
        try:
            content = template_path.read_text(encoding="utf-8")
        except Exception as e:
            self._json({"error": f"读取模板失败: {e}"}, 500)
            return
        self._json({"path": str(template_path.resolve()), "content": content})

    def _api_rights_validate(self) -> None:
        body, err = self._read_json_body()
        if err:
            self._json({"error": err}, 400)
            return

        content = body.get("content")
        if not isinstance(content, str):
            self._json({"error": "content 必须为字符串"}, 400)
            return

        ok, parse_error = self._validate_toml(content)
        if ok:
            self._json({"ok": True, "message": "TOML 语法合法"})
        else:
            self._json({"ok": False, "error": parse_error}, 400)

    def _api_rights_compile(self) -> None:
        body, err = self._read_json_body()
        if err:
            self._json({"error": err}, 400)
            return

        model = body.get("model")
        if not isinstance(model, dict):
            self._json({"error": "model 必须为对象"}, 400)
            return

        try:
            content = model_to_rights_toml(model)
        except Exception as e:
            self._json({"error": f"模型编译失败: {e}"}, 400)
            return

        ok, parse_error = self._validate_toml(content)
        if not ok:
            self._json({"error": f"编译结果 TOML 非法: {parse_error}", "content": content}, 400)
            return

        self._json({"ok": True, "content": content})

    def _api_rights_decompile(self) -> None:
        body, err = self._read_json_body()
        if err:
            self._json({"error": err}, 400)
            return

        content = body.get("content")
        if not isinstance(content, str):
            self._json({"error": "content 必须为字符串"}, 400)
            return

        ok, model, parse_error = parse_rights_toml(content)
        if not ok:
            self._json({"error": f"TOML 解析失败: {parse_error}"}, 400)
            return
        self._json({"ok": True, "model": model})

    def _api_rights_save(self) -> None:
        body, err = self._read_json_body()
        if err:
            self._json({"error": err}, 400)
            return

        content = body.get("content")
        if not isinstance(content, str):
            self._json({"error": "content 必须为字符串"}, 400)
            return

        ok, parse_error = self._validate_toml(content)
        if not ok:
            self._json({"error": f"TOML 校验失败: {parse_error}"}, 400)
            return

        requested = str(body.get("path", "")).strip()
        path = self._resolve_rights_path(requested_path=requested, create_if_missing=True)
        if not path:
            self._json({"error": "未找到 rights.toml 文件"}, 404)
            return

        try:
            backup = path.with_name(f"{path.name}.{datetime.now().strftime('%Y%m%d_%H%M%S')}.bak")
            if path.exists():
                backup.write_bytes(path.read_bytes())
            path.write_text(content, encoding="utf-8")
            self._json({
                "ok": True,
                "path": str(path.resolve()),
                "backup": str(backup.resolve()) if backup.exists() else None,
            })
        except Exception as e:
            self._json({"error": f"保存 rights 文件失败: {e}"}, 500)

    def _api_rights_template_init(self) -> None:
        body, err = self._read_json_body()
        if err:
            self._json({"error": err}, 400)
            return

        requested = str(body.get("path", "")).strip()
        target_path = self._resolve_rights_path(requested_path=requested, create_if_missing=True)
        if not target_path:
            self._json({"error": "未找到目标 rights.toml 文件"}, 404)
            return

        template_path = self._resolve_template_path()
        if not template_path:
            self._json({"error": "未找到模板文件 rights.toml"}, 404)
            return

        try:
            content = template_path.read_text(encoding="utf-8")
            ok, parse_error = self._validate_toml(content)
            if not ok:
                self._json({"error": f"模板 TOML 非法: {parse_error}"}, 500)
                return

            backup = target_path.with_name(f"{target_path.name}.{datetime.now().strftime('%Y%m%d_%H%M%S')}.bak")
            if target_path.exists():
                backup.write_bytes(target_path.read_bytes())
            target_path.write_text(content, encoding="utf-8")
            self._json({
                "ok": True,
                "path": str(target_path.resolve()),
                "template": str(template_path.resolve()),
                "backup": str(backup.resolve()) if backup.exists() else None,
                "content": content,
            })
        except Exception as e:
            self._json({"error": f"模板初始化失败: {e}"}, 500)

    def _api_rights_reload(self) -> None:
        if not _ts3ab_api_base or not _ts3ab_api_user or not _ts3ab_api_token:
            self._json({"error": "未配置 TS3AudioBot WebAPI，请在 recordings-web.json 设置 ts3ab_api_base / ts3ab_api_user / ts3ab_api_token"}, 503)
            return

        url = f"{_ts3ab_api_base.rstrip('/')}/api/rights/reload"
        basic = base64.b64encode(f"{_ts3ab_api_user}:{_ts3ab_api_token}".encode("utf-8")).decode("ascii")
        req = urllib.request.Request(url, method="GET", headers={"Authorization": f"Basic {basic}"})

        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                payload = resp.read().decode("utf-8", errors="replace")
            self._json({"ok": True, "response": payload})
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", errors="replace")
            self._json({"error": f"reload 失败: HTTP {e.code}", "detail": detail}, e.code)
        except Exception as e:
            self._json({"error": f"调用 TS3AudioBot WebAPI 失败: {e}"}, 502)

    @staticmethod
    def _safe_id(s: str) -> bool:
        return bool(s) and ".." not in s and "/" not in s and "\\" not in s

    def _read_json_body(self) -> Tuple[Dict[str, Any], Optional[str]]:
        try:
            length = int(self.headers.get("Content-Length", 0))
            if length <= 0:
                return {}, "请求体为空"
            raw = self.rfile.read(length)
            data = json.loads(raw.decode("utf-8"))
            if not isinstance(data, dict):
                return {}, "JSON 根节点必须是对象"
            return data, None
        except Exception:
            return {}, "无效的 JSON 请求体"

    def _query_param(self, name: str) -> str:
        parsed = urllib.parse.urlparse(self.path)
        q = urllib.parse.parse_qs(parsed.query, keep_blank_values=True)
        return str(q.get(name, [""])[0]).strip()

    def _normalize_candidate_path(self, raw: str) -> Optional[Path]:
        if not raw:
            return None
        p = Path(raw)
        if not p.is_absolute():
            p = (Path.cwd() / p).resolve()
        else:
            p = p.resolve()
        try:
            p.relative_to(Path.cwd().resolve())
        except Exception:
            return None
        return p

    def _resolve_template_path(self) -> Optional[Path]:
        template = (Path.cwd() / TEMPLATE_RIGHTS_FILE).resolve()
        if template.exists():
            return template
        return None

    def _discover_toml_files(self) -> List[str]:
        roots = [Path.cwd(), Path.cwd() / "TS3AudioBot", Path.cwd() / "bots"]
        files: List[Path] = []
        seen = set()
        for root in roots:
            if not root.exists():
                continue
            for p in root.rglob("*.toml"):
                try:
                    rp = p.resolve()
                except Exception:
                    continue
                key = str(rp).lower()
                if key in seen:
                    continue
                seen.add(key)
                files.append(rp)

        files.sort(key=lambda x: str(x).lower())
        return [str(p) for p in files]

    def _resolve_rights_path(self, requested_path: str = "", create_if_missing: bool = False) -> Optional[Path]:
        candidates: List[Path] = []

        requested = self._normalize_candidate_path(requested_path)
        if requested:
            candidates.append(requested)

        if _rights_path:
            p = Path(_rights_path)
            candidates.append(p if p.is_absolute() else (Path.cwd() / p))

        candidates.append(Path.cwd() / "rights.toml")
        candidates.append(Path.cwd() / "TS3AudioBot" / "rights.toml")

        for p in candidates:
            if p.exists():
                return p

        if create_if_missing and candidates:
            p = candidates[0]
            try:
                p.parent.mkdir(parents=True, exist_ok=True)
            except Exception:
                return None
            return p

        return None

    def _validate_toml(self, content: str) -> Tuple[bool, str]:
        if tomllib is None:
            return False, "当前 Python 环境不支持 tomllib（需要 Python 3.11+）"
        try:
            tomllib.loads(content)
            return True, ""
        except Exception as e:
            return False, str(e)

    def _cors(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def _respond(self, code: int, data: bytes, content_type: str = "text/plain") -> None:
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self._cors()
        self.end_headers()
        self.wfile.write(data)

    def _json(self, obj: Any, code: int = 200) -> None:
        data = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self._respond(code, data, content_type="application/json")


def main() -> None:
    load_config()
    server = http.server.ThreadingHTTPServer(("0.0.0.0", _port), Handler)
    print(f"[recordings] Web 界面启动 -> http://localhost:{_port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[recordings] 已停止")
        server.shutdown()


if __name__ == "__main__":
    main()
