#include "PacketParser.h"

#include <Arduino.h>

#include <LedUtils.h>
#include <SETTINGS.h>
#include <ServoUtils.h>

/*

Packet Structure:

number (32 bits) : Packet ID
args (in format key=value separated by ;) : Arguments

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

*/

// ---- Parsing (pure, no side effects) ----

static bool isDigits(const String &s) {
  if (s.length() == 0)
    return false;
  for (unsigned int i = 0; i < s.length(); i++) {
    if (s[i] < '0' || s[i] > '9')
      return false;
  }
  return true;
}

bool parsePacket(const String &dataIn, Command &cmd) {
  cmd = Command();

  // Tolerate trailing CR/LF from line-oriented senders
  String data = dataIn;
  while (data.length() > 0 &&
         (data[data.length() - 1] == '\r' || data[data.length() - 1] == '\n'))
    data = data.substring(0, data.length() - 1);

  if (data.length() == 0)
    return false;

  // ---- Extract Packet ID ----
  int idx = data.indexOf(';');
  String idToken = (idx == -1) ? data : data.substring(0, idx);
  if (!isDigits(idToken))
    return false;
  cmd.packetId = idToken.toInt();

  // ---- Extract arguments ----
  String rest = (idx == -1) ? "" : data.substring(idx + 1);
  while (rest.length() > 0) {
    String token;
    int semi = rest.indexOf(';');
    if (semi == -1) {
      token = rest;
      rest = "";
    } else {
      token = rest.substring(0, semi);
      rest = rest.substring(semi + 1);
    }

    int eq = token.indexOf('=');
    if (eq == -1)
      continue; // tolerate stray tokens without '='
    String key = token.substring(0, eq);
    int value = token.substring(eq + 1).toInt();

    if (key == "bS") {
      cmd.hasBaseServo = true;
      cmd.baseServoAngle = value;
    } else if (key == "tS") {
      cmd.hasTopServo = true;
      cmd.topServoAngle = value;
    } else if (key == "r") {
      cmd.hasRed = true;
      cmd.red = value;
    } else if (key == "g") {
      cmd.hasGreen = true;
      cmd.green = value;
    } else if (key == "b") {
      cmd.hasBlue = true;
      cmd.blue = value;
    } else if (key == "fl") {
      cmd.ledAction = LED_FLICKER;
      cmd.flickerMs = value;
    } else if (key == "fa") {
      cmd.ledAction = LED_FADE;
      cmd.fadeMs = value;
    } else if (key == "fr") {
      cmd.fadeFrom[0] = value;
    } else if (key == "fg") {
      cmd.fadeFrom[1] = value;
    } else if (key == "fb") {
      cmd.fadeFrom[2] = value;
    }
  }

  return true;
}

// ---- Actuation ----

void applyCommand(const Command &cmd) {
  if (cmd.hasBaseServo) {
    LOGD("Base Servo Angle = %d\n", cmd.baseServoAngle);
    moveServo(BASE_SERVO_PIN, cmd.baseServoAngle);
  }

  if (cmd.hasTopServo) {
    LOGD("Top Servo Angle = %d\n", cmd.topServoAngle);
    moveServo(TOP_SERVO_PIN, cmd.topServoAngle);
  }

  if (cmd.hasRed && cmd.hasGreen && cmd.hasBlue) {
    switch (cmd.ledAction) {
    case LED_FLICKER:
      LOGD("Flickering LED to RGB(%d, %d, %d) for %d ms\n", cmd.red, cmd.green,
           cmd.blue, cmd.flickerMs);
      flicker(cmd.red, cmd.green, cmd.blue, cmd.flickerMs);
      break;
    case LED_FADE:
      LOGD("Fading LED from RGB(%d, %d, %d) to RGB(%d, %d, %d) over %d ms\n",
           cmd.fadeFrom[0], cmd.fadeFrom[1], cmd.fadeFrom[2], cmd.red,
           cmd.green, cmd.blue, cmd.fadeMs);
      fadeToColor(cmd.fadeFrom[0], cmd.fadeFrom[1], cmd.fadeFrom[2], cmd.red,
                  cmd.green, cmd.blue, cmd.fadeMs, EASE_IN_QUART);
      break;
    default:
      cancelEffect();
      LOGD("Setting LED to RGB(%d, %d, %d)\n", cmd.red, cmd.green, cmd.blue);
      setColor(cmd.red, cmd.green, cmd.blue);
      break;
    }
  }
}
