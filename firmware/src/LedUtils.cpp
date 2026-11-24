#include "LedUtils.h"
#include <Arduino.h>

enum EffectKind { FX_NONE, FX_FLICKER, FX_FADE };

// Pins attached in setupLEDPWM(), needed by setColor() on cores where
// ledcWrite() takes a pin instead of a channel (Arduino core >= 3).
static int s_redPin = -1, s_greenPin = -1, s_bluePin = -1;

static struct {
  EffectKind kind = FX_NONE;
  uint32_t startMs = 0;
  uint32_t durationMs = 0;
  int from[3], to[3];
  FadeType fadeType = LINEAR;
} fx;

static float applyEase(float p, FadeType t) {
  switch (t) {
  case EASE_IN_QUAD:
    return p * p;
  case EASE_IN_CUBIC:
    return p * p * p;
  case EASE_IN_QUART:
    return p * p * p * p;
  case LINEAR:
  default:
    return p;
  }
}

void setupLEDPWM(int redPin, int greenPin, int bluePin) {
  s_redPin = redPin;
  s_greenPin = greenPin;
  s_bluePin = bluePin;

#if ESP_ARDUINO_VERSION_MAJOR >= 3
  // Core 3.x: attach with explicit channels so we never collide with the
  // channels ESP32Servo allocates (0-1)
  ledcAttachChannel(redPin, PWM_FREQ, PWM_RESOLUTION, RED_CHANNEL);
  ledcAttachChannel(greenPin, PWM_FREQ, PWM_RESOLUTION, GREEN_CHANNEL);
  ledcAttachChannel(bluePin, PWM_FREQ, PWM_RESOLUTION, BLUE_CHANNEL);
#else
  // Initialize LED PWM channels
  ledcSetup(RED_CHANNEL, PWM_FREQ, PWM_RESOLUTION);
  ledcSetup(GREEN_CHANNEL, PWM_FREQ, PWM_RESOLUTION);
  ledcSetup(BLUE_CHANNEL, PWM_FREQ, PWM_RESOLUTION);

  // Attach the LED pins to the respective channels
  ledcAttachPin(redPin, RED_CHANNEL);
  ledcAttachPin(greenPin, GREEN_CHANNEL);
  ledcAttachPin(bluePin, BLUE_CHANNEL);
#endif

  setColor(255, 0, 0);
  delay(1000); // Let capacitors charge up
  setColor(0, 255, 0);
  delay(1000); // Let capacitors charge up
  setColor(0, 0, 255);
}

void setColor(int redValue, int greenValue, int blueValue) {
#if ESP_ARDUINO_VERSION_MAJOR >= 3
  ledcWrite(s_redPin, max(redValue, 15));
  ledcWrite(s_greenPin, max(greenValue, 15));
  ledcWrite(s_bluePin, max(blueValue, 25));
#else
  ledcWrite(RED_CHANNEL, max(redValue, 15));
  ledcWrite(GREEN_CHANNEL, max(greenValue, 15));
  ledcWrite(BLUE_CHANNEL, max(blueValue, 25));
#endif
}

void flicker(int redValue, int greenValue, int blueValue, int duration) {
  fx.kind = FX_FLICKER;
  fx.startMs = millis();
  fx.durationMs = duration;
  fx.to[0] = redValue;
  fx.to[1] = greenValue;
  fx.to[2] = blueValue;
}

void fadeToColor(int rFrom, int gFrom, int bFrom, int rTarget, int gTarget,
                 int bTarget, int durationMs, FadeType fadeType) {
  fx.kind = FX_FADE;
  fx.startMs = millis();
  fx.durationMs = durationMs;
  fx.from[0] = rFrom;
  fx.from[1] = gFrom;
  fx.from[2] = bFrom;
  fx.to[0] = rTarget;
  fx.to[1] = gTarget;
  fx.to[2] = bTarget;
  fx.fadeType = fadeType;
}

void updateLED() {
  if (fx.kind == FX_NONE)
    return;

  uint32_t elapsed = millis() - fx.startMs;

  if (fx.kind == FX_FLICKER) {
    if (elapsed >= fx.durationMs) {
      setColor(0, 0, 0);
      fx.kind = FX_NONE;
      return;
    }
    bool on = ((elapsed / 25) % 2) == 0; // 25 ms on / 25 ms off
    if (on)
      setColor(fx.to[0], fx.to[1], fx.to[2]);
    else
      setColor(0, 0, 0);
  } else if (fx.kind == FX_FADE) {
    if (elapsed >= fx.durationMs) {
      setColor(fx.to[0], fx.to[1], fx.to[2]);
      fx.kind = FX_NONE;
      return;
    }
    float e = applyEase(float(elapsed) / fx.durationMs, fx.fadeType);
    setColor(fx.from[0] + (fx.to[0] - fx.from[0]) * e,
             fx.from[1] + (fx.to[1] - fx.from[1]) * e,
             fx.from[2] + (fx.to[2] - fx.from[2]) * e);
  }
}

void cancelEffect() { fx.kind = FX_NONE; }