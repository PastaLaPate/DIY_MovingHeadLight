# MovingHead DIY

This is a DIY Moving Head project using an ESP32, servos, and RGB LEDs. The project allows you to control the position of the servos and the color of the LEDs via WebSocket.

## Usage

You will need vscode w/ PlatformIO installed to build and upload the code to your ESP32.

1. Create the file `src/SECRETS.h` following the example in `src/SECRETS.h.example` to define your WiFi credentials.
2. Upload the code to your ESP32 using PlatformIO.
3. Do the circuit

   ![CircuitDiagram](https://raw.githubusercontent.com/PastaLaPate/DIY_MovingHeadLight/master/imgs/breadboard_circuit.png)

You can now open a WebSocket connection to `ws://<your-esp32-ip>:<port>/ws` to control the servos and LEDs. Port is defined in `src/SETTINGS.h` (default is 81). 3. Use the WebSocket client to send JSON commands to control the servos and LEDs.
JSON Body for controlling servo:

```json
{
  "servo": "top" | "base",
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
