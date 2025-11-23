#include <Arduino.h>

#include <SECRETS.h>
#include <SETTINGS.h>

#include <WiFi.h>
#include <ArduinoJson.h>

#include <ServoUtils.h>
#include <LedUtils.h>
#include <ServerUtils.h>

// TODO: Make led blue blinking while connecting, green while starting etc...

// ***** Setup *****
void setup()
{
  Serial.begin(115200);
  delay(1000);
  Serial.println("**************************");
  Serial.println("    Moving Head Light");
  Serial.println("**************************");
  Serial.println();
  Serial.println("Setuping leds & servos...");
  setupLEDPWM(RED_PIN, GREEN_PIN, BLUE_PIN);
  initServo();
  flicker(255, 0, 0, 500);
  // Connect to WiFi
  Serial.printf("Connecting to %s\n", WIFI_SSID);
  WiFi.begin(WIFI_SSID, WIFI_PSWD);
  while (WiFi.status() != WL_CONNECTED)
  {
    fadeToColor(0, 0, 0, 0, 0, 255, 500, EASE_IN_CUBIC);
    Serial.print(".");
    fadeToColor(0, 0, 255, 0, 0, 0, 500, EASE_IN_CUBIC);
  }
  setColor(255, 255, 255);
  Serial.println();
  Serial.print("Connected! Local Wifi IP address: ");
  Serial.println(WiFi.localIP());
  Serial.print("RSSI: ");
  Serial.println(WiFi.RSSI());
  Serial.println("Setuping AsyncWebServer & WebSocket...");
  setupServer();
  // Start WebSocket server
  Serial.printf("WebSocket server started on port %d \r\n", PORT);
  Serial.println("Operational!");
  flicker(0, 255, 0, 1000);
}

// ***** Main Loop *****
void loop()
{
  loopServer();
}
