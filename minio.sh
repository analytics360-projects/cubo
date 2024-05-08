#!/bin/bash

apt update
apt upgrade
wget https://dl.min.io/server/minio/release/linux-amd64/archive/minio_20240113075303.0.0_amd64.deb
dpkg -i minio_20240113075303.0.0_amd64.deb
groupadd -r minio-user
useradd -M -r -g minio-user minio-user
mkdir /mnt/data
chown minio-user:minio-user /mnt/data
ufw allow 9000:9001/tcp
wget https://github.com/minio/certgen/releases/download/v1.2.0/certgen_1.2.0_linux_amd64.deb
dpkg -i certgen_1.2.0_linux_amd64.deb
certgen -host $(hostname -I)
mkdir -p /home/$(hostname)/.minio/certs
mv private.key public.crt /home/$(hostname)/.minio/certs
chown minio-user:minio-user /home/$(hostname)/.minio/certs/private.key
chown minio-user:minio-user /home/$(hostname)/.minio/certs/public.crt
