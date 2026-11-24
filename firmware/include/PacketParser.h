#pragma once

#include "WString.h"
#include <stdint.h>

enum LedAction { LED_SET, LED_FLICKER, LED_FADE };

// Parsed representation of one control packet: "<packetID>;key=value;..."
struct Command {
  uint32_t packetId = 0;

  bool hasBaseServo = false;
  int baseServoAngle = 0;

  bool hasTopServo = false;
  int topServoAngle = 0;

  bool hasRed = false, hasGreen = false, hasBlue = false;
  int red = 0, green = 0, blue = 0;

  LedAction ledAction = LED_SET;
  int flickerMs = 0;
  int fadeMs = 0;
  int fadeFrom[3] = {0, 0, 0};
};

// Pure parsing: fills `cmd` from raw packet text, no side effects.
// Returns false on format error (empty packet or invalid packet ID).
bool parsePacket(const String &data, Command &cmd);

// Applies a parsed command to the hardware (servos + LED).
void applyCommand(const Command &cmd);
