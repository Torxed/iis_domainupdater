#!/usr/bin/python
import socket, ssl, re, sys
from threading import *
from os import _exit
from os.path import isfile
from time import sleep, time, strftime
from urllib import urlencode, quote_plus
from getpass import getpass
from logger import log

## = Added the stdout redirect to simplify the output to a log file
## = in case you run this script as a cron job (which, is a good idea)
sys.stdout = open('/var/log/iis_domainupdater.log', 'ab')

__date__ = '2012-06-12 00:20 CET'
__version__ = '0.3.1'
__author__ = 'Anton Hvornum - http://www.linkedin.com/profile/view?id=140957723'

print strftime('%Y-%m-%d %H:%M:%S - Initated the script')
sys.stdout.flush()

if isfile('config.py'):
	from config import *
else:
	## =============== Change these in: config.py !!!
	##
	__customerID__, __customerPWD__, __domain__ = (None, None, None)
	__externalIP__, __nsserver__, __lastknown__ = (None, None, None)

## == These are values that we'll scan for later on, so do not set these!
## == (unless you know what you're doing!)
__domainid__ = -1
__nameserverID__ = None

def refstr(s):
	return s.strip(" \t:,\r\n\"'")

if not __customerID__ and not __customerPWD__:
	print ' * Note:  You can always set \'__customerID__\' (and \'__customerPWD__\')'
	sys.stdout.flush()
if not __customerID__:
	__customerID__ = refstr(raw_input('Enter your IIS customer number (ex 12345678): '))
if not __customerPWD__:
	__customerPWD__ = getpass()
if not __domain__:
	__domain__ = refstr(raw_input('Enter your domainname to update (example.se): '))
if not __nsserver__:
	__nsserver__ = refstr(raw_input('Enter the nameserver to update (ns1.example.se): '))
if not __externalIP__:
	s = socket.socket()
	s.connect(('automation.whatismyip.com', 80))
	s.send('GET /n09230945.asp HTTP/1.1\r\nHost: automation.whatismyip.com\r\n\r\n')
	ips = re.findall(r'[0-9]+(?:\.[0-9]+){3}', s.recv(8192))
	s.close()
	if type(ips) == list and len(ips) == 1:
		__externalIP__ = refstr(str(ips[0]))
	else:
		__externalIP__ = refstr(str(ips))
	print ' - Got external IP: ' + str(__externalIP__)
	sys.stdout.flush()
if isfile('lastknown_ip_iis.conf'):
	f = open('lastknown_ip_iis.conf', 'rb')
	__lastknown__ = refstr(f.read())
	f.close()
if __lastknown__ and __lastknown__ == __externalIP__:
	print ' - External IP matches the last known IP on IIS.se, ending the script'
	sys.stdout.flush()
	_exit(0)

class nonblockingrecieve(Thread):
	def __init__(self, sock):
		self.sock = sock
		self.data = ''
		self.lastupdate = time()
		Thread.__init__(self)
		self.start()

	def run(self):
		while True:
			d = self.sock.read()
			if not d:
				break
			self.data += d
			self.lastupdate = time()

class httplib():
	def __init__(self, htmldata):
		self.htmldata = htmldata
		self.sock = None
		self.cookies = {}
		self.lasturl = 'https://' + self.htmldata['host'] + '/'

	def connect(self):
		if not self.sock:
			s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			self.sock = ssl.wrap_socket(s)
			self.sock.connect((self.htmldata['host'], 443))

	def eatcookie(self, data):
		cookie, trash = data.split(';',1)
		name, value = cookie.split('=',1)
		self.cookies[name] = value

	def parse(self, data):
		headers = {}
		if not '\r\n\r\n' in data:
			print 'Bad data:',[data]
			sys.stdout.flush()
			return None, None
		head, data = data.split('\r\n\r\n',1)
		for row in head.split('\r\n'):
			if len(row) <= 0: continue
			if not ':' in row: continue # most likely HTTP/1.1 status code
			k, v = row.split(':',1)
			k, v = refstr(k).lower(), refstr(v)
			if k == 'set-cookie':
				self.eatcookie(v)
			else:
				headers[k] = v
		return headers, data

	def sendrecieve(self, data):
		self.connect()
		self.sock.write(data)
		datahandle = nonblockingrecieve(self.sock)
		loops = 0
		last = 'X'
		data = ''
		while loops <= 10 and time() - datahandle.lastupdate:
			d = datahandle.data
			if d != last:
				loops = 0
				data = d
				last = data
				if '</html>' in data.lower():
					break
			else:
				loops += 1
			sleep(0.25)
		del last
		del loops
		try:
			datahandle._Thread__stop()
		except:
			pass
		try:
			datahandle._Thread__delete()
		except:
			pass

		self.disconnect()
		return data

	def disconnect(self):
		self.sock.close()
		self.sock = None

	def postformat(self):
		outdata = ''
		for k, v in self.htmldata['form'].items():
			outdata += k + '=' + quote_plus(v) + '&'
		outdata = outdata[:-1]
		return outdata

	def navigate(self):
		if 'inform' in self.htmldata and self.htmldata['inform']:
			log(self.htmldata['inform'])
		outdata = ''
		postdata = None

		if self.htmldata['type'] == 'GET':
			#print ' * Getting ' + self.htmldata['target']
			outdata += 'GET ' + self.htmldata['target'] + ' HTTP/1.1\r\n'
		else:
			outdata += 'POST ' + self.htmldata['target'] + ' HTTP/1.1\r\n'
			postdata = self.postformat()
			if not postdata:
				print 'Problem formatting the POST data'
				sys.stdout.flush()
				return None
			outdata += 'Content-Length: ' + str(len(postdata)) + '\r\n'
			outdata += 'Content-Type: application/x-www-form-urlencoded\r\n'
			outdata += 'Referer: https://' + self.htmldata['host'] + self.htmldata['target'] + '\r\n'

		outdata += 'Host: ' + self.htmldata['host'] + '\r\n'
		if len(self.cookies) > 0:
			outdata += 'Cookie: '
			for cookie, value in self.cookies.items():
				outdata += cookie + '=' + value + '; '
			outdata = outdata[:-2] + '\r\n'

		outdata += 'Accept-Encoding: text\r\n'
		outdata += 'User-Agent: Autoupdater/0.1 (X11; Linux i686) Own/20121204 AutoUpdater/0.1\r\n'
		outdata += 'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8\r\n'
		outdata += 'Connection: keep-alive\r\n'
		outdata += '\r\n'
		if postdata:
			outdata += postdata

		data = self.sendrecieve(outdata)

		headers, data = self.parse(data)
		if headers:
			if 'location' in headers:
				self.htmldata['type'] = 'GET'
				self.lastupdate = 'https://' + self.htmldata['host'] + self.htmldata['target']
				self.htmldata['target'] = headers['location']
				self.navigate()
			else:
				self.lastupdate = 'https://' + self.htmldata['host'] + self.htmldata['target']
		return headers, data

def getdomain(data):
	retmap = {}

	dompos = data.find(__domain__ + '</a>')
	start = data.rfind('<a',0,dompos)
	end = data.rfind('>', 0, dompos)

	link = data[start:end]
	link = link.split(' ')

	for val in link:
		if not '=' in val: continue

		key, val = val.split('=',1)
		key, val = refstr(key), refstr(val)

		if key == 'href' and 'id' in val:
			crap, _id = val.split('id=',1)
			retmap['id'] = _id
		else:
			retmap[key] = val
	log(' - Got new ID for ' + retmap['title'] + ', the ID is ' + retmap['id'])
	__domainid__ = domaindata['id']
	return retmap

def getediturl(data):
	nameservpos = data.find(__nsserver__)
	start = data.rfind('<a', 0,nameservpos)
	end = data.rfind('>', 0,nameservpos)

	link = data[start:end]
	link = link.split(' ')

	ret = {}

	for val in link:
		if not '=' in val: continue

		key, val = val.split('=',1)
		key, val = refstr(key), refstr(val)

		if key == 'href':
			crap, values = val.split('?',1)
			for values in values.split('&'):
				if '=' in values:
					k, v = values.split('=',1)
					k, v = refstr(k), refstr(v)
					ret[k] = v
			__nameserverID__ = ret['hid']
			return ret

def getUpdateID(data):
	nameservpos = data.lower().find('uppdatera</a>')
	start = data.rfind('<a', 0,nameservpos)
	end = data.rfind('>', 0,nameservpos)

	link = data[start:end]
	link = link.split(' ')

	ret = {}

	for val in link:
		if not '=' in val: continue

		key, val = val.split('=',1)
		key, val = refstr(key), refstr(val)

		if key == 'href':
			crap, values = val.split('?',1)
			for values in values.split('&'):
				if '=' in values:
					k, v = values.split('=',1)
					k, v = refstr(k), refstr(v)
					ret[k] = v
			__updateid__ = ret['upd_id']
			return ret	

def getCurrentIp(data):
	inpnamepos = data.find('name="update_ip"')
	valuestart = data.find('value="',inpnamepos)+7
	valueend = data.find('"', valuestart+2)
	f = open('lastknown_ip_iis.conf', 'wb')
	f.write(data[valuestart:valueend])
	f.close()
	return refstr(data[valuestart:valueend])

class pages():
	def __init__(self):
		pass
	def root(self):
		return {
				'host' : 'domanhanteraren.iis.se',
				'target' : '/',
				'type' : 'GET',
				'form' : {},
				'inform' : ' - Imitating login navigation',
				}

	def loginpage(self):
		return {
				'host' : 'domanhanteraren.iis.se',
				'target' : '/start/login',
				'type' : 'POST',
				'form' : {'username' : __customerID__,
							'password' : __customerPWD__,
							'login' : 'Logga in'},
				'inform' : ' - Sending logininformation',
				}
	def getdomains(self):
		return {
				'host' : 'domanhanteraren.iis.se',
				'target' : '/domains',
				'type' : 'GET',
				'form' : {},
				'inform' : ' - Getting domainname ID',
				}
	def getnameservers(self):
		return {
				'host' : 'domanhanteraren.iis.se',
				'target' : '/domains/details/nameservers?id=' + __domainid__,
				'type' : 'GET',
				'form' : {},
				'inform' : ' - Getting nameserver ID',
				}

	def geteditnameserver(self):
		return {
				'host' : 'domanhanteraren.iis.se',
				'target' : '/domains/details/editns?' + 'id=' + __domainid__ + '&hid=' + __nameserverID__,
				'type' : 'GET',
				'form' : {},
				'inform' : ' - Getting IP edit link ID',
				}

	def getcurrentiponnameserver(self):
		return {
				'host' : 'domanhanteraren.iis.se',
				'target' : '/domains/details/editns/updateip?' + 'id=' + __domainid__ + '&hid=' + __nameserverID__ + '&upd_id=' + __updateid__,
				'type' : 'GET',
				'form' : {},
				'inform' : ' - Finding current IP at iis.se',
				}
	def updatedata(self):
		return {
				'host' : 'domanhanteraren.iis.se',
				'target' : '/domains/details/editns/updateip',
				'type' : 'POST',
				'form' : {'id' : __domainid__, 'hid' : __nameserverID__, 'upd_id' : __updateid__, 'update_ip' : __externalIP__, 'update' : 'Uppdatera'},
				'inform' : ' - Updating the IP on iis.se to ' + __externalIP__,
				}

## Pages is a class to build and return
## dictionary data used by the .navigate() function.
pages = Pages()

http = httplib(pages.root())
if 'maintenance' in http.navigate()[1]: # in data, headers = [0]
	log(' - IIS.se is undergoing maintenance, ending the script', True)

http.htmldata = pages.loginpage()
http.navigate()

if __domainid__ == -1:
	http.htmldata = pages.getdomains()
	getdomain(http.navigate()[1])

http.htmldata = pages.getnameservers()
getediturl(http.navigate()[1])

http.htmldata = pages.geteditnameserver()
getUpdateID(http.navigate()[1])

http.htmldata = pages.getcurrentiponnameserver()
currentRegisteredIp = getCurrentIp(http.navigate()[1])
if __externalIP__ == currentRegisteredIp:
	log(' - Skipping update, external IP is the regisitrered IP at iis.se', True)
else:
	http.htmldata = pages.updatedata()
	http.navigate()

for t in enumerate():
	try:
		t._Thread__delete()
	except:
		pass
_exit(0)
