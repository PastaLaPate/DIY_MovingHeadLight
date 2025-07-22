import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from mpl_toolkits.mplot3d import Axes3D

# Light configuration
BASE_POS = [0, 0, 2]  # Mounted 2m above origin
BEAM_LENGTH = 5        # Beam visualization length

def calculate_beam_endpoint(pan_deg, tilt_deg):
    """Convert pan/tilt angles (degrees) to a 3D beam endpoint."""
    pan_rad = np.radians(pan_deg)
    tilt_rad = np.radians(tilt_deg)
    
    # Calculate direction vector components
    x = np.sin(pan_rad) * np.cos(tilt_rad)
    y = np.sin(tilt_rad)
    z = np.cos(pan_rad) * np.cos(tilt_rad)
    
    # Scale direction to beam length and add base position
    return BASE_POS + BEAM_LENGTH * np.array([x, y, z])

# Set up the figure
fig = plt.figure(figsize=(10, 8))
ax = fig.add_subplot(111, projection='3d')
ax.set_title('Moving Head Beam Light Simulation')
ax.set_xlabel('X (m)')
ax.set_ylabel('Y (m)')
ax.set_zlabel('Z (m)')
ax.set_xlim(-5, 5)
ax.set_ylim(-5, 5)
ax.set_zlim(0, 7)

# Initialize beam plot
light_point, = ax.plot([BASE_POS[0]], [BASE_POS[1]], [BASE_POS[2]], 'ro', markersize=10)
beam_line, = ax.plot([], [], [], 'b-', linewidth=2)

def update_beam(pan, tilt):
    """Update the beam line with new pan/tilt angles."""
    end = calculate_beam_endpoint(pan, tilt)
    beam_line.set_data_3d(
        [BASE_POS[0], end[0]],
        [BASE_POS[1], end[1]],
        [BASE_POS[2], end[2]]
    )
    return beam_line,

# Add this after the static plot setup
def animate(frame):
    """Animate pan/tilt motion over frames."""
    pan = 30 * np.sin(2 * np.pi * frame / 100)  # Pan: sine wave (30° amplitude)
    tilt = 20 * np.sin(2 * np.pi * frame / 50)   # Tilt: faster sine wave (20° amplitude)
    return update_beam(pan, tilt)

ani = FuncAnimation(fig, animate, frames=200, interval=50, blit=True)
plt.show()