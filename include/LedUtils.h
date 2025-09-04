// ***** LED PWM Channel Configuration *****
#define RED_CHANNEL 0
#define GREEN_CHANNEL 1
#define BLUE_CHANNEL 2
#define PWM_FREQ 2500
#define PWM_RESOLUTION 8

// LED Resistor calculations
#define VIN_VOLTAGE 5

// U=I*R
// R=U/I
// I = 20mA = 0.02A

#define CHANNEL_CONSUMTION 0.02 // In Amperes-

#define RED_MAX_VOLT 2.1   // In volts
#define GREEN_MAX_VOLT 3.1 // In volts
#define BLUE_MAX_VOLT 3.1  // In volts

#define RED_RESISTOR (VIN_VOLTAGE - RED_MAX_VOLT) / CHANNEL_CONSUMTION     // 145=~150
#define GREEN_RESISTOR (VIN_VOLTAGE - GREEN_MAX_VOLT) / CHANNEL_CONSUMTION // 95=~100
#define BLUE_RESISTOR (VIN_VOLTAGE - BLUE_MAX_VOLT) / CHANNEL_CONSUMTION   // 95=~100

enum FadeType
{
  LINEAR,
  EASE_IN_QUAD,
  EASE_IN_CUBIC,
  EASE_IN_QUART,
};

void setupLEDPWM(int redPin, int greenPin, int bluePin);
void setColor(int redValue, int greenValue, int blueValue);

void flicker(int redValue, int greenValue, int blueValue, int duration);
void fadeToColor(int rFrom, int gFrom, int bFrom, int rTarget, int gTarget, int bTarget, int durationMs, FadeType fadeType = LINEAR);
