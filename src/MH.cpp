#include <Arduino.h>

#include <SECRETS.h>
#include <SETTINGS.h>

#include <WiFi.h>
#include <ESPAsyncWebServer.h>
#include <ArduinoJson.h>
#include <Servo.h>

#include "LedUtils.h"

// ***** Servo *****
Servo servo;

// WebSocket server on port 81
AsyncWebServer server(PORT);
AsyncWebSocket ws("/ws");

// Function to smoothly move a servo (adjust speed as needed)
void moveServo(int pin, int angle)
{
  servo.write(pin, angle, 2000, 0);
}

// Handle incoming WebSocket messages
void handleWebSocketMessage(void *arg, uint8_t *data, size_t len)
{
  DynamicJsonDocument doc(256);
  // Parse the JSON payload from the WebSocket message
  DeserializationError error = deserializeJson(doc, data, len);
  if (error)
  {
    Serial.println("Invalid JSON received");
    return;
  }

  // Handle servo commands
  if (doc.containsKey("servo") && doc.containsKey("angle"))
  {
    int angle = doc["angle"];
    const char *servoName = doc["servo"];
    if (strcmp(servoName, "top") == 0)
    {
      Serial.printf("Moving top servo to %d°\n", angle);
      moveServo(TOP_SERVO_PIN, angle);
    }
    else if (strcmp(servoName, "base") == 0)
    {
      Serial.printf("Moving base servo to %d°\n", angle);
      moveServo(BASE_SERVO_PIN, angle);
    }
  }

  // Handle LED color command
  if (doc.containsKey("led"))
  {
    int r = doc["led"]["r"];
    int g = doc["led"]["g"];
    int b = doc["led"]["b"];
    if (doc.containsKey("flicker"))
    {
      int flickerDuration = doc["flicker"];
      Serial.printf("Flickering LED color R:%d, G:%d, B:%d for %d ms\n", r, g, b, flickerDuration);
      flicker(r, g, b, flickerDuration);
    }
    else if (doc.containsKey("fade"))
    {
      int fadeDuration = doc["fade"];
      int fr = 0;
      int fg = 0;
      int fb = 0;
      if (doc.containsKey("from"))
      {
        fr = doc["from"]["r"];
        fg = doc["from"]["g"];
        fb = doc["from"]["b"];
      }
      Serial.printf("Fading LED color to R:%d, G:%d, B:%d over %d ms\n", r, g, b, fadeDuration);
      fadeToColor(fr, fg, fb, r, g, b, fadeDuration, EASE_IN_QUART);
    }
    else
    {
      Serial.printf("Setting LED color to R:%d, G:%d, B:%d\n", r, g, b);
      setColor(r, g, b);
    }
  }
}

// WebSocket event handler
void onWebSocketEvent(AsyncWebSocket *server, AsyncWebSocketClient *client, AwsEventType type, void *arg, uint8_t *data, size_t len)
{
  String msg; // Declare outside switch to avoid bypassing initialization
  switch (type)
  {
  case WS_EVT_CONNECT:
    Serial.printf("WebSocket client #%u connected from %s\n", client->id(), client->remoteIP().toString().c_str());
    msg = "{\"message\":\"Connected successfully\",\"clientId\":" + String(client->id()) + "}";
    client->text(msg);
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
void setup()
{
  Serial.begin(115200);
  delay(1000);

  // Connect to WiFi
  Serial.printf("Connecting to %s\n", WIFI_SSID);
  WiFi.begin(WIFI_SSID, WIFI_PSWD);
  while (WiFi.status() != WL_CONNECTED)
  {
    delay(500);
    Serial.print(".");
  }
  Serial.println();
  Serial.print("Connected! IP address: ");
  Serial.println(WiFi.localIP());

  setupLEDPWM(RED_PIN, GREEN_PIN, BLUE_PIN);

  // Attach servos
  servo.attach(TOP_SERVO_PIN, 4);
  servo.attach(BASE_SERVO_PIN, 5);

  // Start WebSocket server
  ws.onEvent(onWebSocketEvent);
  server.addHandler(&ws);
  server.begin();
  Serial.printf("WebSocket server started on port %d \r\n", PORT);
}

// ***** Main Loop *****
void loop()
{
  // Clean up disconnected clients
  ws.cleanupClients();
}
