# GoldMu bot
simple bot (very hardrailed, no randoms, developed for fun)
I commit only lastest working version, old bot (prototype directory) has much more functions like: 
party bot, summon, zen check, roboflow with PK, gold moobs finder.

# prereqs
you need working raspberry pi zero with HID 

# instalacja RPi3
imager 2.0.3

## config ssh
username: brt
pass: testowe123

ssh brt@192.168.50.228

ssh-copy-id brt@192.168.50.228

## gadget mode config

sudo -i
nano /boot/firmware/config.txt

At the end of the file, add:
Bash:
```
dtoverlay=dwc2
```
Comment out the following lines (add # at the beginning of each):
Bash:
```
#dtparam=audio=on
#camera_auto_detect=1
#display_auto_detect=1
#dtoverlay=vc4-kms-v3d
#max_framebuffers=2
```


###
Instalcja python gdzie jest MuOnline

python 3.14

mkdir cv-project
cd cv-project
python -m venv venv
venv\Script\activate
python -m pip install -U pip

pip install opencv-python mss pywin32

#pico nuke
https://github.com/Gadgetoid/pico-universal-flash-nuke/releases/tag/v1.0.1


####
sprawdzenie czy gadget działa

watch -n 1 lsusb


na rpi

ls /sys/class/udc

ls /sys/kernel/config/usb_gadget

ma reset 143




sudo nano /etc/systemd/system/hid-flask.service


/home/brt/flask-keyboard/app.py

sudo journalctl -u hid-flask -f

sudo systemctl daemon-reexec
sudo systemctl daemon-reload
sudo systemctl enable hid-flask
sudo systemctl start hid-flask