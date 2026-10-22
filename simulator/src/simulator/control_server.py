import queue
import socket
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

UDP_PORT = 1234
HTTP_PORT = 8080


class ControlServer:
    """UDP + HTTP control server. Only enqueues commands; never touches GL."""

    def __init__(self, udp_port=UDP_PORT, http_port=HTTP_PORT, host="0.0.0.0"):
        self.host = host
        self.udp_port = udp_port
        self.http_port = http_port
        self.queue: queue.Queue = queue.Queue()
        self.last_packet_id = 0
        self.received_any = False

    def start(self):
        threading.Thread(target=self._run_udp, daemon=True).start()
        threading.Thread(target=self._run_http, daemon=True).start()

    # --- UDP ---------------------------------------------------
    def _run_udp(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            sock.bind((self.host, self.udp_port))
        except Exception as e:
            print(f"UDP bind failed on {self.host}:{self.udp_port}: {e}")
            return
        print(f"UDP server listening on udp://{self.host}:{self.udp_port}")

        while True:
            try:
                data, addr = sock.recvfrom(4096)
                text = data.decode("utf-8", errors="ignore").strip()
                if not text:
                    continue
                tokens = text.split(";")
                try:
                    packet_id = int(tokens[0])
                except ValueError:
                    continue
                if packet_id <= self.last_packet_id:
                    continue
                self.last_packet_id = packet_id

                args = {}
                for t in tokens[1:]:
                    if "=" in t:
                        k, v = t.split("=", 1)
                        args[k] = v

                self._parse_args(args)
                self.received_any = True

                try:
                    sock.sendto(f"ACK:{packet_id}".encode(), addr)
                except Exception:
                    pass
            except Exception:
                continue

    def _parse_args(self, args: dict):
        for key, name in (("bS", "base"), ("tS", "top")):
            if key in args:
                try:
                    self.queue.put({"servo": name, "angle": float(args[key])})
                except ValueError:
                    pass

        if all(k in args for k in ("r", "g", "b")):
            try:

                def ch(k):
                    return int(
                        max(0, min(255, float(args[k]) if args[k] != "" else 0.0))
                    )

                cmd = {"led": {"r": ch("r"), "g": ch("g"), "b": ch("b")}}
                if "fl" in args:
                    cmd["flicker"] = int(args["fl"])
                elif "fa" in args:
                    cmd["fade"] = int(args["fa"])
                    from_obj = {}
                    for src, dst in (("fr", "r"), ("fg", "g"), ("fb", "b")):
                        if args.get(src, "") != "":
                            from_obj[dst] = int(float(args[src]))
                    if from_obj:
                        cmd["from"] = from_obj
                self.queue.put(cmd)
            except Exception:
                pass

    # --- HTTP --------------------------------------------------
    def _run_http(self):
        outer = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                if self.path != "/resetIndexCounter":
                    self.send_response(404)
                    self.end_headers()
                    return
                outer.last_packet_id = 0
                self.send_response(200)
                self.send_header("Content-Type", "text/plain")
                self.end_headers()
                self.wfile.write(b"Packet index counter reset.")

            def log_message(self, format, *args):
                return

        try:
            server = HTTPServer((self.host, self.http_port), Handler)
            print(f"HTTP server listening on http://{self.host}:{self.http_port}")
            server.serve_forever()
        except Exception as e:
            print("HTTP server failed:", e)
