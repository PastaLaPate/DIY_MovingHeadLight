#include <ServerUtils.h>
#include <ServoUtils.h>
#include <LedUtils.h>

// Handle incoming WebSocket messages
void handleWebSocketMessage(void *arg, uint8_t *data, size_t len)
{
  JsonDocument doc;
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
  JsonDocument resp;
  String msg;

  switch (type)
  {
  case WS_EVT_CONNECT:
    Serial.printf("WebSocket client #%u connected from %s\n", client->id(), client->remoteIP().toString().c_str());
    resp["message"] = "Connected successfully";
    resp["clientId"] = String(client->id());
    serializeJson(resp, msg);
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

void setupServer()
{
  ws.onEvent(onWebSocketEvent);
  server.addHandler(&ws);
  ElegantOTA.begin(&server);
  server.begin();
}

void loopServer()
{
  ElegantOTA.loop();
  ws.cleanupClients();
}