#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# vi: set autoindent noexpandtab tabstop=4 shiftwidth=4

import logging
from dbus.mainloop.glib import DBusGMainLoop
try:
    from gi.repository import GObject as gobject
    from gi.repository.GObject import idle_add
except ImportError:
    import gobject
    from gobject import idle_add
import dbus
import dbus.service
import inspect
import pprint
import os
import sys

# velib path
sys.path.insert(1, os.path.join(os.path.dirname(__file__), './velib_python'))
from vedbus import VeDbusService

class KostalInverter:
    dbusservice = []

    def __init__(self, dev, connection, instance, serial, product, firmwarev, pversion, position):
        # Set up logging
        logging.basicConfig(level=logging.DEBUG)
        logging.debug(f"Registriere DBus-Dienst: com.victronenergy.pvinverter.{dev}")
        print(__file__ + " starting up")

        # Initialize DBus service with register=False
        self.dbusservice = VeDbusService('com.victronenergy.pvinverter.' + dev, register=False)

        # Add objects required by ve-api
        self.dbusservice.add_path('/Mgmt/ProcessName', __file__)
        self.dbusservice.add_path('/Mgmt/ProcessVersion', pversion)
        self.dbusservice.add_path('/Mgmt/Connection', connection)
        self.dbusservice.add_path('/DeviceInstance', instance)
        self.dbusservice.add_path('/ProductId', 0xFFFF)  # 0xB012 ?
        self.dbusservice.add_path('/ProductName', product)
        self.dbusservice.add_path('/FirmwareVersion', firmwarev)
        self.dbusservice.add_path('/Serial', serial)
        self.dbusservice.add_path('/CustomName', dev)
        self.dbusservice.add_path('/Connected', 1, writeable=True)
        self.dbusservice.add_path('/ErrorCode', '(0) No Error')
        self.dbusservice.add_path('/Position', position)

        _kwh = lambda p, v: (str(v) + 'KWh')
        _a = lambda p, v: (str(v) + 'A')
        _w = lambda p, v: (str(v) + 'W')
        _v = lambda p, v: (str(v) + 'V')
        _s = lambda p, v: (str(v) + 's')
        _x = lambda p, v: (str(v))

        self.dbusservice.add_path('/Ac/Energy/Forward', None, gettextcallback=_kwh)
        self.dbusservice.add_path('/Ac/L1/Current', None, gettextcallback=_a)
        self.dbusservice.add_path('/Ac/L1/Energy/Forward', None, gettextcallback=_kwh)
        self.dbusservice.add_path('/Ac/L1/Power', None, gettextcallback=_w)
        self.dbusservice.add_path('/Ac/L1/Voltage', None, gettextcallback=_v)
        self.dbusservice.add_path('/Ac/L2/Current', None, gettextcallback=_a)
        self.dbusservice.add_path('/Ac/L2/Energy/Forward', None, gettextcallback=_kwh)
        self.dbusservice.add_path('/Ac/L2/Power', None, gettextcallback=_w)
        self.dbusservice.add_path('/Ac/L2/Voltage', None, gettextcallback=_v)
        self.dbusservice.add_path('/Ac/L3/Current', None, gettextcallback=_a)
        self.dbusservice.add_path('/Ac/L3/Energy/Forward', None, gettextcallback=_kwh)
        self.dbusservice.add_path('/Ac/L3/Power', None, gettextcallback=_w)
        self.dbusservice.add_path('/Ac/L3/Voltage', None, gettextcallback=_v)
        self.dbusservice.add_path('/Ac/Power', None, gettextcallback=_w)
        self.dbusservice.add_path('/Ac/Current', None, gettextcallback=_a)
        self.dbusservice.add_path('/Ac/Voltage', None, gettextcallback=_v)

        self.dbusservice.add_path('/stats/connection_ok', 0, gettextcallback=_x, writeable=True)
        self.dbusservice.add_path('/stats/connection_error', 0, gettextcallback=_x, writeable=True)
        self.dbusservice.add_path('/stats/parse_error', 0, gettextcallback=_x, writeable=True)
        self.dbusservice.add_path('/stats/repeated_values', 0, gettextcallback=_x, writeable=True)
        self.dbusservice.add_path('/stats/last_connection_errors', 0, gettextcallback=_x, writeable=True)
        self.dbusservice.add_path('/stats/last_repeated_values', 0, gettextcallback=_x, writeable=True)
        self.dbusservice.add_path('/stats/reconnect', 0, gettextcallback=_x)
        self.dbusservice.add_path('/Mgmt/intervall', 1, gettextcallback=_s, writeable=True)

        # Explicitly register the DBus service
        try:
            self.dbusservice.register()
        except dbus.exceptions.DBusException as e:
            logging.error(f"Fehler bei der DBus-Registrierung: {e}")
            raise

    def __del__(self):
        if hasattr(self, 'dbusservice') and self.dbusservice is not None:
            try:
                logging.debug(f"Beende DBus-Dienst: {self.dbusservice.name}")
                self.dbusservice.__del__()  # Clean up DBus service
            except Exception as e:
                logging.error(f"Fehler beim Beenden des DBus-Dienstes: {e}")

    def invalidate(self):
        self.set('/Ac/L1/Power', [])
        self.set('/Ac/L2/Power', [])
        self.set('/Ac/L3/Power', [])
        self.set('/Ac/Power', [])

    def set(self, name, value, round_digits=0):
        logging.debug(f"Setze {name} auf {value}")
        if isinstance(value, float):
            self.dbusservice[name] = round(value, round_digits)
        else:
            self.dbusservice[name] = value

    def get(self, name):
        v = self.dbusservice[name]
        return v

    def inc(self, name):
        self.dbusservice[name] += 1
