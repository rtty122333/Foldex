#!/bin/bash

DIR="$(cd "$(dirname $0)" && pwd)"

### Generate config file
conf=$DIR/etc/foldex.conf.gen
echo "[server]" > $conf
echo "host=0.0.0.0" >> $conf
echo "port=8893" >> $conf

read -p "Please input local server ip (NOT 127.0.0.1): " lip
echo "local_ip=$lip" >> $conf

echo -e "\n[evercloud]" >> $conf

read -p "Please input initcloud server ip: " iip
echo "host=$iip" >> $conf
echo "port=8081" >> $conf

echo "Ready to apply settings. Confirm[y/n]?"
while true; do
    read yn
    case $yn in
        [Yy] ) break;;
        [Nn] ) exit;;
        * ) echo "Invalid input. Enter y/n:";;
    esac
done
echo "Applying settings..."
[ -d /etc/foldex ] || mkdir -p /etc/foldex
mv $DIR/etc/foldex.conf.gen /etc/foldex/foldex.conf
echo "Done."

### Copy files
DEST=/opt/Foldex
if [ $DIR != $DEST ]; then
    [ -d $DEST ] && rm -rf $DEST
    mkdir -p $DEST
    cp -r $DIR/* $DEST/
fi

### Run as service
cp $DIR/etc/foldex.service /etc/systemd/system/
echo "Starting Service..."
systemctl enable foldex.service
systemctl daemon-reload
systemctl restart foldex.service
echo "Service started."
