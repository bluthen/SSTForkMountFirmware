#include <QNEthernet.h>

namespace qn = qindesign::network;


#define DEBUG false
#define DEBUG_SERIAL if(DEBUG)Serial

// Based on TelnetClient.ino example of NativeEthernet.
// https://github.com/vjmuzik/NativeEthernet/blob/master/examples/TelnetClient/TelnetClient.ino

// Desktop test with nc: nc -lv 10002

// Buffer size for relaying data between serial and ethernet.
// LX200 commands/responses are small, 256 bytes is more than enough.
#define BUF_SIZE 256

IPAddress ip(192, 168, 46, 77);
IPAddress mount(192, 168, 46, 2);
IPAddress netmask(255,255,255,0);
IPAddress gw(192,168,46,2);



qn::EthernetClient client;

uint8_t serialBuf[BUF_SIZE];
uint8_t netBuf[BUF_SIZE];

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
    connectCounter = 0;
    while (!client.connected() && connectCounter < 300) {
      connectCounter++;
      client.abort();
      client.connect(mount, 10002);
      delay(10);
    }
    if (client.connected()) {
      // Disable Nagle's algorithm so small packets are sent immediately.
      // Critical for low-latency request/response protocols like LX200.
      client.setNoDelay(true);
      DEBUG_SERIAL.println("Client Connected");
    } else {
      DEBUG_SERIAL.println("Client connection failed");
    }
  } else {
    // Read all available bytes from the network and relay to serial in bulk.
    int avail = client.available();
    if (avail > 0) {
      if (avail > BUF_SIZE) avail = BUF_SIZE;
      int n = client.read(netBuf, avail);
      if (n > 0) {
        Serial.write(netBuf, n);
      }
    }

    // Read all available bytes from serial and send over TCP in a single write.
    avail = Serial.available();
    if (avail > 0 && client.connected()) {
      if (avail > BUF_SIZE) avail = BUF_SIZE;
      int n = 0;
      while (n < avail) {
        serialBuf[n++] = Serial.read();
      }
      client.writeFully(serialBuf, n);
      client.flush();
    }
  }
}
