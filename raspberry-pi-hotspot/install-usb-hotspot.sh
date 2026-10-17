#!/bin/sh
set -eu
test "$(id -u)" = 0
install -d /etc/systemd/network
install -m 644 10-airbnb-built-in.link /etc/systemd/network/10-airbnb-built-in.link
install -m 644 10-airbnb-usb.link /etc/systemd/network/10-airbnb-usb.link
if [ "$(nmcli -g WIFI-PROPERTIES.AP device show apusb)" != yes ]; then
    echo 'apusb needs a driver with access-point support before this can run.' >&2
    exit 1
fi
if ! nmcli connection show cozy-corner-rentals >/dev/null 2>&1; then
    nmcli connection add type wifi ifname apusb con-name cozy-corner-rentals ssid cozy-corner-rentals
fi
nmcli connection modify cozy-corner-rentals connection.interface-name apusb 802-11-wireless.ssid cozy-corner-rentals \
    802-11-wireless.mode ap 802-11-wireless.band bg 802-11-wireless.channel 1 \
    802-11-wireless.mac-address 34:E8:94:F7:D6:CF \
    802-11-wireless.ap-isolation yes \
    ipv4.method manual ipv4.addresses 10.43.0.1/24 ipv4.never-default yes \
    ipv6.method disabled connection.autoconnect yes connection.autoconnect-priority 999
nmcli connection up cozy-corner-rentals
nmcli device set apusb autoconnect yes
systemctl restart dnsmasq
