#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#vi: set autoindent noexpandtab tabstop=4 shiftwidth=4

import requests
from requests.auth import HTTPBasicAuth
import json
try:
	from ConfigParser import ConfigParser
except:
	from configparser import ConfigParser
from kostal_inverter import KostalInverter

from dbus.mainloop.glib import DBusGMainLoop
try:
	import gobject # used by victron
	from gobject import idle_add
except:
	from gi.repository import GObject as gobject
	from gi.repository import GLib

import dbus
import dbus.service
import inspect
import pprint
import os
import sys
import threading
import time
import traceback

from lxml import html
import lxml.etree
import re as regular_expression
from io import StringIO
import re 

class DevState:
	WaitForDevice = 0
	Connect = 1
	Connected = 2

class DevStatistics:
	connection_ok = 0
	connection_ko = 0
	parse_error = 0
	last_connection_errors = 0 # reset every ok read
	last_time = 0
	reconnect = 0

class Kostal:
	ip = []
	user = []
	password = []
	stats = DevStatistics
	intervall = []
	version = 1
	instance = 50
	max_retries = 10
	inverter_name = 'Kostal_pico5_5'

global demo
demo = 0
global kostal_is_init
kostal_is_init = 0
global dev_state
dev_state = DevState.WaitForDevice
global energy
energy = 0

def push_statistics() :
	global kostal

	kostal.set('/stats/connection_ok', Kostal.stats.connection_ok)
	kostal.set('/stats/connection_error', Kostal.stats.connection_ko)
	kostal.set('/stats/last_connection_errors', Kostal.stats.last_connection_errors)
	kostal.set('/stats/parse_error', Kostal.stats.parse_error)
	kostal.set('/stats/reconnect', Kostal.stats.reconnect)


def read_settings() :
	parser = ConfigParser()
	cfgname = 'kostal.ini'
	if len(sys.argv) > 1:
		cfgname = str(sys.argv[1])
	print('Using config: ' + cfgname)
	parser.read(cfgname)

	Kostal.ip = parser.get('KOSTAL', 'ip')
	Kostal.intervall = float(parser.get('KOSTAL', 'intervall'))
	Kostal.version = int(parser.get('KOSTAL', 'version'))

	if parser.has_option('KOSTAL', 'username'):
		Kostal.user = parser.get('KOSTAL', 'username')
	else:
		Kostal.user = ""

	if parser.has_option('KOSTAL', 'password'):
		Kostal.password = parser.get('KOSTAL', 'password')
	else:
		Kostal.password = ""

	if parser.has_option('KOSTAL', 'max_retries'):
		Kostal.max_retries = parser.get('KOSTAL', 'max_retries')

	if parser.has_option('KOSTAL', 'inverter_name'):
		Kostal.inverter_name = parser.get('KOSTAL', 'inverter_name')

	if parser.has_option('KOSTAL', 'instance'):
		Kostal.instance = int(parser.get('KOSTAL', 'instance'))
	
	if parser.has_option('KOSTAL', 'position'):
		Kostal.position = int(parser.get('KOSTAL', 'position'))
	else:
		Kostal.position = 0

def kostal_read_example(filename) :
	with open(filename) as f:
		data = json.load(f)
	#print(data)
	return data

def kostal_parse_data( data ) :
	global kostal, kostal_is_init

	# read same variables only the first time
	if kostal_is_init == 0:
		#kostal.set('/ProductName', str(jsonstr['hardware']))
		kostal_is_init = 1

	time_ms = int(round(time.time() * 1000))
	if Kostal.stats.last_time == time_ms:
		kostal.inc('/stats/repeated_values')
		kostal.inc('/stats/last_repeated_values')
		print('got repeated value')
	else:
		Kostal.stats.last_time = time_ms
		kostal.set('/stats/last_repeated_values', 0)

		kostal.set('/Ac/Power', (data['PT']))
		kostal.set('/Ac/Current', (data['IN0']), 1)
		kostal.set('/Ac/L1/Current', (data['IA']), 1)
		kostal.set('/Ac/L1/Voltage', (data['VA']))
		kostal.set('/Ac/L1/Power', (data['PA']))
		kostal.set('/Ac/L2/Current', (data['IB']), 1)
		kostal.set('/Ac/L2/Voltage', (data['VB']))
		kostal.set('/Ac/L2/Power', (data['PB']))
		kostal.set('/Ac/L3/Current', (data['IC']), 1)
		kostal.set('/Ac/L3/Voltage', (data['VC']))
		kostal.set('/Ac/L3/Power', (data['PC']))

		kostal.set('/Ac/Energy/Forward', (data['EFAT']), 2)

		powertotal = data['PT']
		print("++++++++++")
		print("POWER Phase A: " + str(data['PA']) + "W")
		print("POWER Phase B: " + str(data['PB']) + "W")
		print("POWER Phase C: " + str(data['PC']) + "W")
		print("POWER Total: " + str(data['PT']) + "W")
		print("ENERGY Total: " + str(round(data['EFAT'], 0)) + "kWh")
		#print("Time: " + str(data['TIME']) + "ms")
		print("KOSTAL Status: " + str(data['STATUS']))

def kostal_get_table_data_float(tree, xstring):
	return float(kostal_get_table_data(tree, xstring))

		#Kostal.stats.parse_error += 1
def kostal_get_table_data(tree, xstring):
	s = tree.xpath(xstring)[0].text_content()
	s = s.strip().replace(" ", "")
	s = s.split('\n')
	return s[0]

def kostal_read_power_value(string):
	val = 1
	multi = 1
	valstring = re.sub(r'<.+?>','', string)
	#print("Short: " + valstring)
	if valstring.endswith('kW'):
		multi = 1000
	elif valstring.endswith('W'):
		multi = 1
	else:
		print('Did not find value')

	valstring = re.sub('[a-zA-Z.]', '', valstring)
	valstring = valstring.replace(',','.')
	print('short: ' + valstring)
	val = float(valstring)
	return val * multi

def kostal_htmltable_to_json( htmltext ) :
	global energy
	htmltext = htmltext.encode('ascii','ignore').decode('utf-8')
	#tree = lxml.html.document_fromstring(htmltext)
	#print(tree)

	#print('Energie: ' + kostal_get_table_data(tree, '//table[2]//tr[4]/td[6]'))
	#print('Energie:         ' + kostal_get_table_data(tree,'.//table[2]//tr[4]/td[6]'))
	#print('Leistung gesamt: ' + kostal_get_table_data(tree,'.//table[2]//tr[4]/td[3]'))
	#print('Leistung L1: '     + kostal_get_table_data(tree,'.//table[2]//tr[16]/td[6]'))
	#print('Spannung L1: '     + kostal_get_table_data(tree,'.//table[2]//tr[14]/td[6]'))
	#print('Strom    L1: '     + kostal_get_table_data(tree,'.//table[2]//tr[14]/td[6]'))
	#print('Leistung L2: '     + kostal_get_table_data(tree,'.//table[2]//tr[21]/td[6]'))
	#print('Spannung L2: '     + kostal_get_table_data(tree,'.//table[2]//tr[19]/td[6]'))
	#print('Strom    L3: '     + kostal_get_table_data(tree,'.//table[2]//tr[19]/td[6]'))
	#print('Leistung L3: '     + kostal_get_table_data(tree,'.//table[2]//tr[26]/td[6]'))
	#print('Spannung L3: '     + kostal_get_table_data(tree,'.//table[2]//tr[24]/td[6]'))
	#print('Strom    L3: '     + kostal_get_table_data(tree,'.//table[2]//tr[24]/td[6]'))
	#print('Status     : '     + kostal_get_table_data(tree,'.//table[2]//tr[8]/td[3]'))

	#print("The original string : " + htmltext)	
	#res = [float(i) for i in htmltext.split() if i.isdigit()]
	#print(htmltext.split())
	#print("List: " + htmltext.split())

	data = {}
	try:
		linenumber = 1
		for line in htmltext.split("\n"):
			if (linenumber == 46):
				data['PT'] = int((re.findall('\d+', line))[0]);
			if (linenumber == 128):
				data['PA'] = int((re.findall('\d+', line))[0]);
			if (linenumber == 114):
				data['VA'] = int((re.findall('\d+', line))[0]);
			if (linenumber == 167):
				data['PB'] = int((re.findall('\d+', line))[0]);
			if (linenumber == 153):
				print (re.findall('\d+', line))
				data['VB'] = int((re.findall('\d+', line))[0]);
			if (linenumber == 208):
				data['PC'] = int((re.findall('\d+', line))[0]);
			if (linenumber == 193):
				data['VC'] = int((re.findall('\d+', line))[0]);
			if (linenumber == 51):
				data['EFAT'] = int((re.findall('\d+', line))[0]);
				energy = data['EFAT']
			if (linenumber == 74):
				if line.endswith('</td>'):
					line = line[:-5]
				data['STATUS'] = line
			linenumber = linenumber + 1

		data['IA'] = round(data['PA'] / float(data['VA']),1)
		data['IB'] = round(data['PB'] / float(data['VB']),1)
		data['IC'] = round(data['PC'] / float(data['VC']),1)
		data['IN0'] =round( data['IA'] + data['IB'] + data['IC'], 1)
	except Exception as e:
		print(str(e))
		print('parsing error, using default values for version ' + str(Kostal.version) + ' at ' + str(linenumber))
		Kostal.stats.parse_error += 1
		data['PT'] = 0
		data['PA'] = 0
		data['PB'] = 0
		data['PC'] = 0
		data['VA'] = 230
		data['VB'] = 230
		data['VC'] = 230
		data['EFAT'] = energy
		data['STATUS'] = 'Parse Error'
		data['IA'] = 0
		data['IB'] = 0
		data['IC'] = 0
		data['IN0'] = 0

	json_data = json.dumps(data)
	print(json_data)
	return data

def kostal_v2_to_v1_json(xml):
	#print("++++")
	#print(xml)
	#print("----")
	xml = bytes(bytearray(xml, encoding = 'utf-8'))
	el = lxml.etree.XML(xml);
	print("%%%%")
	meas = el.findall('.//Measurement[@Type="AC_Power"]')
	
	data = {}
	try:
		meas = el.findall('.//Measurement[@Type="AC_Power"]')
		data['PA'] = round(float(meas[0].attrib.get('Value')), 1)
		meas = el.findall('.//Measurement[@Type="AC_Voltage"]')
		data['VA'] = round(float(meas[0].attrib.get('Value')), 1)
		meas = el.findall('.//Measurement[@Type="AC_Current"]')
		data['IA'] = round(float(meas[0].attrib.get('Value')), 1)
		data['STATUS'] = 'running'
	except:
		data['PA'] = 0
		data['VA'] = 0
		data['IA'] = 0
		data['STATUS'] = 'standby'

	data['PB'] = 0
	data['PC'] = 0
	data['PT'] = data['PA']
	data['VB'] = 0
	data['VC'] = 0
	data['EFAT'] = 0
	data['IB'] = 0
	data['IC'] = 0
	data['IN0'] = 0

	print(data)
	return data

def kostal_v3_to_v1_json(js):
	data = {}
	data['PT'] = round( float(js['dxsEntries'][0]['value']), 1)
	data['VA'] = round( float(js['dxsEntries'][1]['value']), 1)
	data['PA'] = round( float(js['dxsEntries'][2]['value']), 1)
	data['VB'] = round( float(js['dxsEntries'][3]['value']), 1)
	data['PB'] = round( float(js['dxsEntries'][4]['value']), 1)
	data['VC'] = round( float(js['dxsEntries'][5]['value']), 1)
	data['PC'] = round( float(js['dxsEntries'][6]['value']), 1)
	data['EFAT'] = round( float(js['dxsEntries'][7]['value']) / 1000, 3) # as produced power per day has to convered from Wh to kWh
	data['STATUS'] = js['dxsEntries'][8]['value']
	data['IA'] = 0.0
	data['IB'] = 0.0
	data['IC'] = 0.0

	if 0 != data['VA']:
		data['IA'] = round(data['PA'] / data['VA'], 1)

	if 0 != data['VB']:
		data['IB'] = round(data['PB'] / data['VB'], 1)

	if 0 != data['VC']:
		data['IC'] = round(data['PC'] / data['VC'], 1)

	data['IN0'] = round( data['IA'] + data['IB'] + data['IC'], 1)

	print(data)
	return data


def evcc_to_v1_json(js):
	global energy
	power = js['result']['pvPower']
	print(f"pvpower: {power}")

	energy = energy + power * kostal.get('/Mgmt/intervall') / 3600 / 1000 # kWh

	data = {}
	data['PT'] = round(power, 0)
	data['VA'] = 230
	data['PA'] = round(power, 0)
	data['VB'] = 0
	data['PB'] = 0
	data['VC'] = 0
	data['PC'] = 0
	data['EFAT'] = round(energy, 3)
	data['STATUS'] = 0
	data['IA'] = 0
	data['IB'] = 0.0
	data['IC'] = 0.0

	if 0 != data['VA']:
		data['IA'] = round(data['PA'] / data['VA'], 1)

	if 0 != data['VB']:
		data['IB'] = round(data['PB'] / data['VB'], 1)

	if 0 != data['VC']:
		data['IC'] = round(data['PC'] / data['VC'], 1)

	data['IN0'] = round( data['IA'] + data['IB'] + data['IC'], 1)

	print(data)
	return data

def kostal_data_read_cb( jsonstr ) :
	kostal_parse_data ( jsonstr )
	return

def kostal_status_read_cb( jsonstr, init) :
	global kostal
	if init:
		kostal = KostalInverter(Kostal.inverter_name,'tcp:' + Kostal.ip, Kostal.instance,'0',  Kostal.inverter_name, '0.0','0.1', Kostal.position)
		kostal.set('/Mgmt/intervall', Kostal.intervall, 1)
	return

def kostal_read_data() :
	global demo

	err = 0
	if demo == 0:
		try:
			if (Kostal.user != ""):
				response = requests.get( Kostal.ip, verify=False, auth=HTTPBasicAuth(Kostal.user, Kostal.password), timeout=10)
			else:
				print('requested no login')
				if Kostal.version == 1:
					response = requests.get( Kostal.ip, verify=False, timeout=10)
				elif Kostal.version == 2:
					print("version2")
					response = requests.get( Kostal.ip + '/measurements.xml', verify=False, timeout=10)
				elif Kostal.version == 3:
					response = requests.get( Kostal.ip +  '/api/dxs.json?dxsEntries=67109120&dxsEntries=67109378&dxsEntries=67109379&dxsEntries=67109634&dxsEntries=67109635&dxsEntries=67109890&dxsEntries=67109891&dxsEntries=251658754&dxsEntries=16780032', verify=False, timeout=10) # 192.168.178.51/api/dxs.json?dxsEntries=251658754 gets the prouced power of the day
				elif Kostal.version == 80: # evcc
					response = requests.get( Kostal.ip +  '/api/state', verify=False, timeout=10)
				else:
					print("unknown version")
					quit()
					return
			if(response.ok and len(response.text)):
				#print("code:"+ str(response.status_code))
				#print("******************")
				#print("headers:"+ str(response.headers))
				#print("******************")
				#print("content text:"+ str(response.text))
				#print("******************")
				Kostal.stats.connection_ok += 1
				Kostal.stats.last_connection_errors = 0
				if Kostal.version == 1:
					jsonstr = kostal_htmltable_to_json(response.text)
					kostal_data_read_cb( jsonstr = jsonstr )
				elif Kostal.version == 2:
					jsonstr = kostal_v2_to_v1_json(response.text)
					kostal_data_read_cb( jsonstr = jsonstr )
					return
				elif Kostal.version == 3:
					jsonstr = kostal_v3_to_v1_json(response.json())
					kostal_data_read_cb( jsonstr = jsonstr )
				elif Kostal.version == 80: # evcc
					jsonstr = evcc_to_v1_json(response.json())
					kostal_data_read_cb( jsonstr = jsonstr )
				else:
					print("unknown version")
					quit()
				return 0
			else:
				print('Could not read page, error ' + str(response.status_code))
				return 1
		except (requests.exceptions.HTTPError, requests.exceptions.RequestException):
			print('Error reading from ' + Kostal.ip)
			traceback.print_exc()
			Kostal.stats.connection_ko += 1
			Kostal.stats.last_connection_errors += 1
			return 1
	else:
		data = kostal_v3_to_v1_json(kostal_read_example("example_kostal_data.json"))
		Kostal.stats.connection_ok += 1
		kostal_data_read_cb(data)
		return 0
	return 0

def kostal_read_status(init) :
	global demo

	ret = kostal_read_data()
	return ret

def kostal_update_cyclic(run_event) :
	global dev_state, kostal

	while run_event.is_set():
		print("Thread: doing")
		if dev_state > DevState.WaitForDevice:
			push_statistics()
			intervall = kostal.get('/Mgmt/intervall')
		else:
			intervall = Kostal.intervall

		if Kostal.stats.last_connection_errors > Kostal.max_retries:
			print('Lost connection to kostal, reset')
			dev_state = DevState.Connect
			Kostal.stats.last_connection_errors = 0
			Kostal.stats.reconnect += 1
			kostal.set('/Connected', 0)
			kostal.set('/Ac/L1/Current', None)
			kostal.set('/Ac/L2/Current', None)
			kostal.set('/Ac/L3/Current', None)
			kostal.set('/Ac/L1/Power', None)
			kostal.set('/Ac/L2/Power', None)
			kostal.set('/Ac/L3/Power', None)
			kostal.set('/Ac/L1/Voltage', None)
			kostal.set('/Ac/L2/Voltage', None)
			kostal.set('/Ac/L3/Voltage', None)
			kostal.set('/Ac/Power', None)
			kostal.set('/Ac/Current', None)
			kostal.set('/Ac/Voltage', None)
			kostal.set('/Ac/Energy/Forward', 2)

		if dev_state == DevState.WaitForDevice:
			if kostal_read_status(init=1) == 0:
				dev_state = DevState.Connect
		elif dev_state == DevState.Connect:
			if kostal_read_status(init=0) == 0:
				dev_state = DevState.Connected
				kostal.set('/Connected', 1)
		elif dev_state == DevState.Connected:
			kostal_read_data()
		else:
			dev_state = DevState.WaitForDevice

		time.sleep(intervall)
	return

DBusGMainLoop(set_as_default=True)
read_settings()
print("Using " + Kostal.ip + " user: " + Kostal.user)
kostal_status_read_cb("", init = 1)

try:
	import socket
	run_event = threading.Event()
	run_event.set()

	socket.setdefaulttimeout(10)
	update_thread = threading.Thread(target=kostal_update_cyclic, args=(run_event,))
	update_thread.start()

	mainloop = GLib.MainLoop()
	mainloop.run()

except (KeyboardInterrupt, SystemExit):
	mainloop.quit()
	run_event.clear()
	update_thread.join()
	print("Host: KeyboardInterrupt")
