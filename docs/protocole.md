## Packets

Packet:
Packet_ID;args (in format key=value separated by ;)
The packet ID is only echoed back in the UDP ACK (`ACK:<Packet_ID>`).
Packets are NOT filtered by ID: commands describe absolute state, so the last
packet received always wins, no matter its ID. Resending the same packet (or
the whole state periodically) is therefore always safe.

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
