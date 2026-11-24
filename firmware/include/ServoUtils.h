#pragma once

#include <ESP32Servo.h>

void initServo();
void moveServo(int pin, int angle);
