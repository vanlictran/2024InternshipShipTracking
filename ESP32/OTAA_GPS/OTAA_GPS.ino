/*
.d88888b  dP     dP  a88888b.  .d888888  
88.    "' 88     88 d8'   `88 d8'    88  
`Y88888b. 88     88 88        88aaaaa88a 
      `8b 88     88 88        88     88  
d8'   .8P Y8.   .8P Y8.   .88 88     88  
 Y88888P  `Y88888P'  Y88888P' 88     88  

   Author: fferrero, mtnguyen, lehuytrinh
   Code : RF210_RAK3172_bridge : Provide on ESP32 Serial port a direct access in write and read to Rak3172 module for AT Command mode

*/

#define NB_TRY_JOIN 5
#define TIMEOUT_JOIN 15000


String DEVEUI = "3CB7CC02DB418E4B";
String APPEUI = "0000000000000001";
String APPKEY = "D8C601ECDEB6B7E718E6314494ADAAD6";

int DC = 0;

int BAND = 9;

// ESP32 C3 SERIAL1 (second UART)
HardwareSerial mySerial1(1);

int rxPin = 20;
int txPin = 21;

void setup()
{
  Serial.begin(115200);
  delay(1000);
  

  Serial.println("-------------------");
  Serial.println("OTAA - GPS");
  Serial.println("-------------------");
  
  pinMode(txPin, OUTPUT);
  pinMode(rxPin, INPUT);
  pinMode(10, OUTPUT); //Rak enable
  pinMode(4, OUTPUT); // LED
  pinMode(1, OUTPUT); // GNSS enable
  digitalWrite(4, HIGH);   // turn the LED on (HIGH is the voltage level)
  delay(1000);                       // wait for a second
  digitalWrite(4, LOW);    // turn the LED off by making the voltage LOW
  delay(1000);  

  digitalWrite(10, HIGH); // Switch on RAK3172 LDO
  delay(1000);
  mySerial1.begin(115200, SERIAL_8N1, rxPin, txPin);
  delay(1000);  
  mySerial1.println("ATE");
  delay(20);
  Serial.println("-------------------");
  Serial.println("SETUP - AT COMMANDS");
  Serial.println("-------------------");
  Serial.println("starting...");

  /*
    while (mySerial1.available()){
      Serial.write(mySerial1.read()); // read it and send it out Serial (USB)
    }
  */
  mySerial1.println("AT+NWM=1");
  /*
    while (!mySerial1.available()){
      delay(200);
    }
  */
  delay(1000);
  mySerial1.println("AT+NJM=1");
  delay(300);
  mySerial1.println("AT+CLASS=A"); // Set CLASS
  delay(300);
  mySerial1.print("AT+BAND=");// Set frequency band
  mySerial1.println(BAND);
  delay(300);
  mySerial1.print("AT+DEVEUI=");
  mySerial1.println(DEVEUI);
  delay(200);

  mySerial1.print("AT+APPEUI=");
  mySerial1.println(APPEUI);
  delay(200);

  mySerial1.print("AT+APPKEY=");
  mySerial1.println(APPKEY);
  delay(200);


  delay(10000);
  flush_serial_AT();
  
  Serial.println("done");

  Serial.println("-------------------");
  Serial.println("JOINING ATTEMP");
  Serial.println("-------------------");
  Serial.println("starting...");


  for(int i = 0; i< NB_TRY_JOIN; i++) {
    if(!join()) {
      Serial.println("failed - retry...");
    }
    else {
      Serial.println("joined");
      break;
    }
    delay(2000);
  }
  Serial.println("done");

  Serial.println("-------------------");
  Serial.println("ACTIVATING GPS");
  Serial.println("-------------------");
  Serial.println("starting...");
  
  mySerial1.println("ATC+GPSON=1"); // Activate GNSS
  delay(500);
  mySerial1.println("ATC+GPSON=1"); // Activate GNSS
  delay(500);
  flush_serial_AT();
  Serial.println("done");

  Serial.println("-------------------");
  Serial.println("END");
}

void loop()
{
  int16_t x = 1000 * measure_acc(1);
  int16_t y = 1000 * measure_acc(2);
  int16_t z = 1000 * measure_acc(3);
  
  int16_t t = (int16_t) 10 * measure_temp(); // return temperature in tens of degree

  int16_t b = measure_bat() / 10;

  int32_t LatitudeBinary = 10000 * measure_gnss(1); //Latitude : 0.0001 ° Signed MSB
  int32_t LongitudeBinary = 10000 * measure_gnss(2); //Longitude : 0.0001 ° Signed MSB
  uint16_t s = 100 * measure_gnss(4); // nb of satellite in view with GNSS

  int i = 0;
  unsigned char mydata[64];
  /*
  //lattitude
  mydata[i++] = ( LatitudeBinary >> 16 ) & 0xFF;
  mydata[i++] = ( LatitudeBinary >> 8 ) & 0xFF;
  mydata[i++] = LatitudeBinary & 0xFF;
  
  //longitude
  mydata[i++] = ( LongitudeBinary >> 16 ) & 0xFF;
  mydata[i++] = ( LongitudeBinary >> 8 ) & 0xFF;
  mydata[i++] = LongitudeBinary & 0xFF;
  // 0 byte
  mydata[i++] = DC;
  //acceleration
  mydata[i++] = x >> 8;
  mydata[i++] = x & 0xFF;
  mydata[i++] = y >> 8;
  mydata[i++] = y & 0xFF;
  mydata[i++] = z >> 8;
  mydata[i++] = z & 0xFF;
  // 0 byte
  mydata[i++] = DC;
  //temperature
  mydata[i++] = t >> 8;
  mydata[i++] = t & 0xFF;
  */
  //battery
  mydata[i++] = b >> 8;
  mydata[i++] = b & 0xFF;
  

  char str[i] = "";
  array_to_string(mydata, i, str);

  //if(s > 0 && LatitudeBinary > 0 && LongitudeBinary > 0) {
    mySerial1.printf("AT+SEND=3:");
    mySerial1.println(str);
    
    mySerial1.readStringUntil('\n');
    
    while (mySerial1.available() == 0)
    {
      delay(100);
    }
    
    if (mySerial1.available())
    { // If anything comes in Serial1 (pins 4 & 5)
      while (mySerial1.available())
        Serial.write(mySerial1.read()); // read it and send it out Serial (USB)
    }
    
    Serial.print("AT set complete with downlink : ");
    Serial.println(str);

    delay(10000);
    return;
  /*}
  else {
    Serial.println("No GPS DATA FOUND");
    delay(5000);
  }
*/
}

bool join() {
  mySerial1.println("AT+JOIN");
  String join = "";
  int start = millis();

  while(millis()-start < TIMEOUT_JOIN) {
    if(mySerial1.available()) {
      join = mySerial1.readStringUntil('\n');
      join.trim();
      if (join.equals("+EVT:JOINED"))
        return 1;
    }
    delay(1000);
  }
  
  Serial.println("ended");

  if (join.equals("+EVT:JOINED"))
    return 1;
  return 0;
}


// Return Acceleration level in G
float measure_acc(int axis) {
  flush_serial_AT();
  if (axis == 1) {
    mySerial1.println("ATC+AX=?");
  }
  else if (axis == 2) {
    mySerial1.println("ATC+AY=?");
  }
  else if (axis == 3) {
    mySerial1.println("ATC+AZ=?");
  }
  String a;
  delay(100);
  if (mySerial1.available()) {
    a = mySerial1.readStringUntil('\n');
    //Serial.print("Acc:");
    Serial.println(a);
  }
  return a.toFloat();
}

// Return bat level in mv
float measure_bat() {

  //Serial.flush();
  flush_serial_AT();// flush AT Serial reading buffer

  mySerial1.println("ATC+BAT=?"); // Request bat value
  String bat;
  while (mySerial1.available() == 0)
  {
    delay(100);
  }
  delay(100);

  if (mySerial1.available()) {
    bat = mySerial1.readStringUntil('\n');
    Serial.print("Bat:");
    Serial.println(bat);
  }

  return bat.toFloat();
}


// Return temperature level in degree
float measure_temp() {

  //Serial.flush();
  flush_serial_AT();// flush AT Serial reading buffer

  mySerial1.println("ATC+TEMP=?"); // Request bat value
  String temperature;
  while (mySerial1.available() == 0)
  {
    delay(100);
  }


  if (mySerial1.available()) {
    temperature = mySerial1.readStringUntil('\n');
    Serial.print("Temperature:");
    Serial.println(temperature);
  }

  return temperature.toFloat();
}



// Return 1:lat 2:long 3:alt 4:sat from GNSS
float measure_gnss(int axis) {

  //Serial.flush();
  flush_serial_AT();// flush AT Serial reading buffer

  if (axis == 1) {
    mySerial1.println("ATC+GPSLAT=?"); // Request lat value
    Serial.print("Lat:");
  }
  else if (axis == 2) {
    mySerial1.println("ATC+GPSLON=?"); // Request lon value
    Serial.print("Long:");
  }
  else if (axis == 3) {
    mySerial1.println("ATC+GPSALT=?"); // Request alt value
    Serial.print("Altitude:");
  }
  else if (axis == 4) {
    mySerial1.println("ATC+GPSSAT=?"); // Request sat value
    Serial.print("Sat:");
  }
  else if (axis == 5) {
    mySerial1.println("ATC+GPSPWR=?"); // Request sat value
    Serial.print("On:");
  }

  String a;
  while (mySerial1.available() == 0)
  {
    delay(100);
  }


  if (mySerial1.available())
  { // If anything comes in Serial1 (pins 4 & 5)
    a = mySerial1.readStringUntil('\n');
    Serial.println(a);
    delay(100);
    mySerial1.readStringUntil('\n');
  }


  if (a.toFloat() > 5  && DC == 0 && axis == 4)
  {
    mySerial1.println("ATC+GPSDC=1"); // Activate GNSS
    DC = 1;
  }
  if (a.toFloat() < 5  && DC == 1 && axis == 4)
  {
    mySerial1.println("ATC+GPSDC=0"); // Activate GNSS
    DC = 0;
  }


  return a.toFloat();
}


void array_to_string(byte array[], unsigned int len, char buffer[])
{
  for (unsigned int i = 0; i < len; i++)
  {
    byte nib1 = (array[i] >> 4) & 0x0F;
    byte nib2 = (array[i] >> 0) & 0x0F;
    buffer[i * 2 + 0] = nib1  < 0xA ? '0' + nib1  : 'A' + nib1  - 0xA;
    buffer[i * 2 + 1] = nib2  < 0xA ? '0' + nib2  : 'A' + nib2  - 0xA;
  }
  buffer[len * 2] = '\0';
}

// Uart sent
void flush_serial_AT() {
  if (mySerial1.available())
  {
    while (mySerial1.available())
      mySerial1.read();
  }
  delay(100);
}