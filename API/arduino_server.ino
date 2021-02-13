#include <SPI.h>
#include <UIPEthernet.h>

EthernetServer server = EthernetServer(13081);

int VDC12 = 5;
int VAC12 = 6;

void setup()
{
  Serial.begin(9600);

  uint8_t mac[6] = {0x00,0x01,0x02,0x03,0x04,0x05};
  IPAddress ip(192,168,1,5);
  pinMode(VDC12, OUTPUT);
  pinMode(VAC12, OUTPUT);
  Serial.print("localIP: ");
  Serial.println(Ethernet.localIP());
  Serial.print("subnetMask: ");
  Serial.println(Ethernet.subnetMask());
  Serial.print("gatewayIP: ");
  Serial.println(Ethernet.gatewayIP());
  Serial.print("dnsServerIP: ");
  Serial.println(Ethernet.dnsServerIP());
  Ethernet.begin(mac,ip);

  server.begin();
}

void loop()
{
  size_t size;

  if (EthernetClient client = server.available())
    {
      while((size = client.available()) > 0)
        {
          uint8_t* msg = (uint8_t*)malloc(size);
          size = client.read(msg,size);
          Serial.write(msg,size);
          client.write(msg,size);
          free(msg);
        }
      digitalWrite(VAC12, HIGH);
      digitalWrite(VDC12, HIGH);
      delay(5000);
      digitalWrite(VDC12, LOW);
      digitalWrite(VAC12, LOW);
      client.flush();
      client.stop();
    }
}