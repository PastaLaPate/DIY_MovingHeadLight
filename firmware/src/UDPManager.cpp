#include <LedUtils.h>
#include <PacketParser.h>
#include <SETTINGS.h>
#include <UDPManager.h>

#include "HardwareSerial.h"

AsyncUDP udp;

void setupUDPManager() {
  if (udp.listen(UDP_PORT)) {
    Serial.print("UDP Listening on IP: ");
    Serial.print(WiFi.localIP());
    Serial.print(":");
    Serial.println(UDP_PORT);
    udp.onPacket([](AsyncUDPPacket packet) {
      Serial.print("Received UDP Packet from ");
      Serial.print(packet.remoteIP());
      Serial.print(" Data: ");
      Serial.write(packet.data(), packet.length());
      Serial.println();

      // Copy exactly packet.length() bytes: the payload is not
      // NUL-terminated, so constructing from (char*) alone would
      // read past the buffer.
      String data((char *)packet.data(), packet.length());

      Command cmd;
      if (parsePacket(data, cmd)) {
        applyCommand(cmd);
        packet.printf("ACK:%u", (unsigned)cmd.packetId);
      }
    });
  }
}