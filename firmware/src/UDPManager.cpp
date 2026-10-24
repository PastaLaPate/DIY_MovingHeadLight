#include <LedUtils.h>
#include <PacketParser.h>
#include <SETTINGS.h>
#include <UDPManager.h>

#include "HardwareSerial.h"

AsyncUDP udp;

/*

UDP Packet Structure:

number (32 bits) : Packet ID
args (in format key=value separated by ;) : Arguments

Arguments:
Servos:
- bS : Base Servo Angle
- tS : Top Servo Angle
Base RGB:
- r : LED Red Value (0-255)
- g : LED Green Value (0-255)
- b : LED Blue Value (0-255)

Flicker:
- fl : Flicker Duration (ms)

Fade:
- fa : Fade Duration (ms)
- fr : From Red Value (0-255)
- fg : From Green Value (0-255)
- fb : From Blue Value (0-255)

*/

String strs[20];

void setupUDPManager(AsyncWebServer *server) {
  if (udp.listen(UDP_PORT)) {
    Serial.print("UDP Listening on IP: ");
    Serial.print(WiFi.localIP());
    Serial.print(":");
    Serial.println(UDP_PORT);
    server->on(
        "/resetIndexCounter", HTTP_POST, [](AsyncWebServerRequest *request) {
          lastPackedIndex = 0;
          request->send(200, "text/plain", "Packet index counter reset.");
        });
    udp.onPacket([](AsyncUDPPacket packet) {
      Serial.print("Received UDP Packet from ");
      Serial.print(packet.remoteIP());
      Serial.print(" Data: ");
      Serial.write(packet.data(), packet.length());
      Serial.println();

      // Convert packet to String
      String data = String((char *)packet.data()).substring(0, packet.length());

      int packetID = parse_packet(data);

      // Send ACK if parsed correctly
      if (packetID != -1) {
        packet.printf("ACK:%u", packetID);
      }
    });
  }
}