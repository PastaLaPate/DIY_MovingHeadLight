// ***** LED PWM Channel Configuration *****
#define RED_CHANNEL 0
#define GREEN_CHANNEL 1
#define BLUE_CHANNEL 2
#define PWM_FREQ 2500
#define PWM_RESOLUTION 8

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
