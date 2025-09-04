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


def draw_spot_cone_volumetric(
    base_radius=0.35, length=4.0, slices=36, rings=12, color=(1.0, 1.0, 1.0, 0.25)
):
    """
    Volumetric-ish cone:
    - rings = number of radial rings along the cone length (increase for smoother volume)
    - slices = segments around the circle
    - uses additive blending so the beam looks bright in the air
    - keeps depth test enabled but disables depth writes so it is occluded by opaque geometry
    """
    lr, lg, lb, a0 = color
    glPushAttrib(GL_ENABLE_BIT | GL_COLOR_BUFFER_BIT | GL_CURRENT_BIT)
    glEnable(GL_BLEND)
    # Additive blending tends to look more like light in the air:
    glBlendFunc(GL_SRC_ALPHA, GL_ONE)

    # We want the cone to be occluded by scene geometry, so KEEP depth test enabled,
    # but do not write into the depth buffer while rendering the cone.
    # (This lets opaque geometry occlude the cone.)
    glDepthMask(GL_FALSE)

    glDisable(GL_LIGHTING)  # cone is self-lit
    # Create rings from base (0) to tip (length). radius decreases linearly.
    for r in range(rings):
        z0 = -(r / rings) * length
        z1 = -((r + 1) / rings) * length
        rad0 = base_radius * (1.0 - r / rings)
        rad1 = base_radius * (1.0 - (r + 1) / rings)

        # alpha falloff: stronger near the base, weaker toward the tip
        alpha0 = a0 * (1.0 - (r / rings) * 0.9)  # tweak falloff factor as desired
        alpha1 = a0 * (1.0 - ((r + 1) / rings) * 0.95)

        glBegin(GL_TRIANGLE_STRIP)
        for s in range(slices + 1):
            theta = (s / float(slices)) * 2.0 * math.pi
            x0 = math.cos(theta) * rad0
            y0 = math.sin(theta) * rad0
            x1 = math.cos(theta) * rad1
            y1 = math.sin(theta) * rad1

            # Outer color (base of strip)
            glColor4f(lr, lg, lb, alpha0)
            glVertex3f(x0, y0, z0)

            # Inner color (next ring)
            glColor4f(lr, lg, lb, alpha1)
            glVertex3f(x1, y1, z1)
        glEnd()

    # Optionally draw a faint disk at the base for a stronger origin glow:
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

    # restore
    glDepthMask(GL_TRUE)
    glDisable(GL_BLEND)
    glEnable(GL_LIGHTING)
    glPopAttrib()


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
    glEnable(GL_LIGHT0)  # ambient/world fill light
    glEnable(GL_COLOR_MATERIAL)
    glShadeModel(GL_SMOOTH)
    glEnable(GL_NORMALIZE)  # keep normals normalized after transforms

    # Reduce global ambient so the spotlight is more visible
    glLightfv(GL_LIGHT0, GL_AMBIENT, (0.05, 0.05, 0.05, 1.0))
    glLightfv(GL_LIGHT0, GL_DIFFUSE, (0.25, 0.25, 0.25, 1.0))
    glLightfv(GL_LIGHT0, GL_SPECULAR, (0.05, 0.05, 0.05, 1.0))

    # --- enable a second light that we'll use as the spotlight ---
    glEnable(GL_LIGHT1)

    # Configure static properties for LIGHT1 (others will be updated each frame)
    # Tuned for stronger, longer-reaching beam:
    glLightf(GL_LIGHT1, GL_CONSTANT_ATTENUATION, 0.6)
    glLightf(GL_LIGHT1, GL_LINEAR_ATTENUATION, 0.02)
    glLightf(GL_LIGHT1, GL_QUADRATIC_ATTENUATION, 0.002)
    glLightf(GL_LIGHT1, GL_SPOT_CUTOFF, 35.0)  # wider cone (degrees)
    glLightf(GL_LIGHT1, GL_SPOT_EXPONENT, 10.0)  # less extreme focus

    # Default material properties to show specular highlights
    glMaterialfv(GL_FRONT_AND_BACK, GL_SPECULAR, (1.0, 1.0, 1.0, 1.0))
    glMaterialf(GL_FRONT_AND_BACK, GL_SHININESS, 64.0)

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
                    fr, fg, fb = SIMULATOR_STATE["led_color"]
                    if cmd["from"]:
                        fr, fg, fb = (
                            cmd["from"]["r"] / 255.0,
                            cmd["from"]["g"] / 255.0,
                            cmd["from"]["b"] / 255.0,
                        )
                    SIMULATOR_STATE["fade_start_color"] = (fr, fg, fb)
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
                # Quartic ease-in
                f = (t / duration) ** 4 if duration > 0 else 1.0
                sc = SIMULATOR_STATE["fade_start_color"]
                ec = SIMULATOR_STATE["fade_end_color"]
                SIMULATOR_STATE["led_color"] = tuple(
                    sc[i] + (ec[i] - sc[i]) * f for i in range(3)
                )

        # Clear frame
        glClearColor(0.03, 0.05, 0.08, 1)  # slightly darker background helps visibility
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

        # --- Spotlight placement & head rendering ---
        glPushMatrix()
        # pivot at bottom of head (same pivot used when rotating head)
        glTranslatef(0, 0.2, 0)
        head_rot = SIMULATOR_STATE["head_current"]
        glRotatef(head_rot, 1, 0, 0)

        # Move the light forward from the pivot so it sits at the head "front".
        # Increased forward offset so the light is not buried inside geometry.
        glTranslatef(0, 0.0, 0)  # tweak this to move the lamp forward/back

        # Get current LED color and apply to GL_LIGHT1
        lr, lg, lb = SIMULATOR_STATE["led_color"]

        # Amplify diffuse a bit so the light appears stronger
        diffuse = (min(lr * 4.0, 3.0), min(lg * 4.0, 3.0), min(lb * 4.0, 3.0), 1.0)
        specular = (min(lr * 4.0, 3.0), min(lg * 4.0, 3.0), min(lb * 4.0, 3.0), 1.0)
        ambient = (lr * 0.02, lg * 0.02, lb * 0.02, 1.0)

        glLightfv(GL_LIGHT1, GL_DIFFUSE, diffuse)
        glLightfv(GL_LIGHT1, GL_SPECULAR, specular)
        glLightfv(GL_LIGHT1, GL_AMBIENT, ambient)

        # Position uses current modelview: set as positional light (w=1)
        glLightfv(GL_LIGHT1, GL_POSITION, (0.0, 0.0, 0.0, 1.0))

        # Spotlight direction in the head's local coordinates: pointing toward -Z (forward)
        glLightfv(GL_LIGHT1, GL_SPOT_DIRECTION, (0.0, 0.0, -1.0))

        # Give the head a slight emission so it looks like a lamp head (small glow)
        glMaterialfv(
            GL_FRONT_AND_BACK, GL_EMISSION, (lr * 0.25, lg * 0.25, lb * 0.25, 1.0)
        )

        # Draw the head box (now lit by LIGHT1)
        glColor3f(
            0.9, 0.9, 0.9
        )  # neutral head color; actual appearance comes from lighting
        glPushMatrix()
        draw_box(w=0.5, h=0.4, d=1.2)
        glPopMatrix()

        # Draw visible beam/cone so you can actually see the light
        # Place origin at light position and draw cone extending forward (-Z)
        # We'll draw a cone length tuned to reach the floor: ~3.5 units
        draw_spot_cone_volumetric(
            base_radius=0.35, length=4.0, slices=36, color=(lr, lg, lb, 0.15)
        )

        # reset emission to zero for subsequent geometry
        glMaterialfv(GL_FRONT_AND_BACK, GL_EMISSION, (0.0, 0.0, 0.0, 1.0))

        glPopMatrix()  # end head transform / light placement

        glPopMatrix()

        pygame.display.flip()


if __name__ == "__main__":
    if not hasattr(asyncio, "get_event_loop"):
        print("Requires Python 3.7+")
        sys.exit(1)
    main()
