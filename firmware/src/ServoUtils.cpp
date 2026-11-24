#include <Arduino.h>

#include <SETTINGS.h>
#include <ServoUtils.h>

static Servo topServo;
static Servo baseServo;

void initServo()
{
  // Servos take the first free LEDC channels (0 and 1 on a plain ESP32).
  // The LED PWM uses channels 3-5, so there is no conflict (see LedUtils.h).
  topServo.setPeriodHertz(50);
  baseServo.setPeriodHertz(50);

  topServo.attach(TOP_SERVO_PIN, 500, 2500);
  if (!topServo.attached())
    Serial.printf("Failed to attach top servo on pin %d\n", TOP_SERVO_PIN);

  baseServo.attach(BASE_SERVO_PIN, 500, 2500);
  if (!baseServo.attached())
    Serial.printf("Failed to attach base servo on pin %d\n", BASE_SERVO_PIN);
}

void moveServo(int pin, int angle)
{
  // The command is applied immediately (no slew/easing); the servo itself
  // is the rate limiter.
  if (pin == TOP_SERVO_PIN)
    topServo.write(angle);
  else if (pin == BASE_SERVO_PIN)
    baseServo.write(angle);
}
