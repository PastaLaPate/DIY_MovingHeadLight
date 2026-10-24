#include <LedUtils.h>
#include <ServerUtils.h>
#include <ServoUtils.h>
#include <UDPManager.h>

AsyncWebServer server(PORT);
AsyncWebSocket ws("/ws");

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
    Serial.printf("[OTA] Progress Current: %u bytes, Final: %u bytes\n",
                  current, final);
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

void setupServer() {
  server.on("/", HTTP_GET, [](AsyncWebServerRequest *request) {
    request->send(200, "text/plain",
                  "Hi! This is ElegantOTA. Go to /update to update.");
  });
  server.addHandler(&ws);
  setupUDPManager(&server);
  ElegantOTA.begin(&server);
  ElegantOTA.onStart(onOTAStart);
  ElegantOTA.onProgress(onOTAProgress);
  ElegantOTA.onEnd(onOTAEnd);
  server.begin();
}

void loopServer() {
  ElegantOTA.loop();
  ws.cleanupClients();
}