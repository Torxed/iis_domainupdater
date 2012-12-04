import socket, ssl
from sys import argv
from threading import *
from os import _exit
from time import sleep, time, strftime
from urllib import urlencode, quote_plus
from getpass import getpass

__version__ = 0.1
__author__ = 'Anton Hvornum <antonATgmail>'
__customerID__ = '13019837'
# == Feel free to set __customerPWD__ in order for the script to
# == skip asking you for a password, taking sys.argv[1] is a bad idea
# == unless you're sure how to pass all those special characters in your
# == password to the python interpretater.
# == (Because you do have a strong password right with & and \)
__customerPWD__ = None
if not __customerPWD__:
	__customerPWD__ = getpass()
__nsserver__ = 'ns1.hvornum.se'
__nameserverID__ = None
__domain__ = 'hvornum.se'
__domainid__ = -1
__externalIP__ = '85.227.193.213'

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
			'form' : {'username' : __customerID__, 'password' : __customerPWD__, 'login' : 'Logga in'}
			}

getdomains = {
		'host' : 'domanhanteraren.iis.se',
		'target' : '/domains',
		'type' : 'GET',
		'form' : {},
}

def refstr(s):
	while len(s) > 1 and s[0] in (' ', '	', ':', ',', '\r', '\n', '"', "'"):
		s = s[1:]
	while len(s) > 1 and s[-1] in (' ', '	', ':', ',', '\r', '\n', '"', "'"):
		s = s[:-1]
	return s

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
		#									ca_certs="/etc/ca_certs_file",
		#									cert_reqs=ssl.CERT_REQUIRED)

			self.sock.connect((self.htmldata['host'], 443))

		#	print repr(self.sock.getpeername())
		#	print self.sock.cipher()
		#	print str(self.sock.getpeercert())

	def eatcookie(self, data):
		cookie, trash = data.split(';',1)
		name, value = cookie.split('=',1)
		self.cookies[name] = value

	def parse(self, data):
		headers = {}
		if not '\r\n\r\n' in data:
			print 'Bad data:',[data]
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
		#outdata = ''
		#if len(self.htmldata['form']) > 0:
		#	for k, v in self.htmldata['form'].items():
		#		outdata += k +'='+ v + '&'
		#	outdata = outdata[:-1]

		outdata = ''
		for k, v in self.htmldata['form'].items():
			outdata += k + '=' + quote_plus(v) + '&'
		outdata = outdata[:-1]

		# urlencode takes a dictionary {'key' : 'val'}
		# and transforms it into a key=val&... string.
		# quote_plus then takes that string and escapes all
		# characters such as %, " ", etc into html friendly things.
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

print ' - Imitating login navigation and submission'
http = httplib(base)
http.navigate()

http.htmldata = logindata
http.navigate()

print ' - Imitating update process and fetching ID values'

if __domainid__ == -1:
	http.htmldata = getdomains
	domaindata = getdomain(http.navigate()[1])
	print ' - Got new ID for ' + domaindata['title'] + ', the ID is ' + domaindata['id']
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

http.htmldata = getupdatenameserverpage
headers, data = http.navigate()

updatedata = {
			'host' : 'domanhanteraren.iis.se',
			'target' : '/domains/details/editns/updateip',
			'type' : 'POST',
			'form' : {'id' : __domainid__, 'hid' : __nameserverID__, 'upd_id' : __updateid__, 'update_ip' : __externalIP__, 'update' : 'Uppdatera'}
			}

def getCurrentIp(data):
	inpnamepos = data.find('name="update_ip"')
	valuestart = data.find('value="',inpnamepos)+7
	valueend = data.find('"', valuestart+2)
	return refstr(data[valuestart:valueend])

currentRegisteredIp = getCurrentIp(data)
if __externalIP__ == currentRegisteredIp:
	print ' - Skipping update, external IP is the regisitrered IP at iis.se'
else:
	print ' - Updating nameserver ' + __nsserver__ + ' to ' + __externalIP__
	http.htmldata = updatedata
	headers, data = http.navigate()

	f=open('dump.html', 'wb')
	f.write(data)
	f.close()

for t in enumerate():
	try:
		t._Thread__delete()
	except:
		pass
_exit(0)