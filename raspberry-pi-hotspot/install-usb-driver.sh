#!/bin/sh
# Tested on the Pi's RTL8188EUS USB adapter and 6.18.50+rpt-rpi-v8 kernel.
set -eu
test "$(id -u)" = 0
apt-get install -y dkms build-essential
test -d "/lib/modules/$(uname -r)/build"
source_dir=/usr/local/src/airbnb-rtl8188eus
if [ ! -d "$source_dir/.git" ]; then
    git clone https://github.com/SimplyCEO/rtl8188eus.git "$source_dir"
fi
cd "$source_dir"
git checkout 491f34d1e7e40b6ca3ef91dc9b6563faca01d961
sed -i 's/CONFIG_PLATFORM_I386_PC = y/CONFIG_PLATFORM_I386_PC = n/;s/CONFIG_PLATFORM_ARM64_RPI = n/CONFIG_PLATFORM_ARM64_RPI = y/' Makefile
if ! dkms status realtek-rtl8188eus/5.3.9 | grep -q 'installed'; then
    dkms install .
fi
# The built-in brcmfmac adapter and Ethernet are unaffected by this swap.
nmcli device disconnect wlan1 || true
modprobe -r rtl8xxxu
modprobe 8188eu
sleep 3
if [ "$(nmcli -g WIFI-PROPERTIES.AP device show wlan1)" != yes ]; then
    modprobe -r 8188eu
    modprobe rtl8xxxu
    echo 'AP support did not appear; restored the previous USB driver.' >&2
    exit 1
fi
printf 'blacklist rtl8xxxu\n' > /etc/modprobe.d/airbnb-usb-wifi.conf
if command -v update-initramfs >/dev/null 2>&1; then
    update-initramfs -u -k "$(uname -r)"
fi
