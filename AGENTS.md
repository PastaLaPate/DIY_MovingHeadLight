# DIY Moving Head Light - Agent Guide

## Quick Start

```bash
# Build and upload to ESP32
pio run -t upload

# Run simulation (Python/PyGame/OpenGL)
cd simulation && pip install -r pyproject.toml && python main.py
```

## Project Structure

- **`src/`**: Main firmware (ESP32 Arduino) - entrypoint is `MH.cpp`
- **`include/`**: Header files (SETTINGS.h, SECRETS.h, Utils headers)
- **`lib/`**: PlatformIO private libraries (add project-specific libs here)
- **`simulation/`**: Python/PyGame/OpenGL visualizer (run separately)
- **`test/`**: PlatformIO unit tests (empty template)

## Key Configuration Files

| File | Purpose |
|------|---------|
| `include/SETTINGS.h` | Pin definitions, WebSocket port (default 81) |
| `include/SECRETS.h` | WiFi credentials (gitignored) |
| `platformio.ini` | Dependencies: ESPAsyncWebServer, ArduinoJson, ESP32 AnalogWrite, ElegantOTA |
| `simulation/pyproject.toml` | Python 3.11+ deps: pygame, pyopengl |

## Build & Test Commands

```bash
# Full workflow
pio run -t uploadfirmware

# Build only
pio run

# Upload
pio run -t upload

# Serial monitor
pio run -t monitor

# Run simulation (separate process)
cd simulation && python main.py
```

## WebSocket Control Protocol

Connect to `ws://<esp32-ip>:81/ws`

**Servo command:**
```json
{"servo": "top", "angle": 90}
```

**LED command:**
```json
{"led": {"r": 255, "g": 0, "b": 0}}
```

**Multiple servos (simulation supports array):**
```json
{"servo": [{"servo": "base", "angle": 45}, {"servo": "top", "angle": 90}]}
```

**LED with effects:**
```json
{"led": {"r": 128, "g": 128, "b": 128}, "flicker": 500}
{"led": {"r": 255, "g": 0, "b": 0}, "fade": 1000, "from": {"r": 0, "g": 0, "b": 255}}
```

## Hardware Notes

- **Servos**: MG90S on pins 12 (top), 14 (base)
- **LEDs** (Common Anode): Pins 25 (R), 26 (G), 27 (B)
- **Power**: Separate supply recommended for servos (high current draw)
- **Resistors** (Common Anode, 5V): R=150Ω, G=100Ω, B=100Ω

## Simulation Notes

- Uses UDP (port 1234) and HTTP (port 81) for command protocol
- OpenGL rendering with volumetric beam visualization
- Servo movement smooth interpolation at 360°/s
- Camera controls: left-drag to rotate, scroll to zoom

## Common Pitfalls

1. **Pin numbers may differ** - check `SETTINGS.h` for your board
2. **WiFi secrets** - create `include/SECRETS.h` from template
3. **Power supply** - servos can brownout the ESP32
4. **Simulation port** - uses 81 (not 8080) to match firmware
