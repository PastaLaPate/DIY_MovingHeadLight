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
      LOGD("Received UDP Packet from %s Data: %.*s\n",
           packet.remoteIP().toString().c_str(), (int)packet.length(),
           (const char *)packet.data());

      // Copy exactly packet.length() bytes: the payload is not
      // NUL-terminated, so constructing from (char*) alone would
      // read past the buffer.
      String data((char *)packet.data(), packet.length());

      // No ACK: the controller streams absolute state at a fixed frame
      // rate and never reads the socket, so answering every packet would
      // only add airtime. The packet ID is still validated for format.
      Command cmd;
      if (parsePacket(data, cmd)) {
        applyCommand(cmd);
      }
    });
  }
}