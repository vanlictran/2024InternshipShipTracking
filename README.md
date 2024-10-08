# Ship Tracking

## Table of Contents
1- [**RF210 - Device**](#rf210---device)\
&nbsp;&nbsp; 1.1- [References](#references)\
&nbsp;&nbsp; 1.2- [Prelude - Operation of the Chip](#prelude---operation-of-the-chip)\
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; 1.2.1- [RAK3172 - LoRaWAN Communication Module](#rak3172---lorawan-communication-module)\
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; 1.2.2- [ESP32 - Microcontroller](#esp32---microcontroller)\
&nbsp;&nbsp; 1.3- [Build a Device](#build-a-device)\
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; 1.3.1- [Requirements](#requirements)\
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; 1.3.2- [Step 1: RAK3172](#step-1--rak3172)\
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; 1.3.3- [Step 2: ESP32](#step-2--esp32)\
2- [**ChirpStack - LoRaWAN Server**](#chirpstack---lorawan-server)\
&nbsp;&nbsp; 2.1- [Step 1: Create Device Profile](#step-1--create-device-profile)\
&nbsp;&nbsp; 2.1- [Step 2: Create Application & Manage Device](#step-2--create-application--manage-device)\
3- [**Grafana & Needness - Monitoring**](#grafana--needness---monitoring)\
&nbsp;&nbsp; 3.1- [Access to Application](#access-to-application)\
&nbsp;&nbsp; 3.2- [Monitoring](#monitoring)\
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; 3.2.1- [Docker - Containerized solution](#docker---containerized-solution)\
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; 3.2.2- [Grafana - Visualization application](#grafana---visualization-application)\
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; 3.2.3- [Prometheus & Pushgateway - Data storage](#prometheus--pushgateway---data-storage)\
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; 3.2.4- [Nginx - File Web server](#nginx---file-web-server)\
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; 3.2.5- [Python server - processing service](#python-server---processing-service)\
&nbsp;&nbsp; 3.3- [Deploy and Maintain](#deploy-and-maintain)



## RF210 - Device

### &nbsp; References
The chip used is the RF210 from RFThings.

All useful references for the project:
* [RFThings: How to use RF210](https://github.com/PhamDuyAnh/RFThings_how_to_use) by PhamDuyAnh
* [RF210: ATC Commands on RAK3172](https://github.com/XuanMinh201/RF210) by XuanMinh201
* [RF210: ESP32 examples for RF210](https://github.com/XuanMinh201/RF210-Lib-Example) by XuanMinh201
* [SUCA RF210](https://github.com/FabienFerrero/SUCA) by FabienFerrero

### &nbsp; Prelude - Operation of the Chip
In this section, there are two distinct operations to perform on the board to use it in this project. These different operations are explained in the following section **[Build a Device](#build-a-device)**.

The RF210 chip's purpose is to send sensor data to the LoRaWAN network.

#### <span style="color: gray; font-weight: bold; font-size: medium; margin-left: 20px;">RAK3172 - LoRaWAN Communication Module</span>
This module serves as the main component of the board, encompassing both the communication functions to the LoRaWAN network and the connections to the sensors.

It is connected to the GPS module, accelerometer, and thermometer, and it is possible to retrieve their values via customized commands, detailed in the [**README.md**](https://github.com/XuanMinh201/RF210/blob/main/README.md) of the [RFThings_how_to_use](https://github.com/XuanMinh201/RF210) repository.

For LoRa communications, RAKWireless has defined commands to easily configure and use the chip, detailed in this [project](https://github.com/PhamDuyAnh/RFThings_how_to_use/blob/main) in the [**README.md**](https://github.com/PhamDuyAnh/RFThings_how_to_use/blob/main/README.md#AT-command), under the **AT command** section.

#### <span style="color: gray; font-weight: bold; font-size: medium; margin-left: 20px;">ESP32 - Microcontroller</span>
The master component, it orchestrates the RF210. This microcontroller handles the sensors and other components and processes the various data.

The [**OTAA_GPS.ino**](./ESP32/OTAA_GPS/OTAA_GPS.ino) program is a script for collecting, preprocessing, and sending data from the sensors useful for device tracking.

Below is the format of the messages sent to the LoRaWAN network.

<image src="./assets/bit_composition_message_Chirpstack.drawio.png" style="max-height: 450px;"/>

More information about the board can be found in this [**document**](./assets/RF210C-SCAPA.pdf).

### &nbsp; Build a Device
#### <span style="color: gray; font-weight: bold; font-size: medium; margin-left: 20px;">Requirements</span>
- An RF210 chip
- [Arduino IDE](https://www.arduino.cc/en/software)
- [STM32CubeProgrammer](https://www.st.com/en/development-tools/stm32cubeprog.html) software
- A UART connection, for the RAK3172

#### <span style="color: gray; font-weight: bold; font-size: medium; margin-left: 20px;">Step 1: RAK3172</span>
Connect the UART to the RAK3172 as shown below.

<image src="./assets/RF210-UART_connexion.png" style="max-height:450px;"/>

Upload the hexadecimal file to the RAK3172 using STM32CubeProgrammer software by following these steps:

1. Connect the UART to your computer
2. Open STM32CubeProgrammer software
3. Put your device in boot mode, hold the **B_RAK (boot)** button, press **R_RAK (reset)**, then release the **B_RAK (boot)** button
4. On the right, select "**UART**", "**Baudrate 115200**", and click "**Connect**"
5. In the top left, select "**Open file**" and open the file [**ATC_Command_RF210_CKD.ino.hex**](./AT_Command/ATC_Command_RF210_CKD.ino.hex)
6. Select address "**0x80000000**" and click "**Download**"
7. Press the **R_RAK (reset)** button to exit boot mode

#### <span style="color: gray; font-weight: bold; font-size: medium; margin-left: 20px;">Step 2: ESP32</span>
Connect the RF210 to your computer as shown below.

<image src="./assets/RF210-ESP32_connexion.png" style="max-height:450px;"/>

1. Open Arduino
2. Add `https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json` in **File -> Preferences -> Additional URLs**
3. Open the board manager from Tools -> Board Manager and install "RFTHings ESP32 Boards"
4. Select ESP32 RFThings boards/RF210 from Tools -> Board Menu
5. Select the port

To upload the code:
1. Open the [OTAA_GPS.ino](./ESP32/OTAA_GPS/OTAA_GPS.ino) file in Arduino and connect the RF210 board via micro USB
2. Put the board in boot mode by holding the **B_ESP1 (boot)** button, pressing the **ESP_EN1 (reset)** button, then releasing the **B_ESP1 (boot)** button
3. In Arduino, click the **Upload** button
4. Reset the board with a single press on the **ESP_EN1 (reset)** button

## ChirpStack - LoRaWAN Server
ChirpStack is the LoRaWAN server used for this project. It requires certain configurations, which are explained in this section.

### &nbsp; Step 1: Create Device Profile
Here are some steps to help you configure it. You need to enable OTAA connection (the type used by the device).
1. Go to **Device-profiles** and click **Create**
2. Configure the different pages as shown in the images below

<image src="./assets/chirpstack-device-profil-general.png" style="max-width:700px;"/>

<image src="./assets/chirpstack-device-profil-otaa-abp.png" style="max-width:700px;"/>

3. In the CODEC section, add the decoding function from the [**codec_decode.js**](./chirpstack/codec_decode.js) file in the **/chirpstack/** folder

### &nbsp; Step 2: Create Application & Manage Device
1. Go to **Applications** and click **Create**
2. In this section, fill out the form and choose the correct **Profile**
3. After successful creation, the website will return to the applications menu. **Click on the name** of the application you created.
4. To create a device, click **Create**
5. In the **General tab**, set a name and description. Set the **deviceEUI as random** and **select the correct device profile**
6. Click **Create Device**
7. In this part, you need to configure the device for OTAA by **generating a random Application key** in the **KEYS (OTAA)** section

<image src="./assets/chirpstack-applications-keys.png" style="max-width:700px;"/>

8. Generate different keys in the **ACTIVATION** section for **Network session key** and **Application session key**

<image src="./assets/chirpstack-applications-activation.png" style="max-width:700px;"/>

### &nbsp; Step 3: Consume ChirpStack Application Number
In the [**consumer.py**](./grafana/mqtt-consumer/consumer.py) file located in `./grafana/mqtt-consumer`, you need to reference the ID of your application in the **`APP_NUMBER`** variable, found in the first lines of the script.\
You can find the ID in the URL of your application on ChirpStack, in the first column:
<image src="./assets/chirpstack-application-id.png" style="max-width:700px;"/>

## Grafana & Needness - Monitoring

### &nbsp; Access to Application

<table style="width: 350px; margin-left: 40px">
<thead style="background: lightgrey">
    <tr>
        <th style="text-align: center;" scope="col">Application</th>
        <th style="text-align: center;width: 25%" scope="col">Port</th>
    </tr>
</thead>
<tbody style="color: darkred">
    <tr style="color: darkorange;">
        <th scope="row" style="padding-bottom: 15px; padding-top: 12px">Grafana</th>
        <th scope="row">4445</th>
    </tr>
    <tr>
        <td>Prometheus</td>
        <td>4444</td>
    </tr>
    <tr>
        <td>Pushgateway</td>
        <td>4447</td>
    </tr>
    <tr style="color: darkgreen">
        <td>Nginx</td>
        <td>3030</td>
    </tr>
</tbody>
</table>

### &nbsp; Monitoring
#### <span style="color: gray; font-weight: bold; font-size: medium; margin-left: 20px;">Docker - Containerized Solution</span>
The entire Monitoring section of the project, along with all the essentials for data processing, storage, and visualization, is containerized, simplifying deployment and ensuring a dedicated environment for each application.
#### <span style="color: gray; font-weight: bold; font-size: medium; margin-left: 20px;">Grafana - Visualization Application</span>
Grafana is a data visualization application that can display data in the form of graphs, tables, curves, or geospatial maps.\
In this project, the application has been modified in the **State Timeline** visualization plugin.
#### <span style="color: gray; font-weight: bold; font-size: medium; margin-left: 20px;">Prometheus & Pushgateway - Data Storage</span>
Prometheus, coupled with Pushgateway, enables **time-series data storage**. This application is part of the **integrated plugins** of Grafana, and its use is recommended by the visualization tool.

The Pushgateway serves as a simple **gateway** between the storage service, Prometheus, and the Python processing service.

#### <span style="color: gray; font-weight: bold; font-size: medium; margin-left: 20px;">Nginx - File Web Server</span>
The Nginx web server is used for **file distribution** for the Grafana service. It is also used by the Python service for data processing.
It initially distributes **GeoJSON** files to enable the display of zones and the determination of device statuses.

#### <span style="color: gray; font-weight: bold; font-size: medium; margin-left: 20px;">Python Server - Processing Service</span>
This is a simple data processing server that also handles the transit of data between the LoRaWAN server and the storage service.

The service includes several sections highlighted in the code by comments.\
The information retrieved is explained in the [ESP32 - Microcontroller](#esp32---microcontroller) section.

Additional processing performed includes:
- Simple calculation of speed between the current and previous points
- Determination of device status based on its position and movements
- Determination of collision routes in the near future, which involves estimating movement between the different devices.

### &nbsp; Deploy and Maintain
The documentation is located in the **/grafana/** folder under the file [**README.md**](./grafana/README.md).
