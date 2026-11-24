#define HTTP_PORT 80
#define UDP_PORT 6455

// Debug: log every packet on serial. Each logged packet blocks the async
// task for milliseconds (115200 baud), so keep this OFF for shows.
// #define MH_DEBUG

// SERVOS
#define TOP_SERVO_PIN 12
#define BASE_SERVO_PIN 14

// LED Pins
#define RED_PIN 25
#define GREEN_PIN 26
#define BLUE_PIN 27