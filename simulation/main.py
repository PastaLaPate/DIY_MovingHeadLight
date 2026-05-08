# adapted_moving_head_sim.py
# Adapted to accept the same WebSocket JSON shapes used by the ESP32 code:
# - WebSocket path: /ws
# - Port: 8080 (Changed from 81 to avoid needing SUDO root privileges)
# - Supports "servo" as an array: { "servo": [ { "servo":"top","angle":45 }, ... ] }
# - Supports LED shapes used by the firmware:
#     { "led": {"r":255,"g":0,"b":0} }
#     { "led": {"r":..., "g":..., "b":...}, "flicker": 500 }
#     { "led": {"r":..., "g":..., "b":...}, "fade": 1000, "from": {"r":..., "g":..., "b":...} }

import sys
import math
import threading
import socket
from http.server import BaseHTTPRequestHandler, HTTPServer
import queue

import pygame
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *

# --- Configuration ----------------------------------------------
WS_HOST = "0.0.0.0"
HTTP_PORT = 81  # Changed from 81 so sudo is no longer required
UDP_PORT = 1234
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
    "fade_active": False,
    "fade_start_color": (1.0, 1.0, 1.0),
    "fade_end_color": (1.0, 1.0, 1.0),
    "fade_start_time": 0,
    "fade_duration": 0,
}

udp_last_packet_id = 0
SMOOTH_SPEED = 360.0  # degrees per second

# --- Geometry Builders ---


def draw_cylinder(radius=0.5, height=1.0, slices=24):
    quad = gluNewQuadric()
    gluCylinder(quad, radius, radius, height, slices, 1)
    glPushMatrix()
    glRotatef(180, 1, 0, 0)
    gluDisk(quad, 0, radius, slices, 1)
    glPopMatrix()
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


def draw_tessellated_plane(size, steps):
    """
    Splits a flat plane into thousands of tiny squares.
    Crucial for OpenGL fixed-function lighting to show the spotlight correctly.
    """
    half = size / 2.0
    step_size = size / steps
    glBegin(GL_QUADS)
    glNormal3f(0.0, 1.0, 0.0)  # Always face up (transformations handle wall rotation)
    for i in range(steps):
        for j in range(steps):
            x0 = -half + i * step_size
            z0 = -half + j * step_size
            x1 = x0 + step_size
            z1 = z0 + step_size

            glVertex3f(x0, 0, z0)
            glVertex3f(x0, 0, z1)
            glVertex3f(x1, 0, z1)
            glVertex3f(x1, 0, z0)
    glEnd()


def draw_room(size=30.0, steps=60):
    """Draws a closed room to capture the light beam."""
    glColor3f(0.15, 0.15, 0.15)  # Dark grey walls

    # Floor
    glPushMatrix()
    glTranslatef(0, -1.0, 0)
    draw_tessellated_plane(size, steps)
    glPopMatrix()

    # Ceiling
    glPushMatrix()
    glTranslatef(0, size - 1.0, 0)
    glRotatef(180, 1, 0, 0)
    draw_tessellated_plane(size, steps)
    glPopMatrix()

    # Back Wall
    glPushMatrix()
    glTranslatef(0, size / 2 - 1.0, -size / 2)
    glRotatef(90, 1, 0, 0)
    draw_tessellated_plane(size, steps)
    glPopMatrix()

    # Front Wall
    glPushMatrix()
    glTranslatef(0, size / 2 - 1.0, size / 2)
    glRotatef(-90, 1, 0, 0)
    draw_tessellated_plane(size, steps)
    glPopMatrix()

    # Left Wall
    glPushMatrix()
    glTranslatef(-size / 2, size / 2 - 1.0, 0)
    glRotatef(-90, 0, 0, 1)
    draw_tessellated_plane(size, steps)
    glPopMatrix()

    # Right Wall
    glPushMatrix()
    glTranslatef(size / 2, size / 2 - 1.0, 0)
    glRotatef(90, 0, 0, 1)
    draw_tessellated_plane(size, steps)
    glPopMatrix()


# --- UDP / HTTP Servers (Protocol strictly maintained) ---


def run_udp_server(host="0.0.0.0", port=UDP_PORT):
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
                continue

            if packet_id <= udp_last_packet_id:
                continue
            udp_last_packet_id = packet_id

            args = {}
            for t in tokens[1:]:
                if "=" in t:
                    k, v = t.split("=", 1)
                    args[k] = v

            if "bS" in args:
                try:
                    command_queue.put({"servo": "base", "angle": float(args["bS"])})
                except Exception:
                    pass
            if "tS" in args:
                try:
                    command_queue.put({"servo": "top", "angle": float(args["tS"])})
                except Exception:
                    pass

            if "r" in args and "g" in args and "b" in args:
                try:
                    r = max(0, min(255, float(args["r"]) if args["r"] != "" else 0.0))
                    g = max(0, min(255, float(args["g"]) if args["g"] != "" else 0.0))
                    b = max(0, min(255, float(args["b"]) if args["b"] != "" else 0.0))
                    cmd = {"led": {"r": int(r), "g": int(g), "b": int(b)}}

                    if "fl" in args:
                        cmd["flicker"] = int(args["fl"])
                    elif "fa" in args:
                        cmd["fade"] = int(args["fa"])
                        fr = (
                            int(float(args.get("fr", "")))
                            if args.get("fr", "") != ""
                            else None
                        )
                        fg = (
                            int(float(args.get("fg", "")))
                            if args.get("fg", "") != ""
                            else None
                        )
                        fb = (
                            int(float(args.get("fb", "")))
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
                except Exception as e:
                    pass

            try:
                sock.sendto(f"ACK:{packet_id}".encode("utf-8"), addr)
            except Exception:
                pass
        except Exception:
            continue


def run_http_server(host="0.0.0.0", port=HTTP_PORT):
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            if self.path != "/resetIndexCounter":
                self.send_response(404)
                self.end_headers()
                return
            global udp_last_packet_id
            udp_last_packet_id = 0
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"Packet index counter reset.")

        def log_message(self, format, *args):
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
    base_radius=0.25, length=15.0, slices=36, rings=16, color=(1.0, 1.0, 1.0, 0.25)
):
    """Draws the translucent beam in the air."""
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

    glDepthMask(GL_TRUE)
    glDisable(GL_BLEND)
    glEnable(GL_LIGHTING)
    glPopAttrib()


room_list = None


def main():
    global room_list
    pygame.init()
    display = (1000, 800)
    pygame.display.set_mode(display, DOUBLEBUF | OPENGL | RESIZABLE)
    pygame.display.set_caption("Moving Head Simulator (Room & Spot Fixed)")

    glMatrixMode(GL_PROJECTION)
    gluPerspective(50, display[0] / display[1], 0.1, 100.0)
    glMatrixMode(GL_MODELVIEW)

    glEnable(GL_DEPTH_TEST)
    glDepthFunc(GL_LEQUAL)
    glEnable(GL_LIGHTING)
    glEnable(GL_COLOR_MATERIAL)
    glShadeModel(GL_SMOOTH)
    glEnable(GL_NORMALIZE)

    # Ambient room light
    glEnable(GL_LIGHT0)
    glLightfv(GL_LIGHT0, GL_AMBIENT, (0.02, 0.02, 0.03, 1.0))
    glLightfv(GL_LIGHT0, GL_DIFFUSE, (0.1, 0.1, 0.1, 1.0))
    glLightfv(GL_LIGHT0, GL_SPECULAR, (0.0, 0.0, 0.0, 1.0))

    # The Spotlight (Light1)
    glEnable(GL_LIGHT1)
    glLightf(GL_LIGHT1, GL_CONSTANT_ATTENUATION, 0.5)
    glLightf(GL_LIGHT1, GL_LINEAR_ATTENUATION, 0.01)
    glLightf(GL_LIGHT1, GL_QUADRATIC_ATTENUATION, 0.001)
    glLightf(GL_LIGHT1, GL_SPOT_CUTOFF, 15.0)  # Narrower beam
    glLightf(GL_LIGHT1, GL_SPOT_EXPONENT, 75.0)  # Sharper gradient

    glMaterialfv(GL_FRONT_AND_BACK, GL_SPECULAR, (0.8, 0.8, 0.8, 1.0))
    glMaterialf(GL_FRONT_AND_BACK, GL_SHININESS, 32.0)

    room_list = glGenLists(1)
    glNewList(room_list, GL_COMPILE)
    draw_room(size=40.0, steps=45)  # 45 is the "sweet spot" for quality vs speed
    glEndList()

    # Camera defaults adjusted to be inside the room
    cam_yaw = -30.0
    cam_pitch = 5.0
    cam_zoom = -12.0
    mouse_down = False
    last_mouse = (0, 0)

    threading.Thread(target=run_udp_server, daemon=True).start()
    threading.Thread(target=run_http_server, daemon=True).start()

    clock = pygame.time.Clock()

    while True:
        dt = clock.tick(400) / 1000.0
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
                gluPerspective(50, display[0] / display[1], 0.1, 100.0)
                glMatrixMode(GL_MODELVIEW)
            if e.type == MOUSEBUTTONDOWN:
                if e.button == 1:
                    mouse_down, last_mouse = True, e.pos
                elif e.button == 4:
                    cam_zoom += 1.0
                elif e.button == 5:
                    cam_zoom -= 1.0
            if e.type == MOUSEBUTTONUP and e.button == 1:
                mouse_down = False
            if e.type == MOUSEMOTION and mouse_down:
                dx, dy = e.pos[0] - last_mouse[0], e.pos[1] - last_mouse[1]
                cam_yaw += dx * 0.2
                cam_pitch += dy * 0.2
                last_mouse = e.pos

        # WS Command Queue Processing
        while not command_queue.empty():
            cmd = command_queue.get_nowait()
            if "servo" in cmd:
                if isinstance(cmd["servo"], list):
                    for item in cmd["servo"]:
                        name, ang = item.get("servo"), item.get("angle")
                        if name == "base":
                            SIMULATOR_STATE["base_target"] = float(ang)
                        elif name == "top":
                            SIMULATOR_STATE["head_target"] = float(ang)
                elif isinstance(cmd["servo"], str) and "angle" in cmd:
                    if cmd["servo"] == "base":
                        SIMULATOR_STATE["base_target"] = float(cmd["angle"])
                    elif cmd["servo"] == "top":
                        SIMULATOR_STATE["head_target"] = float(cmd["angle"])
                else:
                    name, ang = cmd.get("servo"), cmd.get("angle")
                    if name == "base":
                        SIMULATOR_STATE["base_target"] = float(ang)
                    elif name == "top":
                        SIMULATOR_STATE["head_target"] = float(ang)

            if "led" in cmd and isinstance(cmd["led"], dict):
                r, g, b = (
                    cmd["led"].get("r", 0) / 255.0,
                    cmd["led"].get("g", 0) / 255.0,
                    cmd["led"].get("b", 0) / 255.0,
                )
                if "flicker" in cmd:
                    SIMULATOR_STATE["flicker_end_time"] = pygame.time.get_ticks() + int(
                        cmd["flicker"]
                    )
                    SIMULATOR_STATE["flicker_base_color"] = (r, g, b)
                    SIMULATOR_STATE["fade_active"] = False
                elif "fade" in cmd:
                    duration = int(cmd["fade"])
                    now = pygame.time.get_ticks()
                    SIMULATOR_STATE["fade_active"] = True
                    fr, fg, fb = SIMULATOR_STATE["led_color"]
                    if "from" in cmd and isinstance(cmd["from"], dict):
                        fr, fg, fb = (
                            cmd["from"].get("r", fr * 255) / 255.0,
                            cmd["from"].get("g", fg * 255) / 255.0,
                            cmd["from"].get("b", fb * 255) / 255.0,
                        )
                    SIMULATOR_STATE["fade_start_color"] = (fr, fg, fb)
                    SIMULATOR_STATE["fade_end_color"] = (r, g, b)
                    SIMULATOR_STATE["fade_start_time"] = now
                    SIMULATOR_STATE["fade_duration"] = duration
                    SIMULATOR_STATE["flicker_end_time"] = 0
                else:
                    SIMULATOR_STATE["led_color"] = (r, g, b)
                    SIMULATOR_STATE["flicker_end_time"] = 0
                    SIMULATOR_STATE["fade_active"] = False

        # Calculate Frame Color
        now = pygame.time.get_ticks()
        led_color = SIMULATOR_STATE["led_color"]

        if now < SIMULATOR_STATE["flicker_end_time"]:
            led_color = (
                SIMULATOR_STATE["flicker_base_color"]
                if (now // 50) % 2 == 0
                else (0, 0, 0)
            )
        elif SIMULATOR_STATE.get("fade_active", False):
            t = now - SIMULATOR_STATE["fade_start_time"]
            duration = SIMULATOR_STATE["fade_duration"]
            if t >= duration:
                led_color = SIMULATOR_STATE["fade_end_color"]
                SIMULATOR_STATE["fade_active"] = False
            else:
                f = (t / duration) ** 4 if duration > 0 else 1.0
                sc, ec = (
                    SIMULATOR_STATE["fade_start_color"],
                    SIMULATOR_STATE["fade_end_color"],
                )
                led_color = tuple(sc[i] + (ec[i] - sc[i]) * f for i in range(3))

        SIMULATOR_STATE["led_color"] = led_color
        lr, lg, lb = led_color

        # Render Start
        glClearColor(0.01, 0.01, 0.02, 1)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glLoadIdentity()

        # Camera
        glTranslatef(0, -0.5, cam_zoom)
        glRotatef(cam_pitch, 1, 0, 0)
        glRotatef(cam_yaw, 0, 1, 0)

        # Draw the enclosed room (fixes missing light beam issue)
        glCallList(room_list)

        # Draw Moving Head Base
        glPushMatrix()
        base_rot = SIMULATOR_STATE["base_current"] - 90.0
        glRotatef(base_rot, 0, 1, 0)
        glColor3f(0.1, 0.1, 0.1)

        glPushMatrix()
        glRotatef(-90, 1, 0, 0)
        draw_cylinder(radius=0.5, height=1.0)
        glPopMatrix()

        glTranslatef(0, 1.0, 0)
        draw_box(w=0.2, h=0.8, d=0.2)
        glTranslatef(0, 0.4, 0)

        # Draw Moving Head Optic
        glPushMatrix()
        glTranslatef(0, 0.2, 0)

        # FIXED: Reversed projection logic.
        # Negative sign ensures the visual sweeps properly with the beam
        head_rot = SIMULATOR_STATE["head_current"] - 45
        glRotatef(-head_rot, 1, 0, 0)

        # Calculate Lighting power
        diffuse = (min(lr * 6.0, 4.0), min(lg * 6.0, 4.0), min(lb * 6.0, 4.0), 1.0)
        ambient = (lr * 0.05, lg * 0.05, lb * 0.05, 1.0)

        # Apply Spotlight constraints
        glLightfv(GL_LIGHT1, GL_DIFFUSE, diffuse)
        glLightfv(GL_LIGHT1, GL_SPECULAR, diffuse)
        glLightfv(GL_LIGHT1, GL_AMBIENT, ambient)
        glLightfv(GL_LIGHT1, GL_POSITION, (0.0, 0.0, 0.0, 1.0))

        # Fixed Spotlight vector (-Z axis) aligned correctly with head_rot
        glLightfv(GL_LIGHT1, GL_SPOT_DIRECTION, (0.0, 0.0, -1.0))

        # Glowing lense
        glMaterialfv(
            GL_FRONT_AND_BACK, GL_EMISSION, (lr * 0.8, lg * 0.8, lb * 0.8, 1.0)
        )
        glColor3f(0.2, 0.2, 0.2)

        glPushMatrix()
        draw_box(w=0.5, h=0.4, d=1.2)
        glPopMatrix()

        # Volumetric cone through the air
        draw_spot_cone_volumetric(
            base_radius=0.25, length=15.0, slices=36, color=(lr, lg, lb, 0.15)
        )

        # Reset glow for rest of scene
        glMaterialfv(GL_FRONT_AND_BACK, GL_EMISSION, (0.0, 0.0, 0.0, 1.0))

        glPopMatrix()  # End Head
        glPopMatrix()  # End Base

        pygame.display.flip()


if __name__ == "__main__":
    main()
