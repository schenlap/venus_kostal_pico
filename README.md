# venus_kostal_pico
The plugin generates a view of the current PV power on Venus. The inverter values are used for the internal consumption calculation on Venus. It is therefore not really necessary for the system to work, but still practical.

# Clone
git clone https://github.com/schenlap/venus_kostal_pico.git on your local computer (git is not installed on venus)

# Configure

## Kostal version 1 devices
Edit kostal.ini and add your credentials.
```
[KOSTAL]
ip = http://10.0.0.50 # your ip adress
username = pvserver
password = xxxx
intervall = 10 # seconds
version = 1
# 0 for AC-IN1, 1 for AC-OUT, 2 FOR AC-IN2
position = 0
```
## Kostal version 2 devices
Version 2 devices respond on ```http://<IP>/measurements.xml``` with a xml page like
```
<root>
<Device Name="PIKO 2.5-1 MP plus" Type="Inverter" Platform="Net16" HmiPlatform="HMI17" NominalPower="2500" UserPowerLimit="nan" CountryPowerLimit="nan" Serial="XXXXXXXXXXXXXXXXXXXX" OEMSerial="YYYYYYYY" BusAddress="1" NetBiosName="INVZZZZZZZZZZZZ" WebPortal="PIKO Solar Portal" ManufacturerURL="kostal-solar-electric.com" IpAddress="192.168.0.1" DateTime="2021-11-06T08:10:32" MilliSeconds="055">
<Measurements>
<Measurement Value="229.5" Unit="V" Type="AC_Voltage"/>
<Measurement Value="6.345" Unit="A" Type="AC_Current"/>
<Measurement Value="1456.3" Unit="W" Type="AC_Power"/>
<Measurement Value="0.0" Unit="W" Type="AC_Power_fast"/>
<Measurement Value="49.982" Unit="Hz" Type="AC_Frequency"/>
<Measurement Value="78.7" Unit="V" Type="DC_Voltage"/>
<Measurement Value="0.106" Unit="A" Type="DC_Current"/>
<Measurement Value="335.0" Unit="V" Type="LINK_Voltage"/>
<Measurement Unit="W" Type="GridPower"/>
<Measurement Unit="W" Type="GridConsumedPower"/>
<Measurement Unit="W" Type="GridInjectedPower"/>
<Measurement Unit="W" Type="OwnConsumedPower"/>
<Measurement Value="100.0" Unit="%" Type="Derating"/>
</Measurements>
</Device>
</root>
```
Edit kostal.ini and set version 2.
```
[KOSTAL]
ip = http://10.0.0.50 # your ip adress
intervall = 10 # seconds
version = 2
# 0 for AC-IN1, 1 for AC-OUT, 2 FOR AC-IN2
position = 0
```
## Kostal version 3 devices
For version 3 devices there are no login credentials necessary, leave them blank. You can test if yoh have a version 3 device if you enter ```http:<IP>/api/dxs.json?dxsEntries=67109120``` in the browser. If you don't get an error you have a version 3 device.
```
[KOSTAL]
ip = http://10.0.0.50 # your ip adress
username =
password =
intervall = 10 # seconds
version = 3
# 0 for AC-IN1, 1 for AC-OUT, 2 FOR AC-IN2
position = 0
```

## Kostal plenticore devices
For all PIKO IQ and PLENTICORE PLUS inverters see https://github.com/davwil/venus_kostal_plenticore
You can check it with http://<IP>/api/v1/info/version. My plugin does not support PIKO IQ and PLENTICRE PLUS inverters!
       

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

## VELib python
VElib is necessary. Link the whole velib_python directory somewhere from venus into the directory of venus_kostal_pico or clone from https://github.com/victronenergy/velib_python.
```
root@venus_pi2:/data/venus_kostal_pico# ln -s /opt/victronenergy/dbus-pump/ext/velib_python ./
```

The structure of /data/venus_kostal_pico/ should look like this:
```
.
├── kostal.ini
├── kostal_inverter.py
├── kostal.py
├── README.md
├── start_kostal_pico
├── velib_python
│   ├── dbusdummyservice.py
│   ├── dbusmonitor.py
│   ├── examples
│   │   ├── vedbusitem_import_examples.py
│   │   └── vedbusservice_example.py
│   ├── LICENSE
│   ├── logger.py
│   ├── mosquitto_bridge_registrator.py
│   ├── __pycache__
│   │   ├── vedbus.cpython-39.pyc
│   │   └── ve_utils.cpython-39.pyc
│   ├── README.md
│   ├── settingsdevice.py
│   ├── streamcommand.py
...
```

# Test
You can test you script with /data/rc.local.  You should now see your inverter on venus display. To get same debug output you can start ```kostal.py``` from the console. It should look something like this:
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
