#!/usr/bin/env python3


import datetime
import yaml
import os

config_file = os.path.join(os.pardir,'config/config.yml')

with open(config_file) as f:
	config_data = yaml.load(f)

LOG_ROOT = config_data['log']['root']
ERROR_LOG = config_data['log']['error_log']


def FileHandle(filename,data=None,type='r'):
	with open(filename,type) as fh:
		if type == "r":
			return fh.readlines()
		elif type == "a" or type == "w":
			fh.write(data)
			return True
		else:
			return False

def SaveLog(data,type=1):
	'''
	打印日志到日志文件 video_%y-%m-%d.log
	:param data: 日志内容
	:param type: 1 正常日志  2 错误日志 3 同时记录
	:return:
	'''
	time_stm = "[%s]  " % datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
	data = str(data)
	log_file = "video_"+datetime.datetime.now().strftime('%Y-%m-%d')+".log"
	type = int(type)
	if not os.path.exists(LOG_ROOT):os.mkdir(LOG_ROOT)

	if type == 1:
		data = time_stm + " [INFO] " + data + "\n"
	elif type == 2:
		data = time_stm + " [ERROR] " + data + "\n"
	else:
		data = time_stm + " [WARNNING] " + data + "\n"
	FileHandle(os.path.join(LOG_ROOT,log_file),data=data,type='a')




