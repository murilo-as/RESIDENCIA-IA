"""Proxy que repassa ao llama-server e grava usage/finish_reason de cada resposta em JSONL."""
# Descricao: Proxy entre o lm-eval e o llama-server que grava tokens gerados e finish_reason de cada resposta em JSONL.
import http.server, json, sys, threading, time, urllib.request

ALVO, LOG = sys.argv[1], sys.argv[2]
trava = threading.Lock()


class H(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        corpo = self.rfile.read(int(self.headers["Content-Length"]))
        t0 = time.time()
        req = urllib.request.Request(ALVO + self.path, data=corpo, headers={"Content-Type": "application/json"})
        try:
            r = urllib.request.urlopen(req, timeout=3600)
            status, dados = r.status, r.read()
        except urllib.error.HTTPError as e:
            status, dados = e.code, e.read()
        t1 = time.time()
        try:
            j = json.loads(dados)
            reg = {"t0": t0, "t1": t1, "status": status, "completion_tokens": j["usage"]["completion_tokens"],
                   "prompt_tokens": j["usage"]["prompt_tokens"], "finish_reason": j["choices"][0]["finish_reason"]}
        except Exception as e:
            reg = {"t0": t0, "t1": t1, "status": status, "erro": repr(e)}
        with trava, open(LOG, "a") as f:
            f.write(json.dumps(reg) + "\n")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(dados)))
        self.end_headers()
        self.wfile.write(dados)

    def log_message(self, *a):
        pass


http.server.ThreadingHTTPServer(("127.0.0.1", int(sys.argv[3])), H).serve_forever()
