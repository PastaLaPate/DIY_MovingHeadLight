#include "LedUtils.h"
#include <Arduino.h>

void setupLEDPWM(int redPin, int greenPin, int bluePin)
{
  // Initialize LED PWM channels
  ledcSetup(RED_CHANNEL, PWM_FREQ, PWM_RESOLUTION);
  ledcSetup(GREEN_CHANNEL, PWM_FREQ, PWM_RESOLUTION);
  ledcSetup(BLUE_CHANNEL, PWM_FREQ, PWM_RESOLUTION);

  // Attach the LED pins to the respective channels
  ledcAttachPin(redPin, RED_CHANNEL);
  ledcAttachPin(greenPin, GREEN_CHANNEL);
  ledcAttachPin(bluePin, BLUE_CHANNEL);
}

void setColor(int redValue, int greenValue, int blueValue)
{
  ledcWrite(RED_CHANNEL, redValue);
  ledcWrite(GREEN_CHANNEL, greenValue);
  ledcWrite(BLUE_CHANNEL, blueValue);
}

void flicker(int redValue, int greenValue, int blueValue, int duration)
{
  for (int i = 0; i < duration; i += 100)
  {
    setColor(redValue, greenValue, blueValue);
    delay(25);
    setColor(0, 0, 0); // Turn off
    delay(25);
  }
}

void fadeToColor(int rFrom, int gFrom, int bFrom, int rTarget, int gTarget, int bTarget, int durationMs, FadeType fadeType)
{
  int steps = 15; // Number of steps in the fade
  int delayMs = durationMs / steps;

  float rStep = (rTarget - rFrom) / float(steps);
  float gStep = (gTarget - gFrom) / float(steps);
  float bStep = (bTarget - bFrom) / float(steps);

  for (int i = 1; i <= steps; ++i)
  {
    float progress = float(i) / steps;
    float ease;
    switch (fadeType) {
      case LINEAR:        ease = progress; break;
      case EASE_IN_QUAD:  ease = progress * progress; break;
      case EASE_IN_CUBIC: ease = progress * progress * progress; break;
      case EASE_IN_QUART: ease = progress * progress * progress * progress; break;
    }
    int r = rFrom + (rTarget - rFrom) * ease;
    int g = gFrom + (gTarget - gFrom) * ease;
    int b = bFrom + (bTarget - bFrom) * ease;
    setColor(r, g, b);
    delay(delayMs);
  }
  setColor(rTarget, gTarget, bTarget); // Ensure final color is exact
}
