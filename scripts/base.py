#!/usr/bin/env python3


import datetime
import yaml
import os
import pymysql
import requests
import time

config_file = '/Data/webapps/videodownload/config/config.yml'

with open(config_file) as f:
	config_data = yaml.load(f)

LOG_ROOT = config_data['log']['root']


def FileHandle(filename,data=None,type='r'):
	'''
	文件操作
	:param filename:
	:param data: 写入文件内容
	:param type: 类型，默认为读
	:return:
	'''
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
	打印日志到日志文件 video_%y-%m-%d.log≤
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
	elif type == 3:
		data = time_stm + " [DEBUG] " + data + "\n"
	else:
		data = time_stm + " [WARNNING] " + data + "\n"
	FileHandle(os.path.join(LOG_ROOT,log_file),data=data,type='a')




def DB(sql,func="select"):
	'''
	数据库操作方法
	:param sql: 执行sql语句
	:param func: 操作方法，默认select
	:return:
	'''
	db_name = config_data['db']['name']
	db_port = int(config_data['db']['port'])
	db_host = config_data['db']['host']
	db_user = config_data['db']['user']
	db_pass = config_data['db']['passwd']

	conn = pymysql.connect(
		host = db_host,
		port = db_port,
		user = db_user,
		passwd = db_pass,
		db = db_name
	)
	cursor = conn.cursor(cursor=pymysql.cursors.DictCursor)
	if func == "insert":
		try:
			cursor.execute(sql)
			conn.commit()
			conn.close()
			return True
		except:
			conn.rollback()
			conn.close()
			return False
	elif func == "select":
		try:
			cursor.execute(sql)
			results = cursor.fetchall()
			conn.close()
			return results
		except:
			conn.close()
			return False

def getServerData():
	'''
	获取服务器当前下载数据
	'''
	url = config_data['global']['server_current_url']		# 服务器当前下载接口 获取当前下载视频信息
	try:
		data = requests.get(url,timeout=5)
		info_log = "[3] 获取服务器下载列表成功"
		SaveLog(info_log)
		return data.json()['data'][0]
	except:
		err_log = "[3] 获取服务器下载列表失败"
		SaveLog(err_log,2)
	return False

def PostData(data):
	'''
	讲下载结果post给服务器方法
	:param data:
	:return:
	'''
	url = config_data['global']['server_post_url']
	try:
		req = requests.post(url,data=data)
		SaveLog("数据已发送成功 %s" % data)
		SaveLog("服务器返回数据 %s" % req.json())
		return True
	except:
		SaveLog("数据发送失败 %s" % data)
		return False

def adbStatus():
	'''
	检查adb 状态
	:return:
	'''
	while 1:
		demo_status = os.popen("adb shell ps |grep demo")
		if 'demo' in demo_status.read():
			SaveLog('demo program runing OK')
			break
		else:
			SaveLog('demo program is down',2)
			os.open("adb shell am start -n com.demo.wl.jumpdemonew/com.demo.wl.jumpdemonew.MainActivity")
			time.sleep(10)

	if len(os.popen("ps aux|grep 'adb logcat'|grep -v grep").read()) == 0:
		SaveLog('adb logcat is down,restart adb logcat',3)
		os.system("$nohup adb logcat -v time|grep 'play_url' >> %s &" % config_data['device']['log'])
