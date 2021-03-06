#!/usr/bin/python
#add escape message where if certain text detected - command ie. change recipient and prompt user of change
#add emojis and media
#flag toggle for sending only one automated message - sms bomb flag in config add conditional to see if no dup flag needed
#exception handling needed in post requests.exceptions.ConnectionError: ('Connection aborted.', BadStatusLine("''",))
#...paramiko.ssh_exception.NoValidConnectionsError  - ensure that devices ip address is correct
#exception handling needed for authentication issues - silent fails (check response after request for 200)
#package handles toggling authentication very shakily - one or the other
import os, sys, time, datetime, requests, threading, paramiko, ConfigParser
from scp import SCPClient
from requests.auth import HTTPDigestAuth
print

# Get the project directory to avoid using relative paths
rootDirectory = os.getcwd()

# Parse configuration file
c = ConfigParser.ConfigParser()
configFilePath = os.path.join(rootDirectory, 'config.cfg')
c.read(configFilePath)

class Config:
    # Pull user info 
    debNeeded = c.get('install','debNeeded')
    number = c.get('number','number')
    ip = c.get('ssh', 'ip')
    sshPass = c.get('ssh','password')
    udid = c.get('device','udid')
    automationNeeded = c.get('automated','needed')
    automatedTime = c.get('automated','time')
    authenticationNeeded = c.get('authentication','authNeeded')
    authUser = c.get('authentication', 'username')
    authPass = c.get('authentication', 'pass')

class SSH:
	ssh=paramiko.SSHClient()
	ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
	def __init__(self, address, port, user, passwd):
		self.address = address
		self.port = port
		self.user = user
		self.passwd = passwd
	def connect(self):
		SSH.ssh.connect(self.address,self.port,self.user,self.passwd)

print 'Checking config for deb install param...'
print
user_config = Config()
if user_config.debNeeded.lower() == 'true':
	cydiaSession=requests.session()
	remoteMessageIOS9Deb='http://fay.insanelyi.com/pool/free/c/com.sull.remotemessagesios9/com.sull.remotemessagesios9_3.2.1_iphoneos-arm.deb'
	cydiaHeaders={
		'Cache-Control':'max-age=0',
		'Host':'fay.insanelyi.com',
		'User-Agent':'Telesphoreo APT-HTTP/1.0.592',
		'X-Firmware':'9.3.3',
		'X-Machine':'iPhone6,1',
		'X-Unique-ID':user_config.udid #device UDID
	}
	print 'Downloading remote message deb...'
	r=cydiaSession.get(remoteMessageIOS9Deb,headers=cydiaHeaders)
	local_filename = remoteMessageIOS9Deb.split('/')[-1]
	with open(local_filename, 'wb') as f:
		for chunk in r.iter_content(chunk_size=1024): 
			if chunk: # filter out keep-alive new chunks
				f.write(chunk)
	print 'SSHing into device using config vals...'
	local_ssh = SSH(user_config.ip, 22, 'root', user_config.sshPass)
	local_ssh.connect()
	scp = SCPClient(local_ssh.ssh.get_transport())
	print 'SCPing downloaded deb to device...'
	scp.put(os.path.join(rootDirectory, local_filename))
	print 'Installing deb...'
	stdin, stdout, stderr = local_ssh.ssh.exec_command('dpkg -i '+local_filename)
	for i in stdout.readlines():
		print i
	local_ssh.ssh.exec_command('killall -HUP SpringBoard')
	print 'Respringing... Please Wait!'
	time.sleep(10)
else:
	print 'Deb installation is not needed...'
print
#Prompt to make changes to authentication prior to enabling/reenabling feature 
print 'Go into Settings > Remote Messages > Enable [ON]'
print '[CONFIG] '+user_config.ip+' is listed as the IP. Ensure that this is listed as "Current IP"'
if user_config.authenticationNeeded.lower()=='true':
	print '[CONFIG] Authentication required! Using provided credentitals from config! Ensure values in config and Settings app match'
else:
	print '[CONFIG] Authentication not needed. Ensure that "Use Authentication" is disabled'
print 'Ensure that the server port is: 333'
print
raw_input('Confirm the above is True...')
print

hashId='SMS;-;+'+user_config.number #'SMS' or 'iMessage'(self) prepended

#params dict used?
params={
	'hashid':hashId,
	'date':'0',
	'shouldReset':'1',
	'_':str(int(time.time()*1000))
}

messageSent=0   #only send message once - midnight checker toggle flag on midnoght detect conditional

def automatedTimeMessage(time, noDupMessage, authNeeded, authUser, authPass):
	global messageSent
	while 1: #and if flag = 0
		if datetime.datetime.now().strftime("%I:%M%p") == time and noDupMessage==0:
			message=str(datetime.datetime.now())+': Testing automated message. Should send at '+time+'!'
			files={
				'hashid': (None, hashId), 
				'reqUID': (None, ''), #need to parse in-thread for this
				'recipients': (None, ''),
				'file-name': (None, ''),
				'text': (None, message)
			}
			if authNeeded.lower()=='true':
				session.post('http://'+user_config.ip+':333/sendMessage.srv',files=files, auth=HTTPDigestAuth(authUser, authPass))
			else:
				session.post('http://'+user_config.ip+':333/sendMessage.srv',files=files)
			messageSent=1
			noDupMessage=1
			print 'Background conditional thread hit!'

def becauseItsMidnight():
	global messageSent
	while 1:
		if datetime.datetime.now().strftime("%I:%M%p") == "12:00AM":
			print 'Rollover date detected! Resetting flags...'
			messageSent=0
			noDupMessage=0
		#maybe overkill - use sleep
		time.sleep(30)

if user_config.automationNeeded.lower() == 'true':
	print 'Automated messaging set!'
	print 'Messaging '+user_config.number+' at '+user_config.automatedTime
	automatedMessageThread = threading.Thread(target=automatedTimeMessage, args=(user_config.automatedTime,messageSent,user_config.authenticationNeeded,user_config.authUser,user_config.authPass,))
	automatedMessageThread.daemon = True
	automatedMessageThread.start()
	newDayDetectonResetFlag = threading.Thread(target=becauseItsMidnight)
	newDayDetectonResetFlag.daemon = True
	newDayDetectonResetFlag.start()
else:
	print 'Automated messaging disabled!'
print
print 'Messaging '+user_config.number
session=requests.session()
while 1:
	message=raw_input('Message: ')
	files={
		'hashid': (None, hashId), 
		'reqUID': (None, ''),#need to parse in-thread for this
		'recipients': (None, ''),
		'file-name': (None, ''),
		'text': (None, message)
	}
	if user_config.authenticationNeeded.lower()=='true':
		session.post('http://'+user_config.ip+':333/sendMessage.srv',files=files, auth=HTTPDigestAuth(user_config.authUser, user_config.authPass))
	else:
		session.post('http://'+user_config.ip+':333/sendMessage.srv',files=files)
