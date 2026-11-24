## Packets

Packet:
Packet_ID;args (in format key=value separated by ;)
The packet ID is optional metadata: the device does not ACK, does not filter
or reorder by ID. Commands describe absolute state, so the last packet
received always wins. Controllers are expected to stream the full state at a
fixed frame rate (e.g. 60 fps), which makes any lost packet self-healing.

Arguments:
Servos:

- bS : Base Servo Angle
- tS : Top Servo Angle
  Base RGB:
- r : LED Red Value (0-255)
- g : LED Green Value (0-255)
- b : LED Blue Value (0-255)

Flicker:

- fl : Flicker Duration (ms)

Fade:

- fa : Fade Duration (ms)
- fr : From Red Value (0-255)
- fg : From Green Value (0-255)
- fb : From Blue Value (0-255)
