#include <WiFi.h>
#include <ESPAsyncWebServer.h>
#include <ArduinoJson.h>
#include <Servo.h>

// ***** WiFi Credentials *****
const char* ssid     = "xxx";
const char* password = "xxx";

// ***** Servo Pins and Objects *****
int baseServoPin = 14;
int topServoPin  = 12;
Servo servo;

// ***** LED Pin Definitions *****
const int redPin   = 26;
const int greenPin = 25;
const int bluePin  = 27;

// ***** LED PWM Channel Configuration *****
const int redChannel    = 0;
const int greenChannel  = 1;
const int blueChannel   = 2;
const int pwmFreq       = 5000;
const int pwmResolution = 8;

// WebSocket server on port 81
AsyncWebServer server(81);
AsyncWebSocket ws("/ws");

// Function to smoothly move a servo (adjust speed as needed)
void moveServo(int pin, int angle) {
  servo.write(pin, angle, 2000, 0);
}

// Set the color of the LED
void setColor(int redValue, int greenValue, int blueValue) {
  ledcWrite(redChannel, redValue);
  ledcWrite(greenChannel, greenValue);
  ledcWrite(blueChannel, blueValue);
}

// Handle incoming WebSocket messages
void handleWebSocketMessage(void *arg, uint8_t *data, size_t len) {
  DynamicJsonDocument doc(256);
  // Parse the JSON payload from the WebSocket message
  DeserializationError error = deserializeJson(doc, data, len);
  if (error) {
    Serial.println("Invalid JSON received");
    return;
  }

  // Handle servo commands
  if (doc.containsKey("servo") && doc.containsKey("angle")) {
    int angle = doc["angle"];
    const char* servoName = doc["servo"];
    if (strcmp(servoName, "top") == 0) {
      Serial.printf("Moving top servo to %d°\n", angle);
      moveServo(topServoPin, angle);
    } else if (strcmp(servoName, "base") == 0) {
      Serial.printf("Moving base servo to %d°\n", angle);
      moveServo(baseServoPin, angle);
    }
  }

  // Handle LED color command
  if (doc.containsKey("led")) {
    int r = doc["led"]["r"];
    int g = doc["led"]["g"];
    int b = doc["led"]["b"];
    Serial.printf("Setting LED color to R:%d, G:%d, B:%d\n", r, g, b);
    setColor(r, g, b);
  }
}

// WebSocket event handler
void onWebSocketEvent(AsyncWebSocket *server, AsyncWebSocketClient *client, AwsEventType type, void *arg, uint8_t *data, size_t len) {
  switch (type) {
    case WS_EVT_CONNECT:
      Serial.printf("WebSocket client #%u connected from %s\n", client->id(), client->remoteIP().toString().c_str());
      break;
    case WS_EVT_DISCONNECT:
      Serial.printf("WebSocket client #%u disconnected\n", client->id());
      break;
    case WS_EVT_DATA:
      handleWebSocketMessage(arg, data, len);
      break;
    case WS_EVT_PONG:
    case WS_EVT_ERROR:
      break;
  }
}

// ***** Setup *****
void setup() {
  Serial.begin(115200);
  delay(1000);

  // Connect to WiFi
  Serial.printf("Connecting to %s\n", ssid);
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println();
  Serial.print("Connected! IP address: ");
  Serial.println(WiFi.localIP());

  // Initialize LED PWM channels
  ledcSetup(redChannel, pwmFreq, pwmResolution);
  ledcSetup(greenChannel, pwmFreq, pwmResolution);
  ledcSetup(blueChannel, pwmFreq, pwmResolution);
  ledcAttachPin(redPin, redChannel);
  ledcAttachPin(greenPin, greenChannel);
  ledcAttachPin(bluePin, blueChannel);

  // Attach servos
  servo.attach(topServoPin, 4);
  servo.attach(baseServoPin, 5);

  // Start WebSocket server
  ws.onEvent(onWebSocketEvent);
  server.addHandler(&ws);
  server.begin();
  Serial.println("WebSocket server started on port 81");
}

// ***** Main Loop *****
void loop() {
  // Clean up disconnected clients
  ws.cleanupClients();
}
