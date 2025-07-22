#define PORT 81

// SERVOS
#define TOP_SERVO_PIN 12
#define BASE_SERVO_PIN 14

// LED Pins
#define RED_PIN   25
#define GREEN_PIN 26
#define BLUE_PIN  27

// LED Resistor calculations
#define VIN_VOLTAGE 5

// V=I*R
// R=U/I
// I = 20mA = 0.02A

#define CHANNEL_CONSUMTION 0.02 // In Amperes-

#define RED_MAX_VOLT   2.1 // In volts
#define GREEN_MAX_VOLT 3.1 // In volts
#define BLUE_MAX_VOLT  3.1 // In volts

#define RED_RESISTOR (VIN_VOLTAGE - RED_MAX_VOLT) / 0.02 // 145=~150
#define GREEN_RESISTOR (VIN_VOLTAGE - GREEN_MAX_VOLT) / 0.02 // 95=~100
#define BLUE_RESISTOR (VIN_VOLTAGE - BLUE_MAX_VOLT) / 0.02 // 95=~100