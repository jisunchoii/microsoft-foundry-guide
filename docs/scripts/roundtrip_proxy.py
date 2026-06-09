"""Codex namespace round-trip proxy (PoC).

Codex(:client) -> 127.0.0.1:4200 (this) -> 127.0.0.1:4000 (LiteLLM) -> Foundry

FORWARD  (Codex -> LiteLLM): type:"namespace" 툴을 type:"function" 툴로 평탄화하고
         네임스페이스를 이름 접미어로 인코딩한다 -> "<sub>__nsq__<ns>".
REVERSE  (LiteLLM -> Codex): 스트리밍 SSE의 function_call 아이템에서 접미어를
         분리해 "namespace" 필드를 되돌려 주입한다(gpt-4.1 네이티브 와이어 형태 재현).

PoC/워크어라운드 — 운영용 아님. 자세한 배경은 docs/03c 문서를 참고.
"""
import json, os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib import request as urlreq

UPSTREAM = os.environ.get("UPSTREAM_BASE", "http://127.0.0.1:4000/v1").rstrip("/")
LITELLM_KEY = os.environ.get("LITELLM_KEY", "sk-local-anything")
SEP = "__nsq__"


def encode_name(sub, ns):
    return f"{sub}{SEP}{ns}"


def decode_name(name):
    if SEP in name:
        sub, ns = name.split(SEP, 1)
        return sub, ns
    return name, None


def rewrite_request(parsed):
    """namespace 툴 -> function 툴(이름 인코딩) + 히스토리 재인코딩 + 빈 콘텐츠 제거."""
    tools = parsed.get("tools")
    if isinstance(tools, list):
        new_tools = []
        for t in tools:
            if isinstance(t, dict) and t.get("type") == "namespace":
                ns = t.get("name")
                for sub in t.get("tools", []):
                    sub = dict(sub)
                    sub["type"] = "function"
                    sub["name"] = encode_name(sub.get("name"), ns)
                    new_tools.append(sub)
            else:
                new_tools.append(t)
        parsed["tools"] = new_tools

    inp = parsed.get("input")
    if isinstance(inp, list):
        for item in inp:
            if not isinstance(item, dict):
                continue
            if item.get("type") == "function_call":
                ns = item.pop("namespace", None)
                if ns and SEP not in item.get("name", ""):
                    item["name"] = encode_name(item.get("name", ""), ns)
            content = item.get("content")
            if isinstance(content, list):
                kept = [c for c in content
                        if not (isinstance(c, dict)
                                and (c.get("text") or "").strip() == ""
                                and c.get("type", "").endswith("text"))]
                if len(kept) != len(content):
                    item["content"] = kept or [
                        {"type": content[0].get("type", "input_text"), "text": " "}]
    return parsed


def _fix_one(item):
    if isinstance(item, dict) and item.get("type") == "function_call":
        sub, ns = decode_name(item.get("name", ""))
        if ns:
            item["name"] = sub
            item["namespace"] = ns
            return True
    return False


def rewrite_sse_line(line):
    """SSE data 라인의 function_call 아이템에 namespace 재주입."""
    if not line.startswith("data:"):
        return line
    payload = line[len("data:"):].strip()
    if not payload or payload == "[DONE]":
        return line
    try:
        obj = json.loads(payload)
    except Exception:
        return line
    changed = _fix_one(obj)
    if isinstance(obj.get("item"), dict) and _fix_one(obj["item"]):
        changed = True
    resp = obj.get("response")
    if isinstance(resp, dict):
        for it in resp.get("output", []) or []:
            if _fix_one(it):
                changed = True
    return "data: " + json.dumps(obj, ensure_ascii=False) if changed else line


class H(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length) if length else b""
        try:
            parsed = json.loads(body) if body else {}
            body = json.dumps(rewrite_request(parsed)).encode("utf-8")
        except Exception:
            pass
        req = urlreq.Request(UPSTREAM + self.path, data=body, method="POST")
        req.add_header("Authorization", "Bearer " + LITELLM_KEY)
        req.add_header("Content-Type", "application/json")
        try:
            resp = urlreq.urlopen(req)
        except Exception as e:
            err = getattr(e, "read", lambda: b"")()
            self.send_response(getattr(e, "code", 502)); self.end_headers()
            self.wfile.write(err); return
        self.send_response(resp.status)
        for k, v in resp.headers.items():
            if k.lower() not in ("content-length", "transfer-encoding", "connection"):
                self.send_header(k, v)
        self.end_headers()
        buf = ""
        while True:
            chunk = resp.read(512)
            if not chunk:
                break
            buf += chunk.decode("utf-8", "replace")
            while "\n" in buf:
                line, buf = buf.split("\n", 1)
                self.wfile.write((rewrite_sse_line(line) + "\n").encode("utf-8"))
                self.wfile.flush()
        if buf:
            self.wfile.write(rewrite_sse_line(buf).encode("utf-8")); self.wfile.flush()

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    port = int(os.environ.get("PROXY_PORT", "4200"))
    print(f"roundtrip proxy on :{port} -> {UPSTREAM}")
    ThreadingHTTPServer(("127.0.0.1", port), H).serve_forever()
