#!/bin/bash

set -e

echo "en_GB.UTF-8 UTF-8" >> /etc/locale.gen

locale-gen

# Latest Postgres Versions
sh -c 'echo "deb http://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/pgdg.list'
wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | apt-key add -


apt-get update

DEBIAN_FRONTEND=noninteractive apt-get install -y python3 python3-pip postgresql-12 libpq-dev  python-virtualenv rabbitmq-server

pip3 install sphinx virtualenv


cd /vagrant
virtualenv .ve -p python3
source .ve/bin/activate;
# pip install can fail if .ve already exists, and we don't want errors to stop buliding totally. So always pass.
pip3 install -r requirements_dev.txt  || true


su --login -c "psql -c \"CREATE USER app WITH PASSWORD 'password' CREATEDB;\"" postgres
su --login -c "psql -c \"CREATE DATABASE app WITH OWNER app ENCODING 'UTF8'  LC_COLLATE='en_GB.UTF-8' LC_CTYPE='en_GB.UTF-8'  TEMPLATE=template0 ;\"" postgres


echo "alias db='psql -U  app app  -hlocalhost'" >> /home/vagrant/.bashrc
echo "localhost:5432:app:app:password" > /home/vagrant/.pgpass
chown vagrant:vagrant /home/vagrant/.pgpass
chmod 0600 /home/vagrant/.pgpass
