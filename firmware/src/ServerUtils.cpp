#include "ArduinoJson.hpp"
#include "ArduinoJson/Object/JsonObject.hpp"
#include "WString.h"
#include <ESPAsyncWebServer.h>
#include <LittleFS.h>
#include <Update.h>

#include <LedUtils.h>
#include <PacketParser.h>
#include <SECRETS.h>
#include <SETTINGS.h>
#include <ServerUtils.h>
#include <ServoUtils.h>
#include <UDPManager.h>

extern const char ota_html[] asm("_binary_src_ota_html_start");

AsyncWebServer server(HTTP_PORT);
AsyncWebSocket ws("/ws");

static volatile bool otaStarted = false;
static volatile bool otaDone = false;
static volatile bool otaOk = false;
static volatile size_t otaCurrent = 0, otaTotal = 0;
static bool otaAuthorized = false;
static bool otaFailed = false;
static unsigned long otaLastLog = 0;

static void handleUpdateBody(AsyncWebServerRequest *req, uint8_t *data,
                             size_t len, size_t index, size_t total) {
  if (index == 0) {
    otaAuthorized = req->authenticate(OTA_USER, OTA_PASS);
    otaFailed = false;
    if (!otaAuthorized || Update.isRunning()) {
      otaFailed = true;
      return;
    }

    bool isFs = req->hasParam("type") && req->getParam("type")->value() == "fs";
    if (isFs)
      LittleFS.end(); // unmount before overwriting the partition

    if (!Update.begin(total, isFs ? U_SPIFFS : U_FLASH)) {
      Update.printError(Serial);
      otaFailed = true;
      return;
    }
    // Abort cleanly if the client drops mid-upload
    req->onDisconnect([]() {
      if (Update.isRunning()) {
        Update.abort();
        Serial.println("[OTA] Client disconnected, aborted");
      }
    });
    otaTotal = total;
    otaStarted = true;
  }

  if (!otaAuthorized || otaFailed)
    return;

  if (Update.write(data, len) != len) {
    Update.printError(Serial);
    otaFailed = true;
    return;
  }
  otaCurrent = index + len;

  if (index + len == total) {
    if (!Update.end(true)) {
      Update.printError(Serial);
      otaFailed = true;
    }
  }
}

String handleWebSocketMessage(void *arg, uint8_t *data, size_t len) {
  String data_str = String(data, len);
  int packetID = parse_packet(data_str);
  if (packetID != -1) {
    return "applied.";
  } else {
    return "format error.";
  }
}

void onWebSocketEvent(AsyncWebSocket *server, AsyncWebSocketClient *client,
                      AwsEventType type, void *arg, uint8_t *data, size_t len) {
  JsonDocument resp;
  String msg;

  switch (type) {
  case WS_EVT_CONNECT:
    Serial.printf("WebSocket client #%u connected from %s\n", client->id(),
                  client->remoteIP().toString().c_str());
    resp["message"] = "Connected successfully";
    resp["clientId"] = String(client->id());
    serializeJson(resp, msg);
    client->text(msg);
    break;
  case WS_EVT_DISCONNECT:
    Serial.printf("WebSocket client #%u disconnected\n", client->id());
    break;
  case WS_EVT_DATA:
    client->text(handleWebSocketMessage(arg, data, len));
    break;
  case WS_EVT_PING:
  case WS_EVT_PONG:
  case WS_EVT_ERROR:
    break;
  }
}

void setupServer() {
  if (!LittleFS.begin(true))
    Serial.println("LittleFS mount failed");

  server.on("/update", HTTP_GET, [](AsyncWebServerRequest *req) {
    if (!req->authenticate(OTA_USER, OTA_PASS))
      return req->requestAuthentication();
    req->send(200, "text/html", ota_html);
  });

  server.on("/config", HTTP_GET, [](AsyncWebServerRequest *req) {
    JsonDocument doc;

    JsonObject ports = doc["ports"].to<JsonObject>();
    ports["http"] = HTTP_PORT;
    ports["udp"] = UDP_PORT;

    JsonObject pins = doc["pins"].to<JsonObject>();
    pins["top_servo"] = TOP_SERVO_PIN;
    pins["base_servo"] = BASE_SERVO_PIN;
    pins["led_r"] = RED_PIN;
    pins["led_g"] = GREEN_PIN;
    pins["led_b"] = BLUE_PIN;

    String serialized;
    serializeJson(doc, serialized);
    req->send(200, "application/json", serialized.c_str());
  });

  server.on(
      "/update", HTTP_POST,
      [](AsyncWebServerRequest *req) {
        if (!otaAuthorized)
          return req->requestAuthentication();
        bool ok = !otaFailed && !Update.hasError();
        auto *res = req->beginResponse(
            ok ? 200 : 500, "text/plain",
            ok ? "OK, rebooting" : String("FAIL: ") + Update.errorString());
        res->addHeader("Connection", "close");
        req->send(res);
        otaOk = ok;
        otaDone = true;
      },
      nullptr, handleUpdateBody);

  server.serveStatic("/assets", LittleFS, "/assets")
      .setCacheControl("public, max-age=31536000, immutable");
  server.serveStatic("/", LittleFS, "/")
      .setDefaultFile("index.html")
      .setCacheControl("no-cache");

  ws.onEvent(onWebSocketEvent);
  server.addHandler(&ws);
  setupUDPManager(&server);

  server.serveStatic("/", LittleFS, "/").setDefaultFile("index.html");

  server.begin();
}

void loopServer() {
  ws.cleanupClients();

  // OTA events handled here, so the blocking flicker() never runs inside the
  // async task
  if (otaStarted) {
    otaStarted = false;
    Serial.println("[OTA] Starting OTA update...");
    flicker(0, 0, 255, 500);
  }
  if (Update.isRunning() && millis() - otaLastLog > 1000) {
    otaLastLog = millis();
    Serial.printf("[OTA] %u / %u bytes\n", (unsigned)otaCurrent,
                  (unsigned)otaTotal);
  }
  if (otaDone) {
    otaDone = false;
    if (otaOk) {
      Serial.println("[OTA] Finished successfully, rebooting");
      flicker(255, 0, 0, 1000);
      ESP.restart();
    } else {
      Serial.println("[OTA] Error during update");
    }
  }
}