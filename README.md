# MovingHead DIY

[![License](https://img.shields.io/badge/License-CC_BY--NC_4.0-green?link=https%3A%2F%2Fcreativecommons.org%2Flicenses%2Fby-nc-sa%2F4.0%2F%20)](https://creativecommons.org/licenses/by-nc-sa/4.0/)
![GitHub Issues or Pull Requests](https://img.shields.io/github/issues/PastaLaPate/DIY_MovingHeadLight)
![GitHub Issues or Pull Requests](https://img.shields.io/github/issues-pr/PastaLaPate/DIY_MovingHeadLight)
![GitHub top language](https://img.shields.io/github/languages/top/PastaLaPate/DIY_MovingHeadLight)

This is a DIY Moving Head project using an ESP32, servos, and RGB LEDs. The project allows you to control the position of the servos and the color of the LEDs via WebSocket.

## Requirements

You will need vscode w/ PlatformIO installed to build and upload the code to your ESP32.

A 3D Printer is recommended to print the parts, but you can also print the parts online.
You can find the 3D models on [Printables](https://www.printables.com/model/1362122-diy-moving-head-led-beam-light) or see last version (might be unstable / broken) on [AutoDesk Fusion HUB](https://a360.co/457yoQi).

Circuit:
ESP32 Or any compatible board (might need to change pin numbers in the code & PlatformIO project)

- 2 Servos (one for the base and one for the top) Recommended: MG90S

> [!NOTE]
> Make sure to use a power supply that can provide enough current for the servos, as they can draw significant current when moving. A separate power supply for the servos is recommended. W/ Common GND

- 1 RGB LED (common anode or common cathode) or 3 individual LEDs (red, green, blue)
- If rgb common anode:
  - 3 IRLZ44N MOSFETs (or similar) for each color channel
- Else:
  - Just skip the MOSFETs in the circuit.
- 1 220 Ohm Resistor for each LED data line
- Between Mosfet drain & LED cathode/anode See `src/SETTINGS.h` for calculating the resistor values, assuming default values + 5V power supply:
  - Red: 150 Ohm
  - Green: 100 Ohm
  - Blue: 100 Ohm
- Breadboard and jumper wires Or PCB

> [!NOTE]
> Here is a pcb made in Easy eda which support up to a 1W RGB Led
> Project : https://oshwlab.com/pastalapate/movinghead_led
> Editor : https://pro.easyeda.com/editor#id=c217a71503914a7fb4df2c4265607413

## Usage

1. Create the file `src/SECRETS.h` following the example in `src/SECRETS.h.example` to define your WiFi credentials.
2. Upload the code to your ESP32 using PlatformIO.
3. Do the circuit

   ![CircuitDiagram](https://raw.githubusercontent.com/PastaLaPate/DIY_MovingHeadLight/master/imgs/breadboard_circuit.png)

4. Print the 3D models and assemble the moving head.

You can use ![Light Show Controller](https://github.com/PastaLaPate/Lightshow) to create light shows and control the moving head depending of the current music.

## Custom control

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
