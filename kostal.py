#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-

#vi: set autoindent noexpandtab tabstop=4 shiftwidth=4

import requests
from requests.auth import HTTPBasicAuth
import json
from ConfigParser import SafeConfigParser
from kostal_inverter import KostalInverter

from dbus.mainloop.glib import DBusGMainLoop
import gobject
from gobject import idle_add
import dbus
import dbus.service
import inspect
import pprint
import os
import sys
import threading
import time

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
	max_retries = 60

global demo
demo = 0
global kostal_is_init
kostal_is_init = 0
global dev_state
dev_state = DevState.WaitForDevice

def push_statistics() :
	global kostal

	kostal.set('/stats/connection_ok', Kostal.stats.connection_ok)
	kostal.set('/stats/connection_error', Kostal.stats.connection_ko)
	kostal.set('/stats/last_connection_errors', Kostal.stats.last_connection_errors)
	kostal.set('/stats/parse_error', Kostal.stats.parse_error)
	kostal.set('/stats/reconnect', Kostal.stats.reconnect)


def read_settings() :
	parser = SafeConfigParser()
	parser.read('kostal.ini')

	Kostal.ip = parser.get('KOSTAL', 'ip')
	#Kostal.url = parser.get('KOSTAL', 'url')
	#Kostal.statusurl = parser.get('KOSTAL', 'statusurl')
	Kostal.user = parser.get('KOSTAL', 'username')
	Kostal.password = parser.get('KOSTAL', 'password')
	Kostal.intervall = float(parser.get('KOSTAL', 'intervall'))

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

		#kostal.set('/Ac/L1/Energy/Forward', (data['EFAA']/1000))
		#kostal.set('/Ac/L2/Energy/Forward', (data['EFAB']/1000))
		#kostal.set('/Ac/L3/Energy/Forward', (data['EFAC']/1000))

		kostal.set('/Ac/Energy/Forward', (data['EFAT']/1000))

		powertotal = data['PT']
		print("++++++++++")
		print("POWER Phase A: " + str(data['PA']) + "W")
		print("POWER Phase B: " + str(data['PB']) + "W")
		print("POWER Phase C: " + str(data['PC']) + "W")
		print("POWER Total: " + str(data['PT']) + "W")
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

def kostal_htmltable_to_json( htmltext ) :
	htmltext = htmltext.encode('ascii','ignore')
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
			if (linenumber == 74):
				if line.endswith('</td>'):
					line = line[:-5]
				data['STATUS'] = line
			linenumber = linenumber + 1

		data['IA'] = data['PA'] / data['VA']
		data['IB'] = data['PB'] / data['VB']
		data['IC'] = data['PC'] / data['VC']
		data['IN0'] = data['IA'] + data['IB'] + data['IC']
	except:
		print('parsing error, using default values')
		Kostal.stats.parse_error += 1
		data['PT'] = 0
		data['PA'] = 0
		data['PB'] = 0
		data['PC'] = 0
		data['VA'] = 230
		data['VB'] = 230
		data['VC'] = 230
		data['EFAT'] = 1
		data['STATUS'] = 'Parse Error'
		data['IA'] = 0
		data['IB'] = 0
		data['IC'] = 0
		data['IN0'] = 0

	json_data = json.dumps(data)
	print(json_data)
	return data

def kostal_data_read_cb( jsonstr ) :
	kostal_parse_data ( jsonstr )
	return

def kostal_status_read_cb( jsonstr, init) :
	global kostal
	if init:
		kostal = KostalInverter('kostal_tcp_50','tcp:' + Kostal.ip, 50,'0',  'Kostal pico 5.5', '0.0','0.1')
		kostal.set('/Mgmt/intervall', Kostal.intervall, 1)
	return

def kostal_read_data() :
	global demo

	err = 0
	if demo == 0:
		try:
			response = requests.get( Kostal.ip, verify=False, auth=HTTPBasicAuth(Kostal.user, Kostal.password))
			# For successful API call, response code will be 200 (OK)
			if(response.ok):
				#print("code:"+ str(response.status_code))
				#print("******************")
				#print("headers:"+ str(response.headers))
				#print("******************")
				#print("content text:"+ str(response.text))
				#print("******************")
				Kostal.stats.connection_ok += 1
				Kostal.stats.last_connection_errors = 0
				jsonstr = kostal_htmltable_to_json(response.text) # not text
				kostal_data_read_cb( jsonstr = jsonstr )
				return 0
		except (requests.exceptions.HTTPError, requests.exceptions.RequestException):
			print('Error reading from ' + Kostal.ip)
			Kostal.stats.connection_ko += 1
			Kostal.stats.last_connection_errors += 1
			return 1
	else:
		#data = kostal_read_example("example_kostal_data.json")
		#Kostal.stats.connection_ok += 1
		#kostal_data_read_cb(data)
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
	run_event = threading.Event()
	run_event.set()

	update_thread = threading.Thread(target=kostal_update_cyclic, args=(run_event,))
	update_thread.start()

	gobject.threads_init()
	mainloop = gobject.MainLoop()
	mainloop.run()

except (KeyboardInterrupt, SystemExit):
	mainloop.quit()
	run_event.clear()
	update_thread.join()
	print("Host: KeyboardInterrupt")
