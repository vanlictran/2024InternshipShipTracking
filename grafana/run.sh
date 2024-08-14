sudo chown -R 472:472 ./
sudo chmod -R 755 ./

DOCKER_DEFAULT_PLATFORM=linux/amd64 docker compose up --build -d