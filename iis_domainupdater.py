#!/usr/bin/python
import socket, ssl, re, sys
from threading import *
from os import _exit
from os.path import isfile
from time import sleep, time, strftime
from urllib import urlencode, quote_plus
from getpass import getpass

## = Added the stdout redirect to simplify the output to a log file
## = in case you run this script as a cron job (which, is a good idea)
sys.stdout = open('/var/log/iis_domainupdater.log', 'ab')

__date__ = '2012-12-04 23:35 CET'
__version__ = 0.2
__author__ = 'Anton Hvornum - http://www.linkedin.com/profile/view?id=140957723'

## ================== Explanation of the different variables ===================
## ==                                                                         ==
## = __customerID__ - It's the customer ID number you've recieved from iis,    =
## =                  normally it's just a 8 digit number, we'll use it as     =
## =                  a username when we authenticate.                         =
## = __customerPWD__ - This is your password belonging to __customerID__       =
## = __domain__ - Which domain are you trying to update? we need this to find  =
## =              the domain-id that iis has given you.                        =
## = __nsserver__ - Which nameserver do you want to update the IP of?          =
## =                normally there should be at least 2 name-servers for each  =
## =                domain, and they should be on different servers so in      =
## =                order for the script to update the correct nameserver,     =
## =                enter the nameserver that this script will run on.         =
## = __externalIP__ - It's as simple as to what is your external IP?           =
## =                  The script will try to determain the extnernal IP for    =
## =                  you but if you want, you can always make it static here. =
## =============================================================================

print strftime('%Y-%m-%d %H:%M:%S - Initated the script')
sys.stdout.flush()

__customerID__ = None
__customerPWD__ = None # example: r'this\is&a%super;password' escapes %s etc
__domain__ = None
__nsserver__ = None
__externalIP__ = None

## == These are values that we'll scan for later on, so do not set these!
## == (unless you know what you're doing!)
__domainid__ = -1
__nameserverID__ = None
__lastknown__ = None

def refstr(s):
	while len(s) > 1 and s[0] in (' ', '	', ':', ',', '\r', '\n', '"', "'"):
		s = s[1:]
	while len(s) > 1 and s[-1] in (' ', '	', ':', ',', '\r', '\n', '"', "'"):
		s = s[:-1]
	return s

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
			return ret	
	return ret

def getCurrentIp(data):
	inpnamepos = data.find('name="update_ip"')
	valuestart = data.find('value="',inpnamepos)+7
	valueend = data.find('"', valuestart+2)
	return refstr(data[valuestart:valueend])


## == Quick explanation of the syntax of the dictionary data,
## == the data is passed to the http class as http.htmldata
## == when you later on call http.navigate() the function
## == will take the dictionary you've supplied and build it to
## == standard HTTP formated data.
## == host, target and type must be present at all times,
## == form is optional unless you make the type - 'POST', then it's required.
## ==
## == Here are three basic HTTP dictionaries we can pass to http().htmldata
## == and which will simulate the actual login process (click for click):

base = {
		'host' : 'domanhanteraren.iis.se',
		'target' : '/',
		'type' : 'GET',
		'form' : {},
}

logindata = {
			'host' : 'domanhanteraren.iis.se',
			'target' : '/start/login',
			'type' : 'POST',
			'form' : {'username' : __customerID__,
						'password' : __customerPWD__,
						'login' : 'Logga in'}
			}

getdomains = {
		'host' : 'domanhanteraren.iis.se',
		'target' : '/domains',
		'type' : 'GET',
		'form' : {},
}


## == Lets begin the process of signing in, getting the required ID's and
## == then last but not least, update the IP (if nessescary, otherwise end)


print ' - Imitating login navigation and submission'
sys.stdout.flush()
http = httplib(base)
headers, data = http.navigate()

if 'maintenance' in data.lower():
	print ' - IIS.se is undergoing maintenance, ending the script'
	sys.stdout.flush()
	_exit(0)

http.htmldata = logindata
http.navigate()

print ' - Imitating update process and fetching ID values'
sys.stdout.flush()

if __domainid__ == -1:
	http.htmldata = getdomains
	domaindata = getdomain(http.navigate()[1])
	print ' - Got new ID for ' + domaindata['title'] + ', the ID is ' + domaindata['id']
	sys.stdout.flush()
	__domainid__ = domaindata['id']

getdomainviaid = {
		'host' : 'domanhanteraren.iis.se',
		'target' : '/domains/details/nameservers?id=' + __domainid__,
		'type' : 'GET',
		'form' : {},
}
http.htmldata = getdomainviaid
headers, data = http.navigate()
nameserverdata = getediturl(data)
__nameserverID__ = nameserverdata['hid']

geteditpage = {
		'host' : 'domanhanteraren.iis.se',
		'target' : '/domains/details/editns?' + 'id=' + __domainid__ + '&hid=' + __nameserverID__,
		'type' : 'GET',
		'form' : {},
}

http.htmldata = geteditpage
headers, data = http.navigate()
updatedata = getUpdateID(data)
__updateid__ = updatedata['upd_id']

getupdatenameserverpage = {
		'host' : 'domanhanteraren.iis.se',
		'target' : '/domains/details/editns/updateip?' + 'id=' + __domainid__ + '&hid=' + __nameserverID__ + '&upd_id=' + __updateid__,
		'type' : 'GET',
		'form' : {},
}

print ' - Finding current IP at iis.se and imitating update process'
sys.stdout.flush()

http.htmldata = getupdatenameserverpage
headers, data = http.navigate()

updatedata = {
			'host' : 'domanhanteraren.iis.se',
			'target' : '/domains/details/editns/updateip',
			'type' : 'POST',
			'form' : {'id' : __domainid__, 'hid' : __nameserverID__, 'upd_id' : __updateid__, 'update_ip' : __externalIP__, 'update' : 'Uppdatera'}
			}

currentRegisteredIp = getCurrentIp(data)
if __externalIP__ == currentRegisteredIp:
	print ' - Skipping update, external IP is the regisitrered IP at iis.se'
	sys.stdout.flush()
else:
	print ' - Updating nameserver ' + __nsserver__ + ' to ' + __externalIP__
	sys.stdout.flush()
	http.htmldata = updatedata
	headers, data = http.navigate()

	#f=open('dump.html', 'wb')
	#f.write(data)
	#f.close()

if __externalIP__:
	f = open('lastknown_ip_iis.conf', 'wb')
	f.write(__externalIP__)
	f.close()

for t in enumerate():
	try:
		t._Thread__delete()
	except:
		pass
_exit(0)
