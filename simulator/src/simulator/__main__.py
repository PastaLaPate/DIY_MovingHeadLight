# NVIDIA PRIME Offload
import os
import time

from compsoft.core.debug import DebugFlags
from compsoft.core.engine import Engine
from compsoft.graphics.materials.material import Material
from compsoft.resources.textures import TextureRegistry
from compsoft.scene.actor import Actor
from compsoft.scene.components.cube import SimpleCubeComponent
from compsoft.scene.components.light import DirectionalLight
from glm import vec3
from OpenGL import GL
from OpenGL.GL import glGetString

from simulator.control_server import ControlServer
from simulator.fixture_state import FixtureState
from simulator.moving_head_line import MovingHeadLine

os.environ["__NV_PRIME_RENDER_OFFLOAD"] = "1"
os.environ["__GLX_VENDOR_LIBRARY_NAME"] = "nvidia"

# AMD / Mesa PRIME
os.environ["DRI_PRIME"] = "1"


def main():
    print("Welcome...")
    t = time.time_ns()

    engine = Engine()

    vendor = glGetString(GL.GL_VENDOR)
    renderer = glGetString(GL.GL_RENDERER)
    if isinstance(vendor, bytes) and isinstance(renderer, bytes):
        print(f"Vendor:   {vendor.decode('utf-8')}")
        print(f"Renderer: {renderer.decode('utf-8')}")

    scene = engine.scene
    scene.load()
    # scene.debug.add_flag(DebugFlags.DEBUG_RENDER_SHADOW_MAP)
    scene.debug.add_flag(DebugFlags.DEBUG_FRAME_TIME)
    # scene.debug.add_flag(DebugFlags.DEBUG_FRAME_TIME_DETAILLED)
    scene.camera.pos = vec3(0, 7, 0)
    scene.camera.look_at(vec3(5, 10, 5))

    plane_actor = scene.add_actor(Actor())
    plane = plane_actor.add_component(
        SimpleCubeComponent(Material(TextureRegistry.get_solid_color((30, 30, 30))))
    )
    plane_actor.position = vec3(0, -1, 0)
    plane_actor.add_component(DirectionalLight(vec3(0, -1, 0), intensity=1))
    plane.load()
    plane.scale = vec3(100, 1, 100)

    moving_head_line = MovingHeadLine(scene, 5, same_seed=True)
    moving_head_line.set_base_rot_all(90)
    moving_head_line.set_head_rot_all(90)

    server = ControlServer()
    server.start()
    fixture = FixtureState()
    last_t = None

    def tick(t: float, dt: float):
        nonlocal last_t

        # Drain network commands (main thread only)
        while True:
            try:
                fixture.apply(server.queue.get_nowait())
            except Exception:  # queue.Empty
                break

        if server.received_any:
            base, head, (r, g, b) = fixture.update(dt)
            moving_head_line.set_base_rot_all(base)
            moving_head_line.set_head_rot_all(head)
            moving_head_line.set_color_all(vec3(r, g, b))
        else:
            # No remote controller yet: keep the built-in demo animation
            moving_head_line.update(t)

    engine._add_prerender_listener(tick)

    print(f"Started in {round((time.time_ns() - t) / 1e6)}ms")
    engine.start()
    engine.exit()
