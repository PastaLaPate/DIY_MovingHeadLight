from compsoft.graphics.materials.material import Material
from compsoft.resources.textures import TextureRegistry
from compsoft.scene.actor import Actor
from compsoft.scene.components.cube import SimpleCubeComponent
from compsoft.scene.components.cylinder import SimpleCylinderComponent
from compsoft.scene.components.light import SpotLight
from pyglm.glm import vec3


class MovingHead(Actor):
    def __init__(self, name: str = "MovingHead"):
        super().__init__(name)
        mh_base = self.add_component(
            SimpleCubeComponent(
                material=Material(TextureRegistry.get_solid_color((30, 30, 30)))
            )
        )
        mh_base.scale = vec3(0.5, 0.2, 0.3)
        mh_base.load()

        mh_pillar_1 = self.add_component(
            SimpleCubeComponent(
                material=Material(TextureRegistry.get_solid_color((30, 30, 30)))
            )
        )
        mh_pillar_1.position = vec3(-0.25 + 0.1 / 2, 0.2 / 2 + 0.4 / 2, 0)
        mh_pillar_1.scale = vec3(0.1, 0.4, 0.3)
        mh_pillar_1.load()

        mh_pillar_2 = self.add_component(
            SimpleCubeComponent(
                material=Material(TextureRegistry.get_solid_color((30, 30, 30)))
            )
        )
        mh_pillar_2.position = vec3(0.25 - 0.1 / 2, 0.2 / 2 + 0.4 / 2, 0)
        mh_pillar_2.scale = vec3(0.1, 0.4, 0.3)
        mh_pillar_2.load()

        self.head = self.add_child(Actor())
        self.head.position = vec3(0, 0.2 / 2 + 0.4 - 0.1, 0)
        self.head.rotation = vec3(90, 0, 0)
        mh_head_cyl = self.head.add_component(
            SimpleCylinderComponent(
                material=Material(TextureRegistry.get_solid_color((90, 90, 90)))
            )
        )
        mh_head_cyl.position = vec3(0, 0.10, 0)
        mh_head_cyl.scale = vec3(0.35, 0.45, 0.35)
        mh_head_cyl.load()
        self.head.add_component(
            SpotLight(direction=vec3(0, 1, 0), position=vec3(0, 0.42, 0), angle=10)
        )

    def set_base_rot(self, rot: float):
        self.rotation = vec3(0, rot, 0)

    def set_head_rot(self, rot: float):
        self.head.rotation = vec3(rot, 0, 0)
