#!/usr/bin/env python3
# coding=utf-8

import re
from base import *
from monitor import *
import requests
import os
import time
import json
import random

class AdbTool(object):
	def __init__(self):
		self.device_log_file = config_data['device']['log']				#设备日志地址
		self.device_ip = config_data['device']['ip']					#设备IP地址
		self.video_save_path = config_data['video']['root']				#视频存储目录
		self.contact = config_data['monitor']['mail']					#联系人
		self.log_level = config_data['global']['log_level']
		self.img_dir_path = config_data['image']['root']				#图片目录路径
		self.video_last_data = self.getLastDeviceLog()

	def demoStart(self):
		os.system("adb shell am start -n com.demo.wl.jumpdemonew/com.demo.wl.jumpdemonew.MainActivity")

	def demoShutdown(self):
		os.system("adb shell am force-stop com.demo.wl.jumpdemonew")

	def demoCheck(self):
		if len(os.popen("ps aux|grep 'adb logcat'|grep -v grep").read()) == 0:
			SaveLog("[0] adb logcat 未启动,正在启动 adb logcat",3)
			os.system("$nohup adb logcat -v time|grep 'play_url' >> %s &" % self.device_log_file)
		else:
			SaveLog("[0] adb locat 运行正常")


	def getLastDeviceLog(self):
		'''
		获取最后一条有效日志
		:return:
		'''
		self.demoCheck()
		self.demoStart()  # 启动demo程序
		try:
			device_log_data = FileHandle(self.device_log_file,type='r')[-10:]				# 获取最后10条日志记录
			device_last_log = {}															# 最后一条可用日志数据 {'aid':111,'sid':1111,'url':'http:xxxx'}
			url_compile = re.compile(r'^\d+.+?D/VooleEpg2.+AdPlayer.+\[CDATA\[(?P<url>http://.+aid\":\"(?P<aid>\w+)\".+\"sid\":\"(?P<sid>\w+).+proto=5&up=\'ua=\w+&ub=\w+&ud=\w+&ug=\w+\')\]\].+$')
			for each_log in device_log_data:
				url_info_dict = url_compile.match(each_log)
				if url_info_dict:
					device_last_log = url_info_dict.groupdict()

			if device_last_log:
				info_log = "[1] 获取日志数据成功"
				debug_log = info_log + " %s" % str(device_last_log)
				if self.log_level == 'info':
					SaveLog(info_log)
				elif self.log_level == "debug":
					SaveLog(debug_log, 3)
				device_last_log['url'] = device_last_log['url'].replace('127.0.0.1', self.device_ip)	# 替换日志url地址中127。0.0.1 为设备IP
				device_last_log['vid']  = device_last_log['aid'] + device_last_log['sid']				# 增加vid字段
				return device_last_log  # 返回最后一条记录aid sid url信息
			else:
				err = "[1] 未获取到正确下载日志"
				SaveLog(err,2)
			return False
		except:
			err = "[1] 获取日志数据失败"
			sendMail(self.contact, err)
			SaveLog(err, 2)
			return False

	def matchCurrentVideoData(self):
		'''
		判断当前日志信息跟下发信息是否匹配
		:return: 匹配返回True 否则返回False
		'''
		log_current_data = self.video_last_data
		if not log_current_data:		# 如果没有 日志数据
			err = "[2] 日志数据为空，匹配失败"
			SaveLog(err,2)
			return False
		server_current_data = getServerData()		# 获取服务器下发视频信息
		print(server_current_data)
		if log_current_data['aid'] == server_current_data['aid'] and log_current_data['sid'] == server_current_data['sid']:	# 判断信息是否匹配
			info_log = "[2] 日志/服务器 视频信息匹配正确"
			debug_log = info_log + " %s" % str(server_current_data)
			if self.log_level == 'info':
				SaveLog(info_log)
			elif self.log_level == 'debug':
				SaveLog(debug_log,3)
			return True
		else:
			err_log = "[2] 日志/服务器 视频信息不匹配 服务器数据(%s) 日志数据(%s)" % (server_current_data,log_current_data)
			SaveLog(err_log,2)
			return False


	def checkVideoStatus(self):
		'''
		检查当前日志 视频ID 是否已下载，如果已下载完成返回Fales，
		如果下载错误失败，或者没有记录，更新成新的正在新增下载记录 返回True
		:return: 已下载返回False ， 新增下载返回True
		'''
		log_current_data = self.video_last_data					# 获取日志视频信息
		if not log_current_data:
			return False
		aid = log_current_data['aid']
		sid = log_current_data['sid']
		url = log_current_data['url']
		vid = log_current_data['vid']
		sql = "SELECT * FROM video_info WHERE vid = %s"  % vid 		# 查询当前视频是否有记录
		db_res = DB(sql,'select')									# 执行sql，返回查询结果
		if db_res:													# 如果存在数据，判断状态值
			path = db_res[0]['path']
			name = "%s/%s" % (path,db_res[0]['name'])
			if db_res[0]['status'] == '2':							# 如果状态等于 2 ，返回服务器下载完成
				post_data =  {'aid':aid,'sid':sid,'path':path,'name':name,'status':'2'}		# 返回服务器接口数据
				PostData(post_data)
				self.demoShutdown()								# 返回下载成功后关闭 demo程序
				return False
			else:													# 如果状态不为2 ，删除对应下载记录
				update_sql = "UPDATE video_info SET status = '1', url = '%s' WHERE vid = '%s' " % (url,vid)
				DB(update_sql,'insert')
				info_log = "[3] 检查到新视频信息，更新下载失败记录状态为 1  vid: %s " % vid
				SaveLog(info_log)
				return True
		else:														# 如果不存在记录，添加记录
			insert_sql = "INSERT INTO video_info(vid,path,status,name,aid,sid,url) VALUES ('%s','%s','%s','%s','%s','%s','%s')" % (vid,'null','1','null',aid,sid,url)
			DB(insert_sql,'insert')
			info_log = "[3] 新增视频信息，vid: %s" % vid
			SaveLog(info_log)
			return True

	def getDownloadUrl(self,url_data,vid):
		'''
		通过原始url地址 获取下载url地址
		:param base_url:
		:return:
		'''
		try:
			html_res = requests.get(url_data['url'], timeout=10)
			html_res = html_res.text.split()
			for each in html_res:
				if each.startswith("http://"):
					url = each
					info_log = "[4] 解析下载地址成功，vid:%s" % vid
					debug_log = info_log + " 解析地址为: %s" % url
					if self.log_level == 'info':
						SaveLog(info_log)
					elif self.log_level == 'debug':
						SaveLog(debug_log, 3)
					return url
			else:
				error_log = "[4] 解析视频地址失败 vid:%s url:%s" % (vid,url_data)
				SaveLog(error_log,3)
				return False
		except:
			error_log = "[4] 解析视频地址出错 vid:%s url:%s" % (vid, url_data)
			SaveLog(error_log,3)
			return False


	def runDownload(self):
		if not self.matchCurrentVideoData():					# 判断日志与服务器是否匹配
			return False
		if not self.checkVideoStatus():							# 判断是否有新视频需要下载
			return False
		video_data = self.video_last_data
		print(video_data)
		download_url = self.getDownloadUrl(video_data['url'],video_data['vid'])			# 获取解析后的下载地址
		if not download_url:															# 如果解析地址失败，更新数据库状态，返回False
			update_sql = "UPDATE video_info SET status='4' WHERE vid='%'" % (video_data['vid'])
			DB(update_sql,'insert')
			return False

		video_name = "%s_%s.mp4" % (str(int(time.time())),''.join(random.sample(['1','2','3','4','5','6','7','8','9','0'],6)))	# 根据时间戳 随机数 生成文件名
		video_aid = video_data['aid']
		video_sid = video_data['sid']
		video_vid = video_data['vid']
		video_path = str(datetime.datetime.now().strftime('/%Y/%m/%d'))
		video_dir_path = os.path.join(self.video_save_path, video_path.lstrip('/'))
		update_sql = "UPDATE video_info SET name = '%s',path = '%s' WHERE vid = '%s'" % (video_name, video_path, video_vid)
		DB(update_sql,'insert')
		if not os.path.isdir(video_dir_path):
			os.system('mkdir -p %s' % video_dir_path)

		video_save_name = os.path.join(video_dir_path, video_name)
		if self.DownloadVideo(video_vid,download_url,video_aid,video_sid,video_path,video_name,video_save_name):
			return True
		return False

	def DownloadVideo(self,vid, url, aid, sid, path, name, save_name):
		sql = "UPDATE video_info SET status = 9 WHERE vid = '%s' " % vid
		DB(sql,'insert')
		info_log = "[5] 开始进入下载 vid : %s" % vid

		ffmpeg_log_name = self.script_path + "/ffmpeg_log/" + name + ".log"			# 当前下载日志
		cmd = "ffmpeg -i '%s' -absf aac_adtstoasc -acodec copy -vcodec copy -f mp4 %s > %s 2>&1" % (url, save_name, ffmpeg_log_name)
		post_data = {'aid': aid, 'sid': sid, 'path': path, 'name': '%s/%s' % (path, name), 'status': '1'}
		PostData(post_data)
		cmd_status = os.system(cmd)
		info_log = "【6】ID: %s 下载命令执行完毕,命令返回值:%s" % (vid,str(cmd_status))
		SaveLog(info_log)
		file_data = self.getFileData(save_name, vid)

		if not file_data and cmd_status != '0':
			sql = "UPDATE video_info SET status = '5' WHERE vid = '%s'" % vid
			DB(sql,'insert')
			error_log = "【6】视频下载失败 vid: %s " % vid
			SaveLog(error_log,3)
			return False

		else:
			SaveLog("ID: %s 下载成功 存放地址:%s" % (vid,save_name))
			self.savePic(save_name, path, name, vid)
			try:																	# 判断视频文件是否需要转码
				cmd = "ffprobe -v quiet -print_format json -show_format -show_streams -i %s" % save_name
				file_info = os.popen(cmd).read()
				if 'color_space' in json.loads(file_info)['streams'][0]:
					sql = "UPDATE video_info SET status = '3' WHERE vid = '%s'" % vid
					DB(sql,'insert')
					SaveLog("[6] ID: %s 更新视频状态为 待转码 成功"%vid)
					post_data = {'aid': aid, 'sid': sid, 'path': path, 'name': '%s/%s' % (path, name), 'status': '2'}
					PostData(post_data)
					self.demoShutdown()														# 关闭demo程序
					return True
			except:
				SaveLog("[6] ID: %s 获取视频信息 失败",3)
			sql = "UPDATE video_info SET status = '2' WHERE vid = '%s'" % vid
			DB(sql,'insert')
			SaveLog("[6] ID: %s 更新视频状态为 下载完成 成功" %vid)
			post_data = {'aid': aid, 'sid': sid, 'path': path, 'name': '%s/%s' % (path, name), 'status': '2'}
			PostData(post_data)
			self.demoShutdown()
			return True

	def savePic(self,full_path,path,name,vid):
		'''
		保存视频图片
		:param save_name:
		:param path:
		:param name:
		:param vid:
		:return:
		'''
		base_dir = self.img_dir_path
		pic_dir = os.path.join(base_dir, path.lstrip('/'))
		if not os.path.isdir(pic_dir):
			os.system("mkdir -p %s" % pic_dir)
		pic_full_path = os.path.join(pic_dir, name.replace('mp4', 'jpg'))
		try:
			cmd_get_time = os.popen(
				"ffprobe -v quiet -print_format json -show_format -show_streams -i %s" % full_path).read()
			v_time_stm = int(float(json.loads(cmd_get_time)['streams'][0]['duration']))
			pic_stm = random.randint(int(v_time_stm / 2), v_time_stm)
			pic_time = self.sec2time(pic_stm)
		except:
			pic_time = "00:00:50"
		cmd = "ffmpeg -ss %s -i %s -f image2 -q:v 2 -y %s >/dev/null 2>&1" % (pic_time, full_path, pic_full_path)

		os.system(cmd)
		SaveLog("[7] ID: %s 截图已生成,图片时间:%s 位置 %s" % (vid, pic_time, pic_full_path))

	def sec2time(self,sec):
		hour = 60 * 60
		min = 60
		if sec > hour:
			h = str(int(sec / hour)).zfill(2)
			m = str(int((sec - (int(h) * 60 * 60)) / min)).zfill(2)
			s = str(int(sec - (int(h) * 60 * 60 + int(m) * 60))).zfill(2)
			return ("%s:%s:%s" % (h, m, s))
		elif sec > min:
			m = str(int(sec / min)).zfill(2)
			s = str(int(sec - int(m) * 60)).zfill(2)
			return ("00:%s:%s" % (m, s))
		else:
			return ("00:00:%s" % str(sec).zfill(2))


	def getFileData(self,name,vid):
		'''
		获取视频文件信息
		:param save_name:
		:param vid:
		:return:
		'''
		if os.path.isfile(name):
			SaveLog("[8] 正在获取视频文件信息")
			file_size = int(os.path.getsize(name))
			file_size_unit = ['b', 'K', 'M', 'G']
			file_size_bit = 0
			while file_size > 1024:
				file_size = int(file_size / 1024)
				file_size_bit += 1
			file_size = int(file_size)
			sql = "UPDATE video_info SET size = '%s' WHERE vid = '%s'" % (str(os.path.getsize(name)), vid)
			DB(sql, 'insert')
			SaveLog("[8] 获取视频文件信息成功,文件大小:%s%s" % (file_size, file_size_unit[file_size_bit]))
			return (file_size, file_size_unit[file_size_bit])
		else:
			SaveLog("[8] 获取视频文件信息失败,文件不存在", 3)
			return False

if __name__ == '__main__':
	pid = str(os.getpid())
	with open(config_data['global']['pid'],'w') as f:
		f.write(pid)


	while 1:
		adbtool = AdbTool()
		adbtool.runDownload()
		adbtool.demoShutdown()
		time.sleep(10)













	# def basicLog(self,log_data):
	# 	'''
	# 	正常日志分析
	# 	:return: 解析成功返回 {aid,sid,url,vid}
	# 	'''
    #
    #
	# 	url_compile = re.compile(r'^\d+.+?D/VooleEpg2.+AdPlayer.+\[CDATA\[(?P<url>http://.+aid\":\"(?P<aid>\w+)\".+\"sid\":\"(?P<sid>\w+).+proto=5&up=\'ua=\w+&ub=\w+&ud=\w+&ug=\w+\')\]\].+$')
	# 	video_data = url_compile(log_data)
    #
	# 	if video_data:
	# 		video_data = video_data.groupdict()
	# 		url = video_data['url'].replace('127.0.0.1',self.device_ip)
	# 		sid = video_data['sid']
	# 		aid = video_data['aid']
	# 		vid = aid+sid
	# 		return {'aid':aid,'sid':sid,'url':url,'vid':vid}
	# 	else:
	# 		err = "视频地址解析失败:%s" % log_data
	# 		SaveLog(err,2)
	# 		sendMail(self.contact,err)
	# 	return False
    #
	# @property
	# def getApiLasttime(self):
	# 	'''
	# 	获取请求时间差
	# 	:return:
	# 	'''
	# 	url = config_data['global']['server_lasttime_url']
	# 	try:
	# 		res_time = requests.get(url).text
	# 		t = time.strptime(res_time,"%Y-%m-%d %H:%M:%S")
	# 		t1 = datetime.datetime(*t[:6])
	# 		t2 = datetime.datetime.now()
	# 		time_interval= int((t2-t1).seconds)
	# 		return time_interval
	# 	except:
	# 		err = "获取API请求时间失败"
	# 		SaveLog(err,2)
	# 		sendMail(self.contact,err)
	# 	return False
    #
	# def postDownloadErr(self):
	# 	"""
	# 	返回当前
	# 	:return:
	# 	"""

	# def analysisLog(self):
	# 	'''
	# 	分析日志方法
	# 	:return:
	# 	'''
    #
	# 	device_last_log = self.getLastDeviceLog()
	# 	if not device_last_log:
	# 		return False
    #
	# 	#正常日志
	# 	if "vodfile.m1905" not in device_last_log:      # 非 1905 日志
	# 		video_data = self.basicLog(device_last_log) # 分析日志参数 返回 aid sid url vid
	# 		if not video_data:
	# 			return False
    #
	# 		server_data = self.getServerData()          # 获取当前api接口aid sid
	# 		if not server_data:
	# 			return False
    #
	# 		if len(server_data) == 0:                   # 判断接口是否为空
	# 			time_interval = self.getApiLasttime  # 获取最后获取接口数据时间
	# 			if not time_interval:
	# 				return False
	# 			if time_interval > 1200:                # 判断最后获取接口时间 时间差是否大于1200
	# 				self.xiaokRestart()                 # 重启小K
	# 				err = "API 接口 %s 秒没收到请求,重启小K" % time_interval
	# 				SaveLog(err)
	# 				sendMail(self.contact,err)
	# 				return False
    #
	# 		if video_data['aid'] == server_data['aid'] and video_data['sid'] == server_data['sid']:     # 判断api接口数据跟日志是否一致
	# 			sql = "SELECT * FROM video_info WHERE vid = '%s'" % video_data['vid']                   # 查询当前日志vid 是否存在
	# 			sql_res = DB(sql)
	# 			if sql_res:                                                                             # 如果存在返回API 下载完成
	# 				if sql_res[0]['status'] == '2' or sql_res[0]['status'] == '3' or sql_res[0]['status'] == '6' or sql_res[0]['status'] == '7':                                                     # 判断存储status值,如果是2 返回下载完成
	# 					post_data = {
	# 						'aid':sql_res[0]['aid'],
	# 						'sud':sql_res[0]['sid'],
	# 						'path':sql_res[0]['path'],
	# 						'name':sql_res[0]['name'],
	# 						'status':2
	# 					}
	# 					PostData(post_data)
	# 					err = "sid:%s aid:%s 重复下载,返回下载完成" % (sql_res[0]['aid'],sql_res[0]['sid'])
	# 					SaveLog(err,2)
	# 					return True
	# 				elif sql_res[0]['status'] == '4' or sql_res[0]['status']  == '5':                   # 如果状态标记为下载失败,更新记录值
	# 					sql = "UPDATE video_info SET status = '1' ,url='%s'" % video_data['url']
	# 					DB(sql,'insert')                                                                # 更新数据库
	# 					err = "sid:%s aid:%s 更新数据状态,等待重新下载" % (sql_res[0]['aid'],sql_res[0]['sid'])
	# 					SaveLog(err,2)
	# 					return True
	# 			else:                                                                                   # 如果数据不存在,更新数据库
	# 				sql = "INSERT INTO video_info(vid,path,status,name,aid,sid,url) VALUES " \
	# 						"('%s','%s','%s','%s','%s','%s','%s')" % (video_data['vid'],'null','1','null',video_data['aid'], video_data['sid'],video_data['url'])
	# 				DB(sql,'insert')
	# 				return True
	# 		else:                                                                                       # api接口 与 日志 数据不一致,重启小K
	# 			self.xiaokRestart()
	# 			err = "API 接口正常, 未记录日志,重启小K"
	# 			SaveLog(err)
	# 			sendMail(self.contact,err)
	# 			return False
	# 	else:




	# def LogAnalysis(self):
	# 	'''
	# 	分析日志
	# 	:return:
	# 	'''
	# 	try:
	# 		#取出最后一条日志记录 device_last_log
	# 		device_log_list = FileHandle(self.device_log,type="r")
	# 		device_log_list = device_log_list[-20:]
	# 		for each_log in device_log_list:
	# 			if "VOOLEAUTH" not in device_log_list:
	# 				continue
	# 			device_last_log = each_log
	# 	except:
	# 		err = "Open device log failed:%s" % self.device_log
	# 		SaveLog(err,2)
	# 		sendMail(self.contact,err)
	# 		return False
	# 	#正常日志
	# 	if "vodfile.m1905" not in device_last_log:
	# 		#补足完整url地址
	# 		if "&proto=5" not in device_last_log:
	# 			tmp_log = device_last_log.split("&")
	# 			try:
	# 				if 'm3u8' in tmp_log[-2]:
	# 					tmp_log[-1] = "proto=5"
	# 					device_last_log = "&".join(tmp_log)
	# 			except:
	# 				pass
	# 		#匹配出关键词
	# 		url_compile = re.compile('.*VOOLEAUTH.*?(?P<url>http://.*"aid":"(?P<aid>\\w+).*"sid":"(?P<sid>\\w+)",.*proto=5).*')
	# 		video_data = url_compile(device_last_log)
	# 		#地址解析成功
	# 		if video_data:
	# 			video_data = video_data.groupdict()
	# 			url = video_data['url'].replace('127.0.0.1',self.device_ip)
	# 			sid = video_data['sid']
	# 			aid = video_data['aid']
	# 			vid = aid+sid
	#
	#
	# 			#查询vid是否存在
	# 			sql = "SELECT * FROM video_info WHERE vid = '%s'" % vid
	# 			res = DB(sql)
	# 			#如果存在 判断视频状态,如果是2 返回接口视频下载成功,如果是4,更新数据库状态为9 重新下载
	# 			if res:
	# 				video_status = res[0]['status']
	# 				if video_status == '2':
	# 					path = res[0]['path']
	# 					name = res[0]['name']
	# 					post_data = {'aid':aid,'sid':sid,'path':path,'name':'%s/%s'%(path,name),'status':'2'}
	# 					PostData(post_data)
	# 				elif video_status == '4':
	# 					sql = "UPDATE video_info SET status = '1' , url = '%s' ,name = 'null' , path = 'null' WHERE vid = '%s'" % (url,vid)
	# 					if DB(sql,'insert'):
	# 						SaveLog("ID: %s , 更新视频状态成功" % vid)
	# 					else:
	# 						SaveLog("ID: %s , 更新视频状态成功" % vid)
	# 			#如果不存在,新增数据状态为9,等等下载
	# 			else:
	# 				sql = "INSERT INTO video_info(vid,path,status,name,aid,sid,url) VALUES " \
	# 					"('%s','%s','%s','%s','%s','%s','%s')" % (vid,'null','1','null',vid,sid,url)
	# 				if DB(sql,'insert'):
	# 					SaveLog("ID: %s , 新增视频下载信息成功" % vid)
	# 				else:
	# 					SaveLog("ID: %s , 新增视频下载信息失败" % vid)
	# 			return True
	# 		#解析地址失败
	# 		else:
	# 			err = "视频地址解析失败,记录值:%s" % device_last_log
	# 			SaveLog(err)
	# 			sendMail(self.contact,err)
	# 			return False
	# 	#如果是1905地址
	# 	else:
	# 		current_download_data = GetDownloadData()
	# 		try:
	# 			aid = current_download_data[0]['aid']
	# 			sid = current_download_data[0]['sid']
	# 			vid = aid+sid
	# 			post_data = {'aid':aid,'sid':sid,'path':'null','name':'null','status':'4'}
	# 			PostData(post_data)
	# 			sql = "INSERT INTO video_info(vid,path,status,name,aid,sid,url) VALUES " \
	# 				"('%s','%s','%s','%s','%s','%s','%s')" % (vid,'null','1','null',vid,sid,device_last_log)
	# 			DB(sql,'insert')
	# 		except:
	# 			pass
	# 		err = "1905 地址视频 返回下载错误 aid:%s sid:%s" % (aid,sid)
	# 		SaveLog(err,2)
	# 		sendMail(self.contact,err)
	# 		return False
	#
	#
	# def RunDownload(self):
	# 	'''
	# 	执行下载
	# 	:return:
	# 	'''
	# 	self.LogAnalysis()
	#
	# 	#获取下载列表
	# 	video_download_list = {}
	# 	sql = "SELECT * FROM video_info WHERE status = '1'"
	# 	video_data = DB(sql)
	#
	# 	for item in video_data:
	# 		video_download_list.setdefault(item['vid'],{'aid':item['aid'],'sid':item['sid'],
	# 		                                        'name':item['name'],'path':item['path'],
	# 		                                        'status':item['status'],'url':item['url']})
	# 	#判断下载列表是否为空,如果为空,检查
	# 	if len(video_download_list) == 0:
	# 		current_download_data = GetDownloadData()
	# 		if len(current_download_data) > 0:
	# 			aid = current_download_data[0]['aid']
	# 			sid = current_download_data[0]['sid']
	# 			vid = aid+sid
	# 			sql = "SELECT * FROM video_info WHERE vid='%s'" % vid
	# 			db_res = DB(sql)
	# 			#查询数据库,如果vid存在,返回vid状态,如果不存在,返回下载错误
	# 			if len(db_res) > 0:
	# 				path = db_res[0]['path']
	# 				name = db_res[0]['name']
	# 				if db_res[0]['status'] != '2':
	# 					post_data = {'aid':aid,'sid':sid,'path':path,'name':name,'status':'0'}
	# 				else:
	# 					post_data = {'aid':aid,'sid':sid,'path':path,'name':name,'status':'2'}
	# 				PostData(post_data)
	# 			else:
	# 				post_data = {'aid':aid,'sid':sid,'path':'null','name':'null','status':'0'}
	# 				PostData(post_data)
	# 				err = "下载列表为空,下载队列未记录日志,返回下载失败 aid:%s sid:%s" % (aid,sid)
	# 				SaveLog(err)
	# 				sendMail(self.contact,err)







