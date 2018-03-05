#!/usr/bin/env python3

import smtplib
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email.header import Header



def sendMail(email,alert_info,file=None):
	from email.mime.multipart import MIMEMultipart
	from email.mime.text import MIMEText
	from email.mime.application import MIMEApplication

	username = "dev_service@tansuotv.com"
	password = "xx.=xx."
	sender = username
	receivers = ",".join([email])

	msg = MIMEMultipart()
	msg['Subject'] = 'video download error'
	msg['From'] = sender
	msg['To'] = receivers
	msg["Accept-Language"]="zh-CN"
	msg["Accept-Charset"]="ISO-8859-1,utf-8"


	puretext = MIMEText(alert_info,format,'utf-8')
	msg.attach(puretext)


	try:
		client = smtplib.SMTP()
		client.connect('mail.tansuotv.com')
		client.login(username, password)
		client.sendmail(sender, receivers, msg.as_string())
		client.quit()
		print('mail send ok')
	except smtplib.SMTPRecipientsRefused:
		print('Recipient refused')
	except smtplib.SMTPAuthenticationError:
		print('Auth error')
	except smtplib.SMTPSenderRefused:
		print('Sender refused')
	except smtplib.SMTPException as e:
		print(e.message)


if __name__ == '__main__':
	sendMail('zhanglei@tansuotv.com','aaaa')