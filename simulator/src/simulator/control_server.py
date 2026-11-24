import queue
import socket
import threading

UDP_PORT = 1234

class ControlServer:
    """UDP control server. Only enqueues commands; never touches GL."""

    def __init__(self, udp_port=UDP_PORT, host="0.0.0.0"):
        self.host = host
        self.udp_port = udp_port
        self.queue: queue.Queue = queue.Queue()
        self.received_any = False

    def start(self):
        threading.Thread(target=self._run_udp, daemon=True).start()

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

                args = {}
                for t in tokens[1:]:
                    if "=" in t:
                        k, v = t.split("=", 1)
                        args[k] = v

                self._parse_args(args)
                self.received_any = True
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

