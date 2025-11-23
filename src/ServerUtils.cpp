#include <ServerUtils.h>
#include <ServoUtils.h>
#include <LedUtils.h>

// WebSocket server on port 81
AsyncWebServer server(PORT);
AsyncWebSocket ws("/ws");

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
  if (doc["servo"].is<JsonArray>())
  {
    JsonArray servoCommands = doc["servo"];
    for (JsonObject command : servoCommands) {
      int angle = command["angle"];
      const char *servoName = command["servo"];
      if (strcmp(servoName, "top") == 0)
      {
        //Serial.printf("Moving top servo to %d°\n", angle);
        moveServo(TOP_SERVO_PIN, angle);
      }
      else if (strcmp(servoName, "base") == 0)
      {
        //Serial.printf("Moving base servo to %d°\n", angle);
        moveServo(BASE_SERVO_PIN, angle);
      }
    }
  }

  // Handle LED color command
  if (doc["led"].is<JsonObject>())
  {
    int r = doc["led"]["r"];
    int g = doc["led"]["g"];
    int b = doc["led"]["b"];
    if (doc["flicker"].is<int>())
    {
      int flickerDuration = doc["flicker"];
      //Serial.printf("Flickering LED color R:%d, G:%d, B:%d for %d ms\n", r, g, b, flickerDuration);
      flicker(r, g, b, flickerDuration);
    }
    else if (doc["fade"].is<int>())
    {
      int fadeDuration = doc["fade"];
      int fr = 0;
      int fg = 0;
      int fb = 0;
      if (doc["from"].is<JsonObject>())
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

void onOTAStart() {
  Serial.println("[OTA] Starting OTA update...");
  flicker(0, 0, 255, 500);
}

unsigned long ota_progress_millis = 0;

void onOTAProgress(size_t current, size_t final) {
  // Log every 1 second
  if (millis() - ota_progress_millis > 1000) {
    ota_progress_millis = millis();
    flicker(0, 0, 255, 100);
    Serial.printf("[OTA] Progress Current: %u bytes, Final: %u bytes\n", current, final);
  }
}

void onOTAEnd(bool success) {
  flicker(255, 0, 0, 1000);
  if (success) {
    Serial.println("[OTA] OTA update finished successfully!.. Rebooting");
  } else {
    Serial.println("There was an error during OTA update!");
  }
}

void setupServer()
{
  server.on("/", HTTP_GET, [](AsyncWebServerRequest *request) {
    request->send(200, "text/plain", "Hi! This is ElegantOTA. Go to /update to update.");
  });
  ws.onEvent(onWebSocketEvent);
  server.addHandler(&ws);
  ElegantOTA.begin(&server);
  ElegantOTA.onStart(onOTAStart);
  ElegantOTA.onProgress(onOTAProgress);
  ElegantOTA.onEnd(onOTAEnd);
  server.begin();
}

void loopServer()
{
  ElegantOTA.loop();
  ws.cleanupClients();
}