#include <SETTINGS.h>
#include <ServoUtils.h>

void initServo()
{
  // Attach servos
  servo.attach(TOP_SERVO_PIN, 4);
  servo.attach(BASE_SERVO_PIN, 5);
}

void moveServo(int pin, int angle)
{
  servo.write(pin, angle, 2000, 0);
}