#include <SETTINGS.h>

#include <ArduinoJson.h>
#include <ElegantOTA.h> // Can get free pro version w/ https://github.com/Missing-Link-harkat/ESP32-Scanner-POE/blob/main/lib/ElegantOTAPro/ElegantOTAPro.h
#include <ESPAsyncWebServer.h>
// WebSocket server on port 81
AsyncWebServer server(PORT);
AsyncWebSocket ws("/ws");

void setupServer();
void loopServer();