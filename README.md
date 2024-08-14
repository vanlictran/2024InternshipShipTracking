# Ship Tracking

## Table of contents
1- [**RF210 - Device**](#rf210---device)\
&nbsp;&nbsp; 1.1- [References](#references)\
&nbsp;&nbsp; 1.2- [Prelude - Operation of the clip](#prelude---operation-of-the-chip)\
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; 1.2.1- [RAK3172 - Communication module LoRaWAN](#rak3172---communication-module-lorawan)\
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; 1.2.2- [ESP32 - Microcontroller](#esp32---microcontroller)\
&nbsp;&nbsp; 1.3- [Build a device](#build-a-device)\
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; 1.3.1- [Requierements](#requierements)\
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; 1.3.2- [Step 1 : RAK3172](#rak3172---communication-module-lorawan)\
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; 1.3.3- [Step 2 : ESP32](#step-2--esp32)\
2- [**Chirpstack - LoRaWAN Server**](#chiprstack---lorawan-server)\
&nbsp;&nbsp; 2.1- [Step 1 : Create device profile](#step-1--create-device-profile)\
&nbsp;&nbsp; 2.1- [Step 2 : Create application & Manage device](#step-2--create-application--manage-device)




## RF210 - Device

### &nbsp; References
La puce utilisée est la RF210 de RFThings

Toutes les références utiles au projet :
* [RFThings : How to use RF210](https://github.com/PhamDuyAnh/RFThings_how_to_use) by PhamDuyAnh
* [RF210 : ATC Commands on RAK3172](https://github.com/XuanMinh201/RF210) by XuanMinh201
* [RF210 : ESP32 exemples for RF210](https://github.com/XuanMinh201/RF210-Lib-Example) by XuanMinh201
* [SUCA RF210](https://github.com/FabienFerrero/SUCA) by FabienFerrero

### &nbsp; Prelude - Operation of the chip

Dans cette partie, il y a deux manipulations distinctes à réaliser sur la carte pour pouvoir utiliser la carte dans le cadre de ce projet. Ces différentes manipulations sont explicitées dans la partie suivante **[Build a device](#build-a-device)**.

La puce RF210 a pour objectif de remonter les données de capteurs au LoRaWAN.
#### <span style="color: gray; font-weight: bold; font-size: medium; margin-left: 20px;">RAK3172 - Communication module LoRaWAN</span>
Ce module se présente comme composante mère de la carte : elle regroupe à la fois les fonctionalités de communication vers le LoRaWAN ainsi que les connectivités vers les capteurs.

En effet, ce dernier est relié au module GPS, à l'accéléromètre ou encore le thermomètre et il est possible de récupérer leur valeur via des commandes customisées dont vous pouvez retrouver le détail dans le [**README.md**](https://github.com/XuanMinh201/RF210/blob/main/README.md) du répertoire [RFThings_how_to_use](https://github.com/XuanMinh201/RF210). 

Pour les communications LoRa, RAKWireless a défini des commandes pour configurer et utiliser la puce facilement, et sont définies dans ce [projet](https://github.com/PhamDuyAnh/RFThings_how_to_use/blob/main) dans le [**README.md**](https://github.com/PhamDuyAnh/RFThings_how_to_use/blob/main/README.md#AT-command), partie **AT command**.

#### <span style="color: gray; font-weight: bold; font-size: medium; margin-left: 20px;">ESP32 - Microcontroller</span>
Composante maîtresse, elle est la cheffe d'orquestre de la RF210. Ce microcontrolleur se présente comme l'élément qui manipule les capteurs et autres composants, et traite les différentes données.

Le programme [**OTAA_GPS.ino**](./ESP32/OTAA_GPS/OTAA_GPS.ino) est un script de récupération, de pré-traitement et d'envoi de données sur les différents capteurs utiles à la traque des appareils.

Ci-dessous, le format des messages envoyés sur le LoRaWAN.

<image src="./assets/bit_composition_message_Chirpstack.drawio.png" style="max-height: 450px;"/>

Plus d'informations sur la carte dans ce [**document**](./assets/RF210C-SCAPA.pdf). 
### &nbsp; Build a device
#### <span style="color: gray; font-weight: bold; font-size: medium; margin-left: 20px;">Requierements</span>
- Une puce RF210
- l'IDE [Arduino](https://www.arduino.cc/en/software)
- le logiciel [STM32CubeProgammer](https://www.st.com/en/development-tools/stm32cubeprog.html)
- Une connexion en UART, pour la RAK3172

#### <span style="color: gray; font-weight: bold; font-size: medium; margin-left: 20px;">Step 1 : RAK3172</span>

Connectez l'UART à la RAK3172 comme ci-dessous.

<image src="./assets/RF210-UART_connexion.png" style="max-height:450px;"/>

Déposez le fichier hexadécimal sur la RAK3172 avec le logiciel STM32CubeProgrammer en suivant ces étapes.

1. Branchez l'UART à votre ordinateur
2. Ouvrir le logiciel STM32CubeProgrammer
3. Mettez votre appareil en bootmode, maintenez appuyez le bouton **B_RAK (boot)** et appuyez sur **R_RAK (reset)** puis relachez le bouton **B_RAK (boot)**
4. A droite, selectionnez le mode "**UART**", "**Braudrate 115200**" et appuyez sur "**Connect**"
5. En haut à gauche, selectionnez "**Open file**" et ouvrez le fichier [**ATC_Command_RF210_CKD.ino.hex**](./AT_Command/ATC_Command_RF210_CKD.ino.hex)
6. Selectionnez l'adresse "**0x80000000**" et appuyez sur "**Download**"
7. Appuyez sur le bouton **R_RAK (reset)** pour sortir du bootmode

#### <span style="color: gray; font-weight: bold; font-size: medium; margin-left: 20px;">Step 2 : ESP32</span>
Connectez la RF210 à votre ordinateur comme ci-dessous

<image src="./assets/RF210-ESP32_connexion.png" style="max-height:450px;"/>

1. Ouvrez Arduino
2. Ajoutez `https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json` dans **Fichier -> Préférences -> URL additionnelles**
3. Ouvrez le gestionnaire de carte depuis Outils -> Gestionnaire de carte et installez "RFTHings ESP32 Boards"
4. Selectionnez ESP32 RFThings boards/RF210 depuis Outils -> Menu des cartes
5. Selectionnez le port

Pour téléverser le code :
1. Ouvrez le fichier [OTAA_GPS.ino](./ESP32/OTAA_GPS/OTAA_GPS.ino) sur Arduino et connectez la carte RF210 en micro USB
2. Mettez la carte en bootmode en maintenant appuyé le bouton **B_ESP1 (boot)** et appuyer sur le bouton **ESP_EN1 (reset)** puis enfin relacher le bouton **B_ESP1 (boot)**
3. Sur Arduino, appuyer sur le bouton **Televerser**
4. Reset de la carte avec un appui simple sur le bouton **ESP_EN1 (reset)**

## Chiprstack - LoRaWAN Server

Chirpstack est le serveur LoRaWAN utilisé pour ce projet. Il nécessite une certaine configuration qui est expliqué dans cette partie.

### &nbsp; Step 1 : Create device profile
Here's some steps to help you to configure it. You need to enable OTAA connexion (type used by device).
1. Go to **Device-profiles** and click on **Create**
2. Configurez les différentes pages comme les images ci-dessous

<image src="./assets/chirpstack-device-profil-general.png" style="max-width:700px;"/>

<image src="./assets/chirpstack-device-profil-otaa-abp.png" style="max-width:700px;"/>

3. Dans la partie CODEC, mettre la fonction de decodage du fichier [**codec_decode.js**](./chirpstack/codec_decode.js) dans le dossier **/chiprstack/**

### &nbsp; Step 2 : Create Application & Manage Device
1. Go to **Applications** and click **Create**
2. On this section, fill the form and choose the correct **Profile**
3. After create success, website will turn back to applications menu. **Click on the name** of the application you create.
4. To create device, click on **Create**
5. In **General tab**, set a name and description. Set the **deviceEUI as random** and **select the correct device profile**
6. Click on **Create Device**
7. On this part, you need to configure the device for OTAA by **generate a random Application key** in the **KEYS (OTAA)** section

<image src="./assets/chirpstack-applications-keys.png" style="max-width:700px;"/>

8. Generate differents keys in **ACTIVATION** section **Network session key** and **Application session key**

<image src="./assets/chirpstack-applications-activation.png" style="max-width:700px;"/>

## Grafana & Needness - Monitoring
### &nbsp; Monitoring
#### <span style="color: gray; font-weight: bold; font-size: medium; margin-left: 20px;">Docker - Containerized solution</span>
Toute la partie Monitoring du projet et la totalité des essentielles au traitement, du stockage et de la visualisation des données, simplifiant le déploiement et s'assurant de 
#### <span style="color: gray; font-weight: bold; font-size: medium; margin-left: 20px;">Grafana - Visualization application</span>
Grafana est une application de visualisation de données par panneau pouvant prendre la forme de graphique, de tableau, de courbe ou encore de carte geo-spacial.\
Dans ce projet, l'application a subi une modification dans le plugin de visualisation **State Timeline**.
#### <span style="color: gray; font-weight: bold; font-size: medium; margin-left: 20px;">Prometheus & Pushgateway - Data storage</span>

#### <span style="color: gray; font-weight: bold; font-size: medium; margin-left: 20px;">Nginx - File's Web server</span>

#### <span style="color: gray; font-weight: bold; font-size: medium; margin-left: 20px;">Python server - Processing service</span>

### &nbsp; Deploy and Maintain
La documentation se trouve dans le dossier **/grafana/** sous le fichier [**README.md**](./grafana/README.md).