import http.server
import urllib.request
import urllib.error
import os
import sys

PORT = 8081
DOCS_DIR = os.path.join(os.path.dirname(__file__), "docs")

class ProxyHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DOCS_DIR, **kwargs)

    def log_message(self, format, *args):
        # Clean logging
        sys.stderr.write("%s - - [%s] %s\n" % (self.address_string(), self.log_date_time_string(), format % args))

    def do_OPTIONS(self):
        try:
            self.send_response(200)
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', '*')
            self.end_headers()
        except Exception:
            pass

    def handle_proxy(self, method):
        target_path = self.path[len("/api/nvidia/"):]
        target_url = f"https://integrate.api.nvidia.com/{target_path}"
        
        post_data = None
        if method == 'POST':
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
        
        req_headers = {}
        for h in ['Authorization', 'Content-Type']:
            if h in self.headers:
                req_headers[h] = self.headers[h]
        
        req = urllib.request.Request(target_url, data=post_data, headers=req_headers, method=method)
        try:
            with urllib.request.urlopen(req) as resp:
                resp_data = resp.read()
                self.send_response(resp.status)
                self.send_header('Content-Type', resp.headers.get('Content-Type', 'application/json'))
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(resp_data)
        except urllib.error.HTTPError as e:
            try:
                err_data = e.read()
                self.send_response(e.code)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(err_data)
            except Exception:
                pass
        except Exception as e:
            try:
                self.send_response(500)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(f'{{"error": "{str(e)}"}}'.encode('utf-8'))
            except Exception:
                pass

    def do_GET(self):
        if self.path.startswith("/api/nvidia/"):
            self.handle_proxy('GET')
        else:
            try:
                super().do_GET()
            except Exception:
                pass

    def do_POST(self):
        if self.path.startswith("/api/nvidia/"):
            self.handle_proxy('POST')
        else:
            try:
                super().do_POST()
            except Exception:
                pass

def app(environ, start_response):
    status = '200 OK'
    response_headers = [('Content-type', 'text/plain; charset=utf-8')]
    start_response(status, response_headers)
    return [b"PotholePulse Server"]

handler = app

if __name__ == "__main__":
    http.server.ThreadingHTTPServer.allow_reuse_address = True
    with http.server.ThreadingHTTPServer(("", PORT), ProxyHTTPRequestHandler) as httpd:
        print(f"Serving at http://localhost:{PORT} with NVIDIA API Proxy (Threading)")
        sys.stdout.flush()
        httpd.serve_forever()
