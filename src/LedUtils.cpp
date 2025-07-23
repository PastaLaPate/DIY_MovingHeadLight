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