#!/bin/sh
set -eu
# Run with sudo from this folder after copying the site to ./site/.
test "$(id -u)" = 0
test -f site/index.html
test -f site/app.js
test -f site/slideshow-timer.js
install -d /var/www/airbnb-wifi
cp -au site/. /var/www/airbnb-wifi/
chown -R root:root /var/www/airbnb-wifi
find /var/www/airbnb-wifi -type d -exec chmod 755 {} +
find /var/www/airbnb-wifi -type f -exec chmod 644 {} +
install -m 644 airbnb-wifi.conf /etc/dnsmasq.d/airbnb-wifi.conf
install -m 644 nginx-site.conf /etc/nginx/sites-available/airbnb-wifi
if [ -L /etc/nginx/sites-enabled/default ]; then
    unlink /etc/nginx/sites-enabled/default
fi
ln -sfn /etc/nginx/sites-available/airbnb-wifi /etc/nginx/sites-enabled/airbnb-wifi
install -m 644 airbnb-wifi.nft /etc/airbnb-wifi.nft
install -m 644 airbnb-wifi-firewall.service /etc/systemd/system/airbnb-wifi-firewall.service
printf 'net.ipv4.ip_forward=0\n' > /etc/sysctl.d/90-airbnb-wifi.conf
sysctl -p /etc/sysctl.d/90-airbnb-wifi.conf
nginx -t
dnsmasq --test
nft -c -f /etc/airbnb-wifi.nft
if ! nmcli connection show Airbnb-wifi >/dev/null 2>&1; then
    nmcli connection add type wifi ifname wlan0 con-name Airbnb-wifi ssid Airbnb-wifi
fi
nmcli connection modify Airbnb-wifi \
    802-11-wireless.mode ap 802-11-wireless.band bg 802-11-wireless.channel 6 \
    802-11-wireless.ap-isolation yes \
    ipv4.method manual ipv4.addresses 10.42.0.1/24 ipv4.never-default yes \
    ipv6.method disabled connection.autoconnect yes connection.autoconnect-priority 999
systemctl daemon-reload
systemctl disable --now airbnb-youtube.service 2>/dev/null || true
rm -f /etc/systemd/system/airbnb-youtube.service /usr/local/lib/airbnb-wifi/youtube-gateway.py
systemctl enable airbnb-wifi-firewall.service
systemctl restart airbnb-wifi-firewall.service
nmcli connection up Airbnb-wifi
systemctl enable nginx dnsmasq
systemctl restart nginx dnsmasq
