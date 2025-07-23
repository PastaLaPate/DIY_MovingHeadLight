import sys
import math
import json
import threading
import asyncio
import queue

import pygame
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *
import websockets

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


# --- WebSocket Server Logic ---


async def handle_ws(ws):
    print("Client connected")
    try:
        async for msg in ws:
            try:
                command_queue.put(json.loads(msg))
            except json.JSONDecodeError:
                print("Bad JSON:", msg)
    finally:
        print("Client disconnected")


def run_ws_server():
    """
    Spins up its own event loop on the background thread,
    starts the WS server, and runs forever.
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    async def server_main():
        async with websockets.serve(
            handle_ws,
            "localhost",
            8765,
            ping_interval=None,  # ← disable periodic pings
            ping_timeout=None,  # ← disable ping timeouts
        ):
            print("WS server on ws://localhost:8765")
            await asyncio.Future()  # run forever

    loop.run_until_complete(server_main())


# --- Utility & Main Loop ---


def approach(cur, tgt, max_delta):
    d = tgt - cur
    if abs(d) <= max_delta:
        return tgt
    return cur + math.copysign(max_delta, d)


def main():
    pygame.init()
    display = (1000, 800)
    pygame.display.set_mode(display, DOUBLEBUF | OPENGL | RESIZABLE)
    pygame.display.set_caption("Moving Head Simulator")

    # Projection
    glMatrixMode(GL_PROJECTION)
    gluPerspective(45, display[0] / display[1], 0.1, 50.0)
    glMatrixMode(GL_MODELVIEW)
    glEnable(GL_DEPTH_TEST)
    glDepthFunc(GL_LEQUAL)

    glEnable(GL_LIGHTING)
    glEnable(GL_LIGHT0)
    glEnable(GL_COLOR_MATERIAL)

    # Camera state
    cam_yaw = 0.0
    cam_pitch = -20.0
    cam_zoom = -8.0
    mouse_down = False
    last_mouse = (0, 0)

    # Start WebSocket server on background thread
    threading.Thread(target=run_ws_server, daemon=True).start()

    clock = pygame.time.Clock()

    while True:
        dt = clock.tick(60) / 1000.0
        # Smoothly move current→target
        step = SMOOTH_SPEED * dt
        SIMULATOR_STATE["base_current"] = approach(
            SIMULATOR_STATE["base_current"], SIMULATOR_STATE["base_target"], step
        )
        SIMULATOR_STATE["head_current"] = approach(
            SIMULATOR_STATE["head_current"], SIMULATOR_STATE["head_target"], step
        )

        # Event handling
        for e in pygame.event.get():
            if e.type == QUIT or (e.type == KEYDOWN and e.key == K_ESCAPE):
                pygame.quit()
                sys.exit()
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
            if "servo" in cmd and "angle" in cmd:
                ang = float(cmd["angle"])
                if cmd["servo"] == "base":
                    SIMULATOR_STATE["base_target"] = ang
                elif cmd["servo"] == "top":
                    SIMULATOR_STATE["head_target"] = ang
            elif "led" in cmd:
                r, g, b = (cmd["led"][c] / 255.0 for c in ("r", "g", "b"))
                if "flicker" in cmd:
                    SIMULATOR_STATE["flicker_end_time"] = pygame.time.get_ticks() + int(
                        cmd["flicker"]
                    )
                    SIMULATOR_STATE["flicker_base_color"] = (r, g, b)
                    SIMULATOR_STATE["fade_active"] = False  # Cancel fade if flicker
                elif "fade" in cmd:
                    duration = int(cmd["fade"])
                    now = pygame.time.get_ticks()
                    SIMULATOR_STATE["fade_active"] = True
                    SIMULATOR_STATE["fade_start_color"] = SIMULATOR_STATE["led_color"]
                    SIMULATOR_STATE["fade_end_color"] = (r, g, b)
                    SIMULATOR_STATE["fade_start_time"] = now
                    SIMULATOR_STATE["fade_duration"] = duration
                    SIMULATOR_STATE["flicker_end_time"] = 0  # Cancel flicker if fade
                else:
                    SIMULATOR_STATE["led_color"] = (r, g, b)
                    SIMULATOR_STATE["flicker_end_time"] = 0
                    SIMULATOR_STATE["fade_active"] = False

        # Flicker logic
        now = pygame.time.get_ticks()
        if now < SIMULATOR_STATE["flicker_end_time"]:
            if (now // 50) % 2 == 0:
                SIMULATOR_STATE["led_color"] = SIMULATOR_STATE["flicker_base_color"]
            else:
                SIMULATOR_STATE["led_color"] = (0, 0, 0)
        elif SIMULATOR_STATE.get("fade_active", False):
            t = now - SIMULATOR_STATE["fade_start_time"]
            duration = SIMULATOR_STATE["fade_duration"]
            if t >= duration:
                SIMULATOR_STATE["led_color"] = SIMULATOR_STATE["fade_end_color"]
                SIMULATOR_STATE["fade_active"] = False
            else:
                f = t / duration if duration > 0 else 1.0
                sc = SIMULATOR_STATE["fade_start_color"]
                ec = SIMULATOR_STATE["fade_end_color"]
                SIMULATOR_STATE["led_color"] = tuple(
                    sc[i] + (ec[i] - sc[i]) * f for i in range(3)
                )

        # Clear frame
        glClearColor(0.1, 0.15, 0.2, 1)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        # Camera transform
        glLoadIdentity()
        glTranslatef(0, -0.5, cam_zoom)
        glRotatef(cam_pitch, 1, 0, 0)
        glRotatef(cam_yaw, 0, 1, 0)

        # Draw ground
        glColor3f(0.3, 0.3, 0.35)
        glBegin(GL_QUADS)
        glNormal3f(0, 1, 0)
        glVertex3f(-10, -0.5, 10)
        glVertex3f(10, -0.5, 10)
        glVertex3f(10, -0.5, -10)
        glVertex3f(-10, -0.5, -10)
        glEnd()

        # Draw moving head
        glPushMatrix()
        # Base pan
        base_rot = SIMULATOR_STATE["base_current"] - 90.0
        glRotatef(base_rot, 0, 1, 0)
        glColor3f(0.2, 0.2, 0.7)
        glPushMatrix()
        glRotatef(-90, 1, 0, 0)  # stand it up
        draw_cylinder(radius=0.5, height=1.0)
        glPopMatrix()

        # Arm/Yoke
        glTranslatef(0, 1.0, 0)
        glColor3f(0.6, 0.6, 0.6)
        draw_box(w=0.2, h=0.8, d=0.2)

        # Head tilt
        glTranslatef(0, 0.4, 0)
        head_rot = SIMULATOR_STATE["head_current"]
        glColor3fv(SIMULATOR_STATE["led_color"])
        glPushMatrix()
        glTranslatef(0, 0.2, 0)  # pivot at bottom of head
        glRotatef(head_rot, 0, 0, 1)
        draw_box(w=0.8, h=0.4, d=0.5)
        glPopMatrix()

        glPopMatrix()

        pygame.display.flip()


if __name__ == "__main__":
    if not hasattr(asyncio, "get_event_loop"):
        print("Requires Python 3.7+")
        sys.exit(1)
    main()
