# MovingHead DIY

This is a DIY Moving Head project using an ESP32, servos, and RGB LEDs. The project allows you to control the position of the servos and the color of the LEDs via WebSocket.

## Requirements

You will need vscode w/ PlatformIO installed to build and upload the code to your ESP32.

Circuit:
ESP32 Or any compatible board (might need to change pin numbers in the code & PlatformIO project)

- 2 Servos (one for the base and one for the top) Recommended: MG90S

> [!NOTE]
> Make sure to use a power supply that can provide enough current for the servos, as they can draw significant current when moving. A separate power supply for the servos is recommended. W/ Common GND

- 1 RGB LED (common anode) or 3 individual LEDs (red, green, blue)
- 1 Resistor for each LED (220 ohm)
- Breadboard and jumper wires Or PCB

> [!NOTE]
> A custom PCB might be created later in future.

## Usage

1. Create the file `src/SECRETS.h` following the example in `src/SECRETS.h.example` to define your WiFi credentials.
2. Upload the code to your ESP32 using PlatformIO.
3. Do the circuit

   ![CircuitDiagram](https://raw.githubusercontent.com/PastaLaPate/DIY_MovingHeadLight/master/imgs/breadboard_circuit.png)

You can now open a WebSocket connection to `ws://<your-esp32-ip>:<port>/ws` to control the servos and LEDs. Port is defined in `src/SETTINGS.h` (default is 81). 3. Use the WebSocket client to send JSON commands to control the servos and LEDs.
JSON Body for controlling servo:

```json
{
  "servo": "top", // "top" or "base"
  "angle": 90 // angle in degrees
}
```

JSON Body for controlling LED color:

```json
{
  "led": {
    "r": 255, // red value (0-255)
    "g": 0, // green value (0-255)
    "b": 0 // blue value (0-255)
  }
}
```
