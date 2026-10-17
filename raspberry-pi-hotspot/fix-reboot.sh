#!/bin/sh
set -eu
backup=/root/airbnb-wifi-backup/reboot-fix-$(date +%Y%m%d-%H%M%S)
mkdir -p "$backup"
cp -a /etc/netplan /etc/NetworkManager/system-connections /etc/systemd/network /etc/dnsmasq.d /etc/airbnb-wifi.nft "$backup/"
# Preserve the old client profile but prevent it taking either hotspot radio at boot.
for f in /etc/netplan/*.yaml; do
 if grep -q 'netplan-wlan0-OpenWrt2.4' "$f"; then
  sed -i '/proxy\._: /a\              connection.autoconnect: "false"' "$f"
 fi
done
nmcli connection modify netplan-wlan0-OpenWrt2.4 connection.autoconnect no
nmcli connection modify Airbnb-wifi connection.interface-name apbuilt 802-11-wireless.mac-address B8:27:EB:FA:FD:2B connection.autoconnect yes connection.autoconnect-retries 0
nmcli connection modify cozy-corner-rentals-wifi connection.id cozy-corner-rentals connection.interface-name apusb 802-11-wireless.ssid cozy-corner-rentals connection.autoconnect yes connection.autoconnect-retries 0
install -m 644 /home/science/reboot-fix/10-airbnb-built-in.link /etc/systemd/network/
install -m 644 /home/science/reboot-fix/10-airbnb-usb.link /etc/systemd/network/
install -m 644 /home/science/reboot-fix/airbnb-wifi.conf /etc/dnsmasq.d/
install -m 644 /home/science/reboot-fix/airbnb-wifi.nft /etc/
netplan generate
nginx -t
dnsmasq --test
nft -c -f /etc/airbnb-wifi.nft
systemctl enable nginx dnsmasq airbnb-wifi-firewall airbnb-portal
printf 'Backup: %s\n' "$backup"
