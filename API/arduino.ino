#include <UIPEthernet.h>

EthernetClient client;
IPAddress ip(192,168,1,5);
char data[] = "ringing";
int dlength = sizeof(data) / sizeof(char);

char msg_check[4] = "open";
int msg_check_count = 0;
bool ring =  false;
int count = 0;
int bell_pin = 3;
int VDC12 = 5;
int VAC12 = 6;
void setup() {


  Serial.begin(9600);

  uint8_t mac[6] = {0x00,0x01,0x02,0x03,0x04,0x05};
  pinMode(VDC12, OUTPUT);
  pinMode(VAC12, OUTPUT);
  Ethernet.begin(mac, ip);
  pinMode(bell_pin, INPUT);
  Serial.print("localIP: ");
  Serial.println(Ethernet.localIP());
  Serial.print("subnetMask: ");
  Serial.println(Ethernet.subnetMask());
  Serial.print("gatewayIP: ");
  Serial.println(Ethernet.gatewayIP());
  Serial.print("dnsServerIP: ");
  Serial.println(Ethernet.dnsServerIP());
  client.connect(IPAddress(192,168,1,9),13081);
  while(client.connected()!=true) {
    client.connect(IPAddress(192,168,1,9),13081);
  }
  Serial.println("server connected");

}

void loop() {
    if(client.connected()!=true) {
        while(client.connected()!=true) {
          client.stop();
          client.connect(IPAddress(192,168,1,9),13081);
        }
        Serial.println("server connected");
    }

    if(digitalRead(bell_pin) == HIGH && ring == false){
      client.print("ringing");
      ring = true;
      Serial.println("ringing");
    }
    else {
      char msg[4] = "    ";
      client.read(msg, 4);
      Serial.write(msg, 4);
      Serial.println();
      for(int i = 0; i<4; i++) {
        if(msg[i] == msg_check[i]) {
          msg_check_count += 1;
        }
      }
      if(msg_check_count == 4) {
        msg_check_count = 0;
        client.print("received");
        digitalWrite(VAC12, HIGH);
        digitalWrite(VDC12, HIGH);
        delay(5000);
        digitalWrite(VDC12, LOW);
        digitalWrite(VAC12, LOW);

      }
      if(digitalRead(bell_pin) == LOW) {
        ring = false;
      }
      delay(100);
    }
}