#include <LedUtils.h>
#include <SETTINGS.h>
#include <ServoUtils.h>
#include <UDPManager.h>

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
int lastPackedIndex = 0;

void setupUDPManager(AsyncWebServer *server) {
  if (udp.listen(1234)) {
    Serial.print("UDP Listening on IP: ");
    Serial.print(WiFi.localIP());
    Serial.println(":1234");
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

      // Split packet by ';'
      String tokens[20];
      int count = 0;
      while (data.length() > 0 && count < 20) {
        int idx = data.indexOf(';');
        if (idx == -1) {
          tokens[count++] = data;
          break;
        }
        tokens[count++] = data.substring(0, idx);
        data = data.substring(idx + 1);
      }

      if (count == 0)
        return;

      // ---- Extract Packet ID ----
      uint32_t packetID = tokens[0].toInt();
      Serial.print("Packet ID: ");
      Serial.println(packetID);
      if (packetID <= lastPackedIndex) {
        Serial.println("Duplicate or old packet. Ignoring.");
        return;
      }
      lastPackedIndex = packetID;

      // ---- Parse arguments into a dictionary ----
      std::map<String, String> args;

      for (int i = 1; i < count; i++) {
        int eq = tokens[i].indexOf('=');
        if (eq == -1)
          continue;

        String key = tokens[i].substring(0, eq);
        String value = tokens[i].substring(eq + 1);

        args[key] = value;
      }

      // ---- Debug print arguments ----
      Serial.println("Arguments:");
      for (auto const &kv : args) {
        Serial.print("  ");
        Serial.print(kv.first);
        Serial.print(" = ");
        Serial.println(kv.second);
      }

      if (args.count("bS")) {
        int baseServoAngle = args["bS"].toInt();
        Serial.print("Base Servo Angle = ");
        Serial.println(baseServoAngle);
        moveServo(BASE_SERVO_PIN, baseServoAngle);
      }

      if (args.count("tS")) {
        int topServoAngle = args["tS"].toInt();
        Serial.print("Top Servo Angle = ");
        Serial.println(topServoAngle);
        moveServo(TOP_SERVO_PIN, topServoAngle);
      }

      if (args.count("r") && args.count("g") && args.count("b")) {
        int r = args["r"].toInt();
        int g = args["g"].toInt();
        int b = args["b"].toInt();
        if (args.count("fl")) {
          int flickerDuration = args["fl"].toInt();
          Serial.printf("Flickering LED to RGB(%d, %d, %d) for %d ms\n", r, g,
                        b, flickerDuration);
          flicker(r, g, b, flickerDuration);
        } else if (args.count("fa")) {
          int fadeDuration = args["fa"].toInt();
          int fr = 0, fg = 0, fb = 0;
          if (args.count("fr"))
            fr = args["fr"].toInt();
          if (args.count("fg"))
            fg = args["fg"].toInt();
          if (args.count("fb"))
            fb = args["fb"].toInt();
          Serial.printf(
              "Fading LED from RGB(%d, %d, %d) to RGB(%d, %d, %d) over %d ms\n",
              fr, fg, fb, r, g, b, fadeDuration);
          fadeToColor(fr, fg, fb, r, g, b, fadeDuration, EASE_IN_QUART);
        } else {
          Serial.printf("Setting LED to RGB(%d, %d, %d)\n", r, g, b);
          setColor(r, g, b);
        }
      }

      // Send ACK
      packet.printf("ACK:%u", packetID);
    });
  }
}