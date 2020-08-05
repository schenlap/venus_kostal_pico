# venus_kostal_pico
The plugin generates a view of the current PV power on Venus. The inverter values are used for the internal consumption calculation on Venus. It is therefore not really necessary for the system to work, but still practical.

# Clone
git clone https://github.com/schenlap/venus_kostal_pico.git on your local computer (git is not installed on venus)

# Configure

## Kostal version 1 devices
Edit kostal.ini and add your credentials.
```
[KOSTAL]
ip = http://10.0.0.50 # yout ip adress
username = pvserver
password = xxxx
intervall = 10 # seconds
version = 1
```
## Kostal version 3 devices
For version 3 devices there are no login credentials necessary, leave them blank. You can test if yoh have a version 3 device if you enter ```http:<IP>/api/dxs.json?dxsEntries=67109120``` in the browser. If you don't get an error you have a version 3 device.
```
[KOSTAL]
ip = http://10.0.0.50 # yout ip adress
username =
password =
intervall = 10 # seconds
version = 3
```
       

# Get root access
A step by step guide for the root access is available at https://www.victronenergy.com/live/ccgx:root_access. This is necessary for venus_kostal_pico.

# Install
If setting up root access (preferable with ssh key), create a folder in data and add start script
ssh int venus
```
mkdir /data/venus_kostal_pico
echo -e '#!/bin/bash' >> /data/rc.local
echo '(cd /data/venus_kostal_pico/ && ./start_kostal_pico)' >> /data/rc.local
chmod +x /data/rc.local
exit

```
and copy all files
```
scp venus_kostal_pico/* root@venusip:/data/venus_kostal_pico/
```

# Test
You can test you script with /data/rc.local.  You should now see your inverter on venus display. To get same debug output you can start ```kosatal.py``` from the console. It should look something like this:
```
$ ./kostal.py 
Using http://10.0.0.49:90 user: pvserver
/data/venus_kostal_pico/kostal_inverter.pyc starting up
Thread: doing
['235']
{"STATUS": "  Einspeisen MPP", "VA": 229, "VB": 235, "VC": 230, "PT": 831, "IN0": 3.6, "PB": 291, "PC": 274, "PA": 266, "IA": 1.2, "IC": 1.2, "IB": 1.2, "EFAT": 47299}
++++++++++
POWER Phase A: 266W
POWER Phase B: 291W
POWER Phase C: 274W
POWER Total: 831W
KOSTAL Status:   Einspeisen MPP
```
