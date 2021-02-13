
#include <SPI.h>
#include <UIPEthernet.h>

EthernetServer server = EthernetServer(13081);

int VDC12 = 5;
int VAC12 = 6;

void setup()
{
  uint8_t mac[6] = {0x00,0x01,0x02,0x03,0x04,0x05};
  IPAddress ip(192,168,1,5);
  pinMode(VDC12, OUTPUT);
  pinMode(VAC12, OUTPUT);
  Ethernet.begin(mac,ip);

  server.begin();
}

void loop()
{
  if (EthernetClient client = server.available())
    {
      while((client.available()) > 0)
        {
          char msg[5] = "";
          client.read(msg,size);
          client.write(msg,size);
        }
      client.flush();
      client.stop();
      digitalWrite(VAC12, HIGH);
      digitalWrite(VDC12, HIGH);
      delay(5000);
      digitalWrite(VDC12, LOW);
      digitalWrite(VAC12, LOW);
    }
}