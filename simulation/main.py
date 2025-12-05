# adapted_moving_head_sim.py
# Adapted to accept the same WebSocket JSON shapes used by the ESP32 code:
# - WebSocket path: /ws
# - Port: 81 (change PORT below if you cannot bind to 81)
# - Supports "servo" as an array: { "servo": [ { "servo":"top","angle":45 }, ... ] }
# - Supports LED shapes used by the firmware:
#     { "led": {"r":255,"g":0,"b":0} }
#     { "led": {"r":..., "g":..., "b":...}, "flicker": 500 }
#     { "led": {"r":..., "g":..., "b":...}, "fade": 1000, "from": {"r":..., "g":..., "b":...} }
"""

UDP Packet Structure:

number (32 bits) : Packet ID
args (in format key=value separated by ;) : Arguments

Arguments:
Servos:
- bS : Base Servo Angle
- tS : Top Servo Angle
Base RGB:
- r : LED Red Value (0-255)
- g : LED Green Value (0-255)
- b : LED Blue Value (0-255)

Flicker:
- fl : Flicker Duration (ms)

Fade:
- fa : Fade Duration (ms)
- fr : From Red Value (0-255)
- fg : From Green Value (0-255)
- fb : From Blue Value (0-255)

"""

import sys
import math
import threading
import socket
from http.server import BaseHTTPRequestHandler, HTTPServer
import queue

import pygame
from pygame.locals import *
from OpenGL.GL import (
    glPushMatrix,
    glRotatef,
    glPopMatrix,
    glTranslatef,
    glBegin,
    GL_QUADS,
    glEnd,
    glNormal3fv,
    glVertex3fv,
    glPushAttrib,
    glEnable,
    glMatrixMode,
    glBlendFunc,
    glDepthMask,
    glDepthFunc,
    glDisable,
    glColor4f,
    glVertex3f,
    glPopAttrib,
    glShadeModel,
    glLightfv,
    glLightf,
    glViewport,
    glMaterialfv,
    glMaterialf,
    glLoadIdentity,
    glClearColor,
    glClear,
    glColor3f,
    glNormal3f,
    GL_BLEND,
    GL_ENABLE_BIT,
    GL_COLOR_BUFFER_BIT,
    GL_CURRENT_BIT,
    GL_SRC_ALPHA,
    GL_ONE,
    GL_FALSE,
    GL_LIGHTING,
    GL_TRIANGLE_STRIP,
    GL_TRIANGLE_FAN,
    GL_TRUE,
    GL_PROJECTION,
    GL_MODELVIEW,
    GL_LIGHT0,
    GL_LEQUAL,
    GL_DEPTH_TEST,
    GL_COLOR_MATERIAL,
    GL_SMOOTH,
    GL_NORMALIZE,
    GL_LIGHT1,
    GL_AMBIENT,
    GL_DIFFUSE,
    GL_SPECULAR,
    GL_CONSTANT_ATTENUATION,
    GL_LINEAR_ATTENUATION,
    GL_QUADRATIC_ATTENUATION,
    GL_SPOT_CUTOFF,
    GL_SPOT_EXPONENT,
    GL_FRONT_AND_BACK,
    GL_SHININESS,
    GL_DEPTH_BUFFER_BIT,
    GL_POSITION,
    GL_SPOT_DIRECTION,
    GL_EMISSION,
)
from OpenGL.GLU import (
    gluCylinder,
    gluDisk,
    gluNewQuadric,
    gluDeleteQuadric,
    gluPerspective,
)

# --- Configuration ----------------------------------------------
WS_HOST = "0.0.0.0"
WS_PORT = 81  # adjust if binding to 81 requires elevated privileges
WS_PATH = "/ws"
# ---------------------------------------------------------------

# --- Global State & Communication ---
command_queue = queue.Queue()

SIMULATOR_STATE = {
    "base_current": 90.0,
    "base_target": 90.0,
    "head_current": 90.0,
    "head_target": 90.0,
    "led_color": (1.0, 1.0, 1.0),
    "flicker_end_time": 0,
    "flicker_base_color": (1.0, 1.0, 1.0),
    # Fade state
    "fade_active": False,
    "fade_start_color": (1.0, 1.0, 1.0),
    "fade_end_color": (1.0, 1.0, 1.0),
    "fade_start_time": 0,
    "fade_duration": 0,
}

# global packet index tracker used by UDP listener and reset endpoint
udp_last_packet_id = 0

SMOOTH_SPEED = 360.0  # degrees per second


def draw_cylinder(radius=0.5, height=1.0, slices=24):
    quad = gluNewQuadric()
    gluCylinder(quad, radius, radius, height, slices, 1)
    # bottom cap
    glPushMatrix()
    glRotatef(180, 1, 0, 0)
    gluDisk(quad, 0, radius, slices, 1)
    glPopMatrix()
    # top cap
    glPushMatrix()
    glTranslatef(0, 0, height)
    gluDisk(quad, 0, radius, slices, 1)
    glPopMatrix()
    gluDeleteQuadric(quad)


def draw_box(w=1.0, h=0.4, d=0.3):
    hw, hh, hd = w / 2, h / 2, d / 2
    vertices = [
        [-hw, -hh, hd],
        [hw, -hh, hd],
        [hw, hh, hd],
        [-hw, hh, hd],
        [-hw, -hh, -hd],
        [-hw, hh, -hd],
        [hw, hh, -hd],
        [hw, -hh, -hd],
    ]
    faces = [
        (0, 1, 2, 3),
        (4, 5, 6, 7),
        (4, 0, 3, 5),
        (1, 7, 6, 2),
        (3, 2, 6, 5),
        (4, 7, 1, 0),
    ]
    normals = [(0, 0, 1), (0, 0, -1), (-1, 0, 0), (1, 0, 0), (0, 1, 0), (0, -1, 0)]
    glBegin(GL_QUADS)
    for norm, face in zip(normals, faces):
        glNormal3fv(norm)
        for idx in face:
            glVertex3fv(vertices[idx])
    glEnd()


# --- UDP Server Logic ---


def run_udp_server(host="0.0.0.0", port=1234):
    """Simple UDP listener that parses the custom ';' separated packet
    format and pushes normalized command dicts into `command_queue`.
    Packet format: <packetID>;<key>=<value>;<key>=<value>;...
    Keys used: bS (base servo), tS (top servo), r,g,b (led), fl (flicker ms),
    fa (fade ms), fr/fg/fb (from color)
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.bind((host, port))
    except Exception as e:
        print(f"UDP bind failed on {host}:{port}: {e}")
        return

    print(f"UDP server listening on udp://{host}:{port}")
    global udp_last_packet_id
    while True:
        try:
            data, addr = sock.recvfrom(4096)
            text = data.decode("utf-8", errors="ignore").strip()
            if not text:
                continue
            tokens = text.split(";")
            if len(tokens) == 0:
                continue
            try:
                packet_id = int(tokens[0])
            except Exception:
                print("Invalid packet id, ignoring:", tokens[0])
                continue
            if packet_id <= udp_last_packet_id:
                print("Duplicate or old packet. Ignoring.")
                continue
            udp_last_packet_id = packet_id

            args = {}
            for t in tokens[1:]:
                if "=" in t:
                    k, v = t.split("=", 1)
                    args[k] = v

            # Debug
            print("UDP args:", args)

            # Map args into command_queue items similar to WebSocket handler
            if "bS" in args:
                try:
                    ang = float(args["bS"])
                    command_queue.put({"servo": "base", "angle": ang})
                except Exception:
                    pass
            if "tS" in args:
                try:
                    ang = float(args["tS"])
                    command_queue.put({"servo": "top", "angle": ang})
                except Exception:
                    pass

            if "r" in args and "g" in args and "b" in args:
                try:
                    r = int(args["r"]) if args["r"] != "" else 0
                    g = int(args["g"]) if args["g"] != "" else 0
                    b = int(args["b"]) if args["b"] != "" else 0
                    cmd = {"led": {"r": r, "g": g, "b": b}}
                    if "fl" in args:
                        cmd["flicker"] = int(args["fl"])
                    elif "fa" in args:
                        cmd["fade"] = int(args["fa"])
                        # optional from values
                        fr = (
                            int(args.get("fr", ""))
                            if args.get("fr", "") != ""
                            else None
                        )
                        fg = (
                            int(args.get("fg", ""))
                            if args.get("fg", "") != ""
                            else None
                        )
                        fb = (
                            int(args.get("fb", ""))
                            if args.get("fb", "") != ""
                            else None
                        )
                        if fr is not None or fg is not None or fb is not None:
                            from_obj = {}
                            if fr is not None:
                                from_obj["r"] = fr
                            if fg is not None:
                                from_obj["g"] = fg
                            if fb is not None:
                                from_obj["b"] = fb
                            cmd["from"] = from_obj
                    command_queue.put(cmd)
                except Exception:
                    pass

            # Send simple ACK back
            try:
                sock.sendto(f"ACK:{packet_id}".encode("utf-8"), addr)
            except Exception:
                pass

        except Exception as e:
            print("UDP receive error:", e)
            continue


def run_http_server(host="0.0.0.0", port=81):
    """Simple HTTP server exposing POST /resetIndexCounter to reset packet index."""

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            if self.path != "/resetIndexCounter":
                self.send_response(404)
                self.end_headers()
                return
            # reset the global packet counter
            global udp_last_packet_id
            udp_last_packet_id = 0
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"Packet index counter reset.")

        def log_message(self, format, *args):
            # suppress default logging
            return

    try:
        server = HTTPServer((host, port), Handler)
        print(f"HTTP server listening on http://{host}:{port}")
        server.serve_forever()
    except Exception as e:
        print("HTTP server failed:", e)


# --- Utility & Main Loop ---


def approach(cur, tgt, max_delta):
    d = tgt - cur
    if abs(d) <= max_delta:
        return tgt
    return cur + math.copysign(max_delta, d)


def draw_spot_cone_volumetric(
    base_radius=0.35, length=4.0, slices=36, rings=12, color=(1.0, 1.0, 1.0, 0.25)
):
    lr, lg, lb, a0 = color
    glPushAttrib(GL_ENABLE_BIT | GL_COLOR_BUFFER_BIT | GL_CURRENT_BIT)
    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE)
    glDepthMask(GL_FALSE)
    glDisable(GL_LIGHTING)
    for r in range(rings):
        z0 = -(r / rings) * length
        z1 = -((r + 1) / rings) * length
        rad0 = base_radius * (1.0 - r / rings)
        rad1 = base_radius * (1.0 - (r + 1) / rings)
        alpha0 = a0 * (1.0 - (r / rings) * 0.9)
        alpha1 = a0 * (1.0 - ((r + 1) / rings) * 0.95)
        glBegin(GL_TRIANGLE_STRIP)
        for s in range(slices + 1):
            theta = (s / float(slices)) * 2.0 * math.pi
            x0 = math.cos(theta) * rad0
            y0 = math.sin(theta) * rad0
            x1 = math.cos(theta) * rad1
            y1 = math.sin(theta) * rad1
            glColor4f(lr, lg, lb, alpha0)
            glVertex3f(x0, y0, z0)
            glColor4f(lr, lg, lb, alpha1)
            glVertex3f(x1, y1, z1)
        glEnd()
    glBegin(GL_TRIANGLE_FAN)
    glColor4f(lr, lg, lb, a0 * 0.6)
    glVertex3f(0.0, 0.0, 0.0)
    for s in range(slices + 1):
        theta = (s / float(slices)) * 2.0 * math.pi
        x = math.cos(theta) * base_radius
        y = math.sin(theta) * base_radius
        glColor4f(lr, lg, lb, a0 * 0.35)
        glVertex3f(x, y, 0.0)
    glEnd()
    glDepthMask(GL_TRUE)
    glDisable(GL_BLEND)
    glEnable(GL_LIGHTING)
    glPopAttrib()


def main():
    pygame.init()
    display = (1000, 800)
    pygame.display.set_mode(display, DOUBLEBUF | OPENGL | RESIZABLE)
    pygame.display.set_caption("Moving Head Simulator (WS adapted)")

    # Projection
    glMatrixMode(GL_PROJECTION)
    gluPerspective(45, display[0] / display[1], 0.1, 50.0)
    glMatrixMode(GL_MODELVIEW)
    glEnable(GL_DEPTH_TEST)
    glDepthFunc(GL_LEQUAL)

    glEnable(GL_LIGHTING)
    glEnable(GL_LIGHT0)  # ambient/world fill light
    glEnable(GL_COLOR_MATERIAL)
    glShadeModel(GL_SMOOTH)
    glEnable(GL_NORMALIZE)

    glLightfv(GL_LIGHT0, GL_AMBIENT, (0.05, 0.05, 0.05, 1.0))
    glLightfv(GL_LIGHT0, GL_DIFFUSE, (0.25, 0.25, 0.25, 1.0))
    glLightfv(GL_LIGHT0, GL_SPECULAR, (0.05, 0.05, 0.05, 1.0))

    glEnable(GL_LIGHT1)
    glLightf(GL_LIGHT1, GL_CONSTANT_ATTENUATION, 0.6)
    glLightf(GL_LIGHT1, GL_LINEAR_ATTENUATION, 0.02)
    glLightf(GL_LIGHT1, GL_QUADRATIC_ATTENUATION, 0.002)
    glLightf(GL_LIGHT1, GL_SPOT_CUTOFF, 35.0)
    glLightf(GL_LIGHT1, GL_SPOT_EXPONENT, 10.0)

    glMaterialfv(GL_FRONT_AND_BACK, GL_SPECULAR, (1.0, 1.0, 1.0, 1.0))
    glMaterialf(GL_FRONT_AND_BACK, GL_SHININESS, 64.0)

    cam_yaw = 0.0
    cam_pitch = -20.0
    cam_zoom = -8.0
    mouse_down = False
    last_mouse = (0, 0)

    # Start UDP server on background thread
    threading.Thread(target=run_udp_server, daemon=True).start()
    # Start HTTP server to expose reset endpoint
    threading.Thread(target=run_http_server, daemon=True).start()

    clock = pygame.time.Clock()

    while True:
        dt = clock.tick(60) / 1000.0
        step = SMOOTH_SPEED * dt
        SIMULATOR_STATE["base_current"] = approach(
            SIMULATOR_STATE["base_current"], SIMULATOR_STATE["base_target"], step
        )
        SIMULATOR_STATE["head_current"] = approach(
            SIMULATOR_STATE["head_current"], SIMULATOR_STATE["head_target"], step
        )

        for e in pygame.event.get():
            if e.type == QUIT or (e.type == KEYDOWN and e.key == K_ESCAPE):
                pygame.quit()
                sys.exit(1)
            if e.type == VIDEORESIZE:
                display = e.size
                pygame.display.set_mode(display, DOUBLEBUF | OPENGL | RESIZABLE)
                glViewport(0, 0, display[0], display[1])
                glMatrixMode(GL_PROJECTION)
                glLoadIdentity()
                gluPerspective(45, display[0] / display[1], 0.1, 50.0)
                glMatrixMode(GL_MODELVIEW)
            if e.type == MOUSEBUTTONDOWN:
                if e.button == 1:
                    mouse_down = True
                    last_mouse = e.pos
                elif e.button == 4:
                    cam_zoom += 0.5
                elif e.button == 5:
                    cam_zoom -= 0.5
            if e.type == MOUSEBUTTONUP and e.button == 1:
                mouse_down = False
            if e.type == MOUSEMOTION and mouse_down:
                dx, dy = e.pos[0] - last_mouse[0], e.pos[1] - last_mouse[1]
                cam_yaw += dx * 0.2
                cam_pitch += dy * 0.2
                last_mouse = e.pos

        # Process all pending WS commands
        while not command_queue.empty():
            cmd = command_queue.get_nowait()
            # servo handling: support both normalized array items and single-object style
            if "servo" in cmd:
                # servo could be object-name with angle, or the top-level "servo" array was already expanded
                if isinstance(cmd["servo"], list):
                    # defensive: iterate elements if user somehow sent nested array
                    for item in cmd["servo"]:
                        name = item.get("servo")
                        ang = item.get("angle")
                        if name and ang is not None:
                            if name == "base":
                                SIMULATOR_STATE["base_target"] = float(ang)
                            elif name == "top":
                                SIMULATOR_STATE["head_target"] = float(ang)
                elif isinstance(cmd["servo"], str) and "angle" in cmd:
                    name = cmd["servo"]
                    ang = float(cmd["angle"])
                    if name == "base":
                        SIMULATOR_STATE["base_target"] = ang
                    elif name == "top":
                        SIMULATOR_STATE["head_target"] = ang
                else:
                    # maybe we received a single normalized servo command dict (e.g. {'servo':'base','angle':...})
                    name = cmd.get("servo")
                    ang = cmd.get("angle")
                    if isinstance(name, str) and ang is not None:
                        if name == "base":
                            SIMULATOR_STATE["base_target"] = float(ang)
                        elif name == "top":
                            SIMULATOR_STATE["head_target"] = float(ang)

            # led handling matches firmware shape: led object + optional top-level flicker/fade/from
            if "led" in cmd and isinstance(cmd["led"], dict):
                try:
                    r = cmd["led"].get("r", 0) / 255.0
                    g = cmd["led"].get("g", 0) / 255.0
                    b = cmd["led"].get("b", 0) / 255.0
                except Exception:
                    # fallback if someone sent floats already
                    r, g, b = (
                        float(cmd["led"].get("r", 0)),
                        float(cmd["led"].get("g", 0)),
                        float(cmd["led"].get("b", 0)),
                    )
                # flicker or fade are top-level keys (as in the ESP32 handler)
                if "flicker" in cmd and isinstance(cmd["flicker"], (int, float)):
                    SIMULATOR_STATE["flicker_end_time"] = pygame.time.get_ticks() + int(
                        cmd["flicker"]
                    )
                    SIMULATOR_STATE["flicker_base_color"] = (r, g, b)
                    SIMULATOR_STATE["fade_active"] = False
                elif "fade" in cmd and isinstance(cmd["fade"], (int, float)):
                    duration = int(cmd["fade"])
                    now = pygame.time.get_ticks()
                    SIMULATOR_STATE["fade_active"] = True
                    fr, fg, fb = SIMULATOR_STATE["led_color"]
                    if "from" in cmd and isinstance(cmd["from"], dict):
                        fr = cmd["from"].get("r", fr * 255) / 255.0
                        fg = cmd["from"].get("g", fg * 255) / 255.0
                        fb = cmd["from"].get("b", fb * 255) / 255.0
                    SIMULATOR_STATE["fade_start_color"] = (fr, fg, fb)
                    SIMULATOR_STATE["fade_end_color"] = (r, g, b)
                    SIMULATOR_STATE["fade_start_time"] = now
                    SIMULATOR_STATE["fade_duration"] = duration
                    SIMULATOR_STATE["flicker_end_time"] = 0
                else:
                    SIMULATOR_STATE["led_color"] = (r, g, b)
                    SIMULATOR_STATE["flicker_end_time"] = 0
                    SIMULATOR_STATE["fade_active"] = False

        # Flicker logic
        # Compute effective LED color for this frame
        now = pygame.time.get_ticks()
        led_color = SIMULATOR_STATE["led_color"]

        if now < SIMULATOR_STATE["flicker_end_time"]:
            if (now // 50) % 2 == 0:
                led_color = SIMULATOR_STATE["flicker_base_color"]
            else:
                led_color = (0, 0, 0)
        elif SIMULATOR_STATE.get("fade_active", False):
            t = now - SIMULATOR_STATE["fade_start_time"]
            duration = SIMULATOR_STATE["fade_duration"]
            if t >= duration:
                led_color = SIMULATOR_STATE["fade_end_color"]
                SIMULATOR_STATE["fade_active"] = False
            else:
                f = (t / duration) ** 4 if duration > 0 else 1.0
                sc = SIMULATOR_STATE["fade_start_color"]
                ec = SIMULATOR_STATE["fade_end_color"]
                led_color = tuple(sc[i] + (ec[i] - sc[i]) * f for i in range(3))
        SIMULATOR_STATE["led_color"] = led_color

        # Use led_color for all OpenGL lighting
        lr, lg, lb = led_color

        # Clear frame
        glClearColor(0.03, 0.05, 0.08, 1)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        # Camera transform
        glLoadIdentity()
        glTranslatef(0, -0.5, cam_zoom)
        glRotatef(cam_pitch, 1, 0, 0)
        glRotatef(cam_yaw, 0, 1, 0)

        # Draw ground
        glColor3f(0.22, 0.22, 0.25)
        glBegin(GL_QUADS)
        glNormal3f(0, 1, 0)
        glVertex3f(-10, -0.5, 10)
        glVertex3f(10, -0.5, 10)
        glVertex3f(10, -0.5, -10)
        glVertex3f(-10, -0.5, -10)
        glEnd()

        # Draw moving head
        glPushMatrix()
        base_rot = SIMULATOR_STATE["base_current"] - 90.0
        glRotatef(base_rot, 0, 1, 0)
        glColor3f(0.2, 0.2, 0.7)
        glPushMatrix()
        glRotatef(-90, 1, 0, 0)
        draw_cylinder(radius=0.5, height=1.0)
        glPopMatrix()

        glTranslatef(0, 1.0, 0)
        glColor3f(0.6, 0.6, 0.6)
        draw_box(w=0.2, h=0.8, d=0.2)
        glTranslatef(0, 0.4, 0)

        glPushMatrix()
        glTranslatef(0, 0.2, 0)
        head_rot = SIMULATOR_STATE["head_current"]
        glRotatef(head_rot, 1, 0, 0)

        glTranslatef(0, 0.0, 0)

        lr, lg, lb = SIMULATOR_STATE["led_color"]
        diffuse = (min(lr * 4.0, 3.0), min(lg * 4.0, 3.0), min(lb * 4.0, 3.0), 1.0)
        specular = diffuse
        ambient = (lr * 0.02, lg * 0.02, lb * 0.02, 1.0)

        glLightfv(GL_LIGHT1, GL_DIFFUSE, diffuse)
        glLightfv(GL_LIGHT1, GL_SPECULAR, specular)
        glLightfv(GL_LIGHT1, GL_AMBIENT, ambient)
        glLightfv(GL_LIGHT1, GL_POSITION, (0.0, 0.0, 0.0, 1.0))
        glLightfv(GL_LIGHT1, GL_SPOT_DIRECTION, (0.0, 0.0, -1.0))

        glMaterialfv(
            GL_FRONT_AND_BACK, GL_EMISSION, (lr * 0.25, lg * 0.25, lb * 0.25, 1.0)
        )

        glColor3f(0.9, 0.9, 0.9)
        glPushMatrix()
        draw_box(w=0.5, h=0.4, d=1.2)
        glPopMatrix()

        draw_spot_cone_volumetric(
            base_radius=0.35, length=4.0, slices=36, color=(lr, lg, lb, 0.15)
        )

        glMaterialfv(GL_FRONT_AND_BACK, GL_EMISSION, (0.0, 0.0, 0.0, 1.0))

        glPopMatrix()
        glPopMatrix()

        pygame.display.flip()


if __name__ == "__main__":
    main()
