import math
import os
import time

from glm import vec3
from OpenGL import GL
from OpenGL.GL.glget import glGetString
from pyglm.glm import normalize

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


def smooth_noise(t: float, seed: float) -> float:
    """Combines sines at different frequencies for natural, organic motion."""
    return (
        math.sin(t * 0.8 + seed) * 0.5
        + math.sin(t * 1.9 + seed * 1.3) * 0.3
        + math.sin(t * 3.7 + seed * 2.1) * 0.2
    )


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
    plane_actor.add_component(DirectionalLight(vec3(0, -1, 0), intensity=1))
    plane.load()
    plane.position = vec3(0, -1, 0)
    plane.scale = vec3(100, 1, 100)

    moving_head_actor = scene.add_actor(Actor())

    mh_base = moving_head_actor.add_component(
        SimpleCubeComponent(
            material=Material(TextureRegistry.get_solid_color((30, 30, 30)))
        )
    )
    mh_base.scale = vec3(0.5, 0.2, 0.3)
    mh_base.load()

    mh_pillar_1 = moving_head_actor.add_component(
        SimpleCubeComponent(
            material=Material(TextureRegistry.get_solid_color((30, 30, 30)))
        )
    )
    mh_pillar_1.position = vec3(-0.25 + 0.1 / 2, 0.2 / 2 + 0.4 / 2, 0)
    mh_pillar_1.scale = vec3(0.1, 0.4, 0.3)
    mh_pillar_1.load()

    mh_pillar_2 = moving_head_actor.add_component(
        SimpleCubeComponent(
            material=Material(TextureRegistry.get_solid_color((30, 30, 30)))
        )
    )
    mh_pillar_2.position = vec3(0.25 - 0.1 / 2, 0.2 / 2 + 0.4 / 2, 0)
    mh_pillar_2.scale = vec3(0.1, 0.4, 0.3)
    mh_pillar_2.load()

    mh_head = moving_head_actor.add_child(Actor())
    mh_head.position = vec3(0, 0.2 / 2 + 0.4 - 0.1, 0)
    mh_head.rotation = vec3(90, 0, 0)
    mh_head_cyl = mh_head.add_component(
        SimpleCylinderComponent(
            material=Material(TextureRegistry.get_solid_color((90, 90, 90)))
        )
    )
    mh_head_cyl.position = vec3(0, 0.10, 0)
    mh_head_cyl.scale = vec3(0.35, 0.45, 0.35)
    mh_head_cyl.load()
    mh_head.add_component(SpotLight(direction=vec3(0, 1, 0), position=vec3(0, 0.42, 0)))

    def tick(t: float, dt: float):

        mh_head.rotation = vec3(smooth_noise(t / 100, 4.0) * 180, 0, 0)

    engine._add_prerender_listener(tick)

    print(f"Started in {round((time.time_ns() - t) / 1e6)}ms")

    engine.start()
    engine.exit()


if __name__ == "__main__":
    main()
