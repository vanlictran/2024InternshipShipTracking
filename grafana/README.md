# MONITORING - Maintenance & Deployment
## Context
This document explain how this monitoring application works and how to deploy, maintain it.

## Table of content
 * [Technical explanations](#technical-explanations)
 * [Deployement](#deployement)
 * [Maintenance](#maintenance)

## Technical explanations
### &nbsp; Network and communication

### &nbsp; Data

## Deployement

This part is a tutorial to deploy the solution.

### &nbsp; Requierements
- Docker, refer to documentation docker : [Install on Ubuntu](https://docs.docker.com/engine/install/ubuntu/) or [Install on Windows Cumputer](https://www.docker.com/products/docker-desktop/)
- Permission

### &nbsp; Permissions
At the same level than this file :
```sh
sudo chown -R 472:472 ./grafana/
sudo chmod -R 755 ./grafana/
```
An error from grafana launch may occur due to permissions restrictions if not given.

### &nbsp; Application deployement
First, you need to verify the consumer is not in debug mode in the code.
```python
...
DEBUG = False
...
```
Now you can launch the application with the script bash `./run.sh`
```sh
sudo bash ./run.sh
```
## Maintenance
First, docker containers do not use versioned images for security update reasons and to troubleshoot potential issues.  
### &nbsp; Grafana
The grafana application used is a customized version. The docker image is available on [Docker Hub](https://hub.docker.com/repository/docker/benneuville/grafana-track-ship/general).<br>
This modified version improves boat monitoring and accessibility with a adapted State Timeline panel.

**<span style="color: red;">WARNING</span>** : By using this customized version grafana will not undergo any updates.

### &nbsp; MQTT Consumer
This part refer to the Python script working on a python server. You can modify the code, differents variables to configure data processing at what you want.

### &nbsp; Nginx server
This server is an auto-heberged file server. It used to give documents (like .geojson for zone delimitation) used for data processing and/or display.

You can add/delete/modify files directly in the folder `./datas/`. The volume is shared with the container directly while is up.
