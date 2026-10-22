import math
import os
import time

from compsoft.core.debug import DebugFlags
from compsoft.core.engine import Engine
from compsoft.graphics.infrastructure.render_pass import RenderPass
from compsoft.graphics.materials.light_material import LightMaterial
from compsoft.graphics.materials.material import Material
from compsoft.resources.manager import resources
from compsoft.resources.textures import TextureRegistry
from compsoft.scene.actor import Actor
from compsoft.scene.components.cone import SimpleConeComponent
from compsoft.scene.components.cube import SimpleCubeComponent
from compsoft.scene.components.cylinder import SimpleCylinderComponent
from compsoft.scene.components.light import DirectionalLight, SpotLight
from compsoft.scene.components.model_mesh import ModelMeshComponent
from glm import vec3
from OpenGL import GL
from OpenGL.GL.glget import glGetString
from pyglm.glm import normalize

from simulator.moving_head import MovingHead
from simulator.moving_head_line import MovingHeadLine

# NVIDIA PRIME Offload
os.environ["__NV_PRIME_RENDER_OFFLOAD"] = "1"
os.environ["__GLX_VENDOR_LIBRARY_NAME"] = "nvidia"

# AMD / Mesa PRIME
os.environ["DRI_PRIME"] = "1"


class COLORS:
    RED = vec3(1, 0, 0)
    GREEN = vec3(0, 1, 0)
    BLUE = vec3(0, 0, 1)

    WHITE = vec3(1, 1, 1)
    BLACK = vec3(0, 0, 0)


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
    scene.debug.add_flag(DebugFlags.DEBUG_FRAME_TIME_DETAILLED)
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

    def tick(t: float, dt: float):
        moving_head_line.update(t)

    engine._add_prerender_listener(tick)

    print(f"Started in {round((time.time_ns() - t) / 1e6)}ms")

    engine.start()
    engine.exit()


if __name__ == "__main__":
    main()
