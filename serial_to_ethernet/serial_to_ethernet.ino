#include <QNEthernet.h>

namespace qn = qindesign::network;


#define DEBUG false
#define DEBUG_SERIAL if(DEBUG)Serial

// Based on TelnetClient.ino example of NativeEthernet.
// https://github.com/vjmuzik/NativeEthernet/blob/master/examples/TelnetClient/TelnetClient.ino

// Desktop test with nc: nc -lv 10002



IPAddress ip(192, 168, 46, 77);
IPAddress mount(192, 168, 46, 2);
IPAddress netmask(255,255,255,0);
IPAddress gw(192,168,46,2);



qn::EthernetClient client;


void setup() {
  Serial.begin(9600);
  while (!Serial) {
    delay(1);
  }
  delay(1000);
  DEBUG_SERIAL.println("Starting");

  DEBUG_SERIAL.println("Ethernet.begin");
  qn::Ethernet.begin(ip, netmask, INADDR_NONE);
  DEBUG_SERIAL.println("After Ethernet.begin");

  if (qn::Ethernet.hardwareStatus() == qn::EthernetNoHardware) {
    DEBUG_SERIAL.println("Ethernet shield was not found.  Sorry, can't run without hardware. :(");
    while (true) {
      delay(1);  // do nothing, no point running without Ethernet hardware
    }
  }
}


void loop() {
  int connectCounter = 0;
  if(!qn::Ethernet.linkState()) {
    client.stop();
    DEBUG_SERIAL.println("Ethernet cable is not connected.");
    qn::Ethernet.waitForLink(1000);
    DEBUG_SERIAL.print("linkState: ");
    DEBUG_SERIAL.println(qn::Ethernet.linkState());
  } else if(!client.connected()) {
    DEBUG_SERIAL.println("Trying to connect client");
    client.stop();
    delay(10);
    connectCounter += 1;
    while (!client.connected() || connectCounter > 300) {
      connectCounter++;
      client.connect(mount, 10002);
      delay(10);
    }
    DEBUG_SERIAL.println("Client Conected");
  } else {
    // if there are incoming bytes available
    // from the server, read them and print them:
    if (client.available()) {
      char c = client.read();
      Serial.print(c);
    }

    // as long as there are bytes in the serial queue,
    // read them and send them out the socket if it's open:
    while (Serial.available() > 0) {
      char inChar = Serial.read();
      if (client.connected()) {
        client.print(inChar);
      }
    }
  }
}
