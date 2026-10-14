# Airbnb-wifi Raspberry Pi captive portal

Installed on the Raspberry Pi at `192.168.1.151` using Ethernet for management
and internet access. The Pi's `wlan0` broadcasts an open 2.4 GHz network named
**Airbnb-wifi**, on channel 6. Wi-Fi clients receive `10.42.0.20–10.42.0.200`.

The TP-Link USB adapter broadcasts a second open network,
**cozy-corner-rentals-wifi**, on channel 1, with addresses
`10.43.0.20–10.43.0.200` and portal `http://10.43.0.1/`. Both networks serve the
same local site and block all internet access and access to each other.
Both captive portals open **Bed Bug Bordello** directly by default. The site's
collection and Garland pages remain accessible through its navigation.

The main parody site from this repository's `dist/` directory is served locally:

- On the hotspot: `http://10.42.0.1/` or `http://airbnb.wifi/`.
- On the existing home LAN: `http://192.168.1.151/`.
- Site files on the Pi: `/var/www/airbnb-wifi/`.

Common captive-network HTTP probes redirect to the local site. Phones control
whether they open a sign-in window automatically. If no window opens, browse
to `http://10.42.0.1/` after joining the hotspot. All videos, photos, fonts, scripts,
and styles are served by the Pi. Hotspot clients have no internet access: IPv4
forwarding is disabled, IPv6 is disabled on the AP, forwarded traffic is rejected,
and DNS never queries upstream servers. HTTP browsing redirects to the local
portal. The Pi itself retains Ethernet access for SSH and maintenance.

The firewall blocks hotspot access to private IPv4 networks and the Pi's SSH/VNC
services. AP client isolation is enabled. Existing Ethernet configuration and
the previous Wi-Fi client profile are retained. Network configuration backups
are under `/root/airbnb-wifi-backup/` on the Pi.

## USB adapter driver

The RTL8188EUS adapter's original `rtl8xxxu` driver did not advertise AP support.
The [SimplyCEO RTL8188EUS driver](https://github.com/SimplyCEO/rtl8188eus), pinned
to commit `491f34d1e7e40b6ca3ef91dc9b6563faca01d961`, provides the replacement
`8188eu` module. DKMS rebuilds it for installed kernel updates. The built-in
Wi-Fi adapter retains its original `brcmfmac` driver.

To set this up again, copy this folder to the Pi, then run:

```sh
sudo sh install-usb-driver.sh
sudo sh install-usb-hotspot.sh
```

The `--install` deployment enables the USB hotspot when its driver advertises
AP support. If reverting the USB driver, first stop its hotspot, remove
`/etc/modprobe.d/airbnb-usb-wifi.conf`, unload `8188eu`, and load `rtl8xxxu`.

## Refresh the site

With Python and Paramiko installed, run from this repository:

```powershell
python raspberry-pi-hotspot/deploy.py
```

The script asks for the SSH password and copies the current main `dist/` site,
optimized videos, linked `owners/` pages, and `slideshow-timer.js`. It caches the
Google fonts locally and fixes internal paths for the Pi's web root. Downloaded
full-size video folders are excluded from deployment. Credentials are not stored
in these files. Python packages: `paramiko` and `requests`.

To rebuild the GitHub-sized videos from the original download folders (FFmpeg
and ffprobe required):

```powershell
python raspberry-pi-hotspot/prepare-videos.py
```

Outputs are H.264/AAC MP4s under `dist/assets/whitefield/videos/`, with dimensions
up to 1280 by 720, a streaming-friendly MP4 header, and a size below 95 MiB each.
The originals stay in their download folders and are ignored by Git. Both site
versions reference the same optimized files. Source hashes allow unchanged videos
to be skipped when rerunning the preparation script.

## Reapply the configuration

The Pi needs `nginx`, `dnsmasq`, `nftables`, and NetworkManager installed.
The SSH account must support passwordless sudo for this deployment script.

```powershell
python raspberry-pi-hotspot/deploy.py --install
```

## Inspect or stop

Over SSH:

```sh
nmcli device status
sudo iw dev wlan0 info
systemctl status nginx dnsmasq airbnb-wifi-firewall
sudo journalctl -u dnsmasq -n 30
sudo cat /var/lib/misc/dnsmasq.leases
sudo nft list table inet airbnb_wifi
```

To stop the hotspot and restore the previous Wi-Fi connection:

```sh
sudo nmcli connection modify Airbnb-wifi connection.autoconnect no
sudo nmcli connection modify cozy-corner-rentals-wifi connection.autoconnect no
sudo nmcli connection down Airbnb-wifi
sudo nmcli connection down cozy-corner-rentals-wifi
sudo nmcli connection up netplan-wlan0-OpenWrt2.4
sudo systemctl disable --now dnsmasq airbnb-wifi-firewall
```

Nginx can continue serving the site on Ethernet. Disable it separately with
`sudo systemctl disable --now nginx` if desired.

To verify local video playback in a visible Edge window with every external
browser request blocked (requires the Python `playwright` package):

```powershell
python raspberry-pi-hotspot/verify-local-site.py
```

Setup uses the [NetworkManager settings reference](https://networkmanager.pages.freedesktop.org/NetworkManager/NetworkManager/nm-settings-nmcli.html).
