from compsoft.scene.components.light import SpotLight
from compsoft.scene.gizmos.axes import Axis
from compsoft.scene.scene import Scene  # adjust, only used for type hints
from numpy.random import uniform
from pyglm.glm import vec3

from simulator.moving_head import MovingHead
from simulator.noise import smooth_noise

_AXIS_VECTORS = {
    Axis.X: vec3(1, 0, 0),
    Axis.Y: vec3(0, 1, 0),
    Axis.Z: vec3(0, 0, 1),
}


class MovingHeadLine:
    def __init__(
        self,
        scene: Scene,
        count: int,
        axis: Axis = Axis.X,
        spacing: float = 1.0,
        mirror: bool = False,
        origin: vec3 | None = None,
        same_seed: bool = False,
        speed: float = 0.01,
        amplitude: float = 360.0,
    ):
        self.axis = axis
        self.speed = speed
        self.amplitude = amplitude
        self.origin = origin or vec3(0, 0, 0)
        self.heads: list[MovingHead] = []
        self._seeds: list[tuple[float, float]] = []

        direction = _AXIS_VECTORS[axis]

        base_seed = (uniform(0, 10_000), uniform(0, 10_000))

        for i in range(count):
            # mirror: centered on origin, extends in both directions along the axis
            # otherwise: starts at origin and extends in the positive direction
            offset = (i - (count - 1) / 2) if mirror else i

            head = scene.add_actor(MovingHead(name=f"MovingHead_{i}"))
            head.position = self.origin + direction * (offset * spacing)
            self.heads.append(head)

            # independent noise seeds per fixture (base pan, head tilt)
            self._seeds.append(
                (uniform(0, 10_000), uniform(0, 10_000)) if not same_seed else base_seed
            )

    def update(self, t: float) -> None:
        ts = t * self.speed
        for head, (base_seed, head_seed) in zip(self.heads, self._seeds):
            head.set_base_rot(smooth_noise(ts, base_seed) * self.amplitude)
            head.set_head_rot(smooth_noise(ts, head_seed) * self.amplitude)
        self.set_color_all(
            vec3(
                smooth_noise(ts, 1) * 0.5 + 1,
                smooth_noise(ts, 2) * 0.5 + 1,
                smooth_noise(ts, 3) * 0.5 + 1,
            )
        )

    def set_base_rot_all(self, rot: float) -> None:
        for head in self.heads:
            head.set_base_rot(rot)

    def set_head_rot_all(self, rot: float) -> None:
        for head in self.heads:
            head.set_head_rot(rot)

    def set_color_all(self, color: vec3) -> None:
        for head in self.heads:
            light = head.head.get_component_by_type(SpotLight)
            if light:
                light.color = color
