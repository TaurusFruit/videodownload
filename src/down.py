from basescr import *
import time
import re
import pymysql
import requests
import random
import json

class download(object):
    def __init__(self):
        self.mysql = Mysql()            # mysql 操作
        device_log = os.path.join(conf("log","dir"),conf("log","device"))
        self.fh = FileHandle(device_log)          # 文件操作
        self.sd = ServerData()          # 服务器数据交互
        self.device_log_file = os.path.join(conf('log','dir'),conf('log','device'))
        self.device_ip_address = conf('global','device_ip')
        self.video_save_path = conf('global','video_dir')
        self.contact_mail = conf('connect','mail')
        self.img_save_path = conf('global','image_dir')
        self.ffmpeg_log_path = conf('log','ffmpeg_dir')

    def demoStart(self):
        logger.debug("[0] 正在启动demo程序")
        start_cmd = "adb shell am start -n com.demo.wl.jumpdemonew/com.demo.wl.jumpdemonew.MainActivity"
        os.system(start_cmd)
        logger.debug("[0] 正在启动logcat程序")
        os.system("timeout 10 adb logcat -v time|grep 'play_url' > %s " % self.device_log_file)

    def demoStop(self):
        logger.debug("[1] 正在关闭demo程序")
        os.system("adb shell am force-stop com.demo.wl.jumpdemonew")
        logger.debug("[1] 正在关闭小K程序")
        os.system( "adb shell am force-stop com.konka.voole.video")
        time.sleep(10)


    def getLastDeviceLog(self):
        self.demoStart()    # 启动 demo 程序,记录日志
        #进行5次读取文件尝试,如果一直为空,判断为片源不存在,返回服务器下载错误
        retry_time = 5
        try_time = 1
        while retry_time > 0:
            logger.debug("[2] 正在进行第%s次尝试读取日志文件" % try_time)
            device_log_data = self.fh.read()
            if not device_log_data:
                logger.error("[2] 读取设备日志文件为空")
                self.demoStop()
                self.demoStart()
                retry_time -= 1
                try_time += 1
            else:
                logger.debug("[2] 读取设备日志成功")
                break
        else:
            logger.error("[2] 片源不存在,返回服务器下载失败")
            server_current_data = self.sd.getData()
            if not server_current_data:
                return False
            post_data = {"aid":server_current_data['aid'],"sid":server_current_data['sid'],"path":"null","name":"null","status":"0"}
            self.sd.postData(post_data)
            sql = "INSERT INTO video_info(vid,path,status,name,aid,sid,sname) " \
                  "VALUES ('%s','%s','%s','%s','%s','%s','%s')" % (server_current_data['aid']+server_current_data['sid'],'null','10','null',server_current_data['aid'],
                                                                   server_current_data['sid'],server_current_data['sname'])
            self.mysql.insert(sql)
            return False



        # 常规播放地址解析
        # url_nomal_compile = re.compile(r'^\d+.+?D/VooleEpg2.+AdPlayer.+\[CDATA\[(?P<url>http://.+aid\":\"(?P<aid>\w+)\".+\"sid\":\"(?P<sid>\w+).+proto=5&up=\'ua=\w+&ub=\w+&ud=\w+&ug=\w+\')\]\].+$')
        url_nomal_compile = re.compile(r'^.+(?P<url>http://127.0.0.1.+aid\":\"(?P<aid>\w+)\".+\"sid\":\"(?P<sid>\w+).+proto=5&up=\'ua=\w+&ub=\w+&ud=\w+&ug=\w+\').+$')
        # 1905 播放地址解析
        url_1905_compile = re.compile(r'^\d+.+url=\'(?P<url>http:.+\.mp4).+$')
        device_detail_data = {}
        for each_log in device_log_data:
            url_nomal_dict = url_nomal_compile.match(each_log)
            url_1905_dict = url_1905_compile.match(each_log)
            if url_nomal_dict:
                device_detail_data = url_nomal_dict.groupdict()
                logger.debug("[2] 分析设备日志完成,日志类型正常日志")
                logger.debug("[2] 日志明细: %s" % str(device_detail_data))
                break
            if url_1905_dict:
                logger.debug("[2] 分析设备日志完成,日志类型1905")
                device_detail_data = url_1905_dict.groupdict()
                break
        if len(device_detail_data) == 0:
            logger.error("[2] 分析日志完成,没有获取到视频信息")
            return False

        if len(device_detail_data) == 1:    # 1905日志 aid/sid 从服务器端获取
            server_data = self.sd.getData()
            device_detail_data['aid'] = server_data.pop('aid',"")
            device_detail_data['sid'] = server_data.pop('sid',"")
            device_detail_data['type'] = "1905"


        # 加入vid
        device_detail_data['vid'] = device_detail_data['aid'] + device_detail_data['sid']
        url = device_detail_data['url']
        device_detail_data['url'] = url.replace('127.0.0.1',self.device_ip_address)

        # 判断设备日志与服务器日志是否匹配
        device_detail_data = self.matchServerData(device_detail_data)
        if not device_detail_data:
            return False
        # 检查视频信息,更新数据库记录
        if not self.checkVideoStatus(device_detail_data):
            return False

        return device_detail_data       #  返回 {aid,sid,vid,url}

    def matchServerData(self,device_detail_data):
        '''
        与服务器接口信息匹配
        :return:
        '''
        server_current_data = self.sd.getData()

        # 正常日志判断
        if server_current_data['aid'] == device_detail_data['aid'] and server_current_data['sid'] == device_detail_data['sid']:
            sname = server_current_data['sname']
            device_detail_data['sname'] = sname
            logger.debug("[3] 设备日志&服务器信息匹配成功")
            return device_detail_data
        # 1905日志判断
        elif device_detail_data['aid'] == '' and device_detail_data['sid'] == '' and device_detail_data['url'] != '':
            device_detail_data['aid'] = server_current_data['aid']
            device_detail_data['sid'] = server_current_data['sid']
            device_detail_data['sname'] = server_current_data['sname']
            device_detail_data['vid'] = device_detail_data['aid'] + device_detail_data['sid']
            logger.debug("[3] 设备1905日志&服务器日志匹配成功")
            return device_detail_data
        else:
            logger.error("[3] 设备日志&服务器数据匹配失败")
            cmd = "adb shell am force-stop com.konka.voole.video"
            os.system(cmd)
            logger.error("[3] 正在关闭小K程序")
            return False

    def checkVideoStatus(self,device_detail_data):
        '''
        检查视频状态
        :return:
        '''
        select_sql = "SELECT * FROM video_info WHERE vid='%s'" % device_detail_data['vid']
        db_res = self.mysql.select(select_sql)
        if db_res:
            path = db_res[0]["path"]
            name = "%s/%s" % (path,db_res[0]['name'])
            if db_res[0]['status'] == '2':
                post_data = {'aid':device_detail_data['aid'],'sid':device_detail_data['sid'],'path':path,'name':name,'status':'2'}		# 返回服务器接口数据
                self.sd.postData(post_data)
                logger.debug("[4] 当前设备日志信息已下载")
                return False
            else:   # 如果状态不为2 更新视频状态为1
                updae_sql = "UPDATE video_info SET status = '1' WHERE vid = '%s'" % device_detail_data['vid']
                if self.mysql.update(updae_sql):
                    logger.info("[4] 更新数据为新下载成功,vid:%s" % device_detail_data['vid'])
                    del_file = os.path.join("/Data/webapps/video/",name)
                    os.system("rm -f %s"% del_file)
                    logger.info("[4] 删除旧视频文件成功")
                    return True
                else:
                    logger.error("[4] 更新数据为新下载失败 vid:%s" % device_detail_data['vid'])
                    return False
        else:
            device_detail_data['url'] = pymysql.escape_string(device_detail_data['url'])
            device_detail_data['sname'] = pymysql.escape_string(device_detail_data['sname'])
            insert_sql = "INSERT INTO video_info(vid,path,status,name,aid,sid,sname) " \
                         "VALUES ('%s','%s','%s','%s','%s','%s','%s')" % (device_detail_data['vid'],'null',
                                                                               '1','null',device_detail_data['aid'],
                                                                               device_detail_data['sid'],
                                                                               device_detail_data['sname'])
            if self.mysql.insert(insert_sql):
                return True
            else:
                return False

    def getDownloadUrl(self,url,vid):
        '''
        通过小K日志地址 解析下载地址
        1. 通过url 获取 原始m3u地址url2
        2. 通过url2 获取 cdn地址 url3
        3. 通过url3 获取 302地址url4
        :param url:
        :param vid:
        :return:
        '''
        logger.debug("[5] 获取到待解析URL地址:%s  vid:%s" % (url,vid))
        logger.debug("[5] 正在解析地址...")
        retry_times = 20
        try_time = 1
        headers = {'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
               'Accept-Encoding': 'gzip, deflate, sdch, br',
               'Accept-Language': 'zh-CN,zh;q=0.8',
               'Connection': 'keep-alive',
               'Host': 'pan.baidu.com',
               'Upgrade-Insecure-Requests': '1',
               'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/55.0.2883.87 Safari/537.36'}
        while retry_times > 0:
            logger.debug("[5] 正在进行第[%s]次尝试解析"% try_time)
            try:
                html_res = requests.get(url,timeout=10,headers=headers) # 获取原始m3u地址
                html_res_slice = html_res.text.split()
                for each in html_res_slice:
                    if each.startswith("http://"):
                        try:
                            url2 = each         # 通过response获取m3u地址
                            logger.debug("[5] 成功解析原始m3u地址:%s" %url2)
                            url3 = url2.split("'")[1].split("?")[0]
                            logger.debug("[5] 成功获取CDN地址:%s" % url3)

                            html = requests.get(url3, headers=headers, allow_redirects=False)   # 通过url3 获取302地址url4
                            url4 = html.headers['Location']
                            logger.debug("[5] 成功获取最终下载地址:%s" % url4)
                            logger.info("[5] 解析下载地址成功,vid:%s" % vid)

                            return url4
                        except:
                            return False
                else:
                    logger.error("[5] 解析视频地址失败 vid:%s url:%s" % (vid,url))
                    retry_times -= 1
                    try_time+=1
            except:
                logger.error("[5] 解析视频地址出错, vid:%s url:%s" % (vid,url))
                retry_times -= 1
                try_time+=1
            time.sleep(10)
        return False

    def runDownload(self):
        video_data = self.getLastDeviceLog()
        if not video_data:return False

        video_aid = video_data.pop('aid',"")
        video_sid = video_data.pop('sid',"")
        video_vid = video_data.pop('vid',"")
        video_url = video_data.pop("url","")

        #判断是否需要新生成文件名
        select_sql = "SELECT * FROM video_info WHERE vid='%s'" % video_vid
        s_db_data = self.mysql.select(select_sql)

        if s_db_data[0]['name'] != "null" and s_db_data[0]['path'] != "null":
            video_name = s_db_data[0]['name']
            video_path = s_db_data[0]['path']
        else:
            video_name = "%s_%s.mp4" % (str(int(time.time())),''.join(random.sample(['1','2','3','4','5','6','7','8','9','0'],6)))	# 根据时间戳 随机数 生成文件名
            video_path = str(datetime.datetime.now().strftime('/%Y/%m/%d'))
            update_sql = "UPDATE video_info SET name = '%s',path = '%s' WHERE vid = '%s'" % (video_name, video_path, video_vid)
            self.mysql.update(update_sql)
        # 生成服务器存放视频绝对路径
        video_dir_path = os.path.join(self.video_save_path, video_path.lstrip('/'))
        video_save_name = os.path.join(video_dir_path, video_name)
        if not os.path.isdir(video_dir_path):os.system('mkdir -p %s' % video_dir_path)

        #判断视频地址类型
        if video_data.pop("type",None) != "1905":   # 非1905
            download_url = self.getDownloadUrl(video_url,video_vid)
            if not download_url:
                update_sql = "UPDATE video_info SET status='4' WHERE vid='%s'" % video_vid
                self.mysql.update(update_sql)
                logger.debug("[7] 没有解析到下载地址,更新视频记录为下载失败")
                return False
            else:
                 return False if not self.DownloadVideo(video_vid,download_url,video_aid,video_sid,video_path,video_name,video_save_name) else True
        else:   # 1905地址
            cmd = "wget '%s' -O %s" % (video_url,video_save_name)
            logger.debug("[7] 正在下载1905视频,地址命令为:%s" % cmd)
            post_data = {'aid': video_aid, 'sid': video_sid, 'path': video_path, 'name': '%s/%s' % (video_path, video_name), 'status': '1'}
            self.sd.postData(post_data)
            cmd_status = os.system(cmd)
            if cmd_status != 0:
                update_sql = "UPDATE video_info SET status='4' WHERE vid='%s'" % video_vid
                self.mysql.update(update_sql)
                logger.debug("[7] wget 1905视频地址失败,命令状态码为:%s" % cmd_status)
                post_data = {'aid': video_aid, 'sid': video_sid, 'path': video_path, 'name': '%s/%s' % (video_path, video_name), 'status': '0'}
                self.sd.postData(post_data)
                return False
            else:
                self.getFileData(video_save_name,video_vid)
                self.savePic(video_save_name,video_path,video_name,video_vid)
                sql = "UPDATE video_info SET status = '2' WHERE vid = '%s'" % video_vid
                self.mysql.update(sql)
                logger.info("[7] wget 1905视频下载完成 vid:%s" % video_vid)
                post_data = {'aid': video_aid, 'sid': video_sid, 'path': video_path, 'name': '%s/%s' % (video_path, video_name), 'status': '2'}
                self.sd.postData(post_data)
                return True

    def DownloadVideo(self,vid,url,aid,sid,path,name,save_name):
        sql = "UPDATE video_info SET status = 9 WHERE vid = '%s' " % vid
        self.mysql.update(sql)

        logger.debug("[6] 开始进入下载")
        ffmpeg_log_name = self.ffmpeg_log_path +"/" + name + ".log"			# 当前下载日志
        cmd = 'ffmpeg -i "%s" -absf aac_adtstoasc -acodec copy -vcodec copy -f mp4 "%s" > %s 2>&1' % (url, save_name, ffmpeg_log_name)
        post_data = {'aid': aid, 'sid': sid, 'path': path, 'name': '%s/%s' % (path, name), 'status': '1'}
        self.sd.postData(post_data)
        logger.debug("[6] 正在执行下载命令,命令内容为:%s" % cmd)
        cmd_status = os.system(cmd)
        logger.debug("[6] 下载命令执行完毕,返回值:%s" % str(cmd_status))
        file_data = self.getFileData(save_name,vid)

        if not file_data or str(cmd_status) != "0":

            sql = "UPDATE video_info SET status = '5' WHERE vid = '%s'" % vid
            self.mysql.update(sql)
            post_data = {'aid': aid, 'sid': sid, 'path': path, 'name': '%s/%s' % (path, name), 'status': '0'}
            self.sd.postData(post_data)

            logger.error("[6] 更新视频状态为下载失败 vid:%s" % vid)
            return False
        else:
            logger.info("[6] 视频下载成功,vid:%s" % vid)
            self.savePic(save_name,path,name,vid)
            try:
                cmd = "ffprobe -v quiet -print_format json -show_format -show_streams -i %s" % save_name
                file_info = os.popen(cmd).read()
                if 'color_space' in json.loads(file_info)['streams'][0]:
                    sql= "UPDATE video_info SET status = '3' WHERE vid = '%s'" % vid
                    self.mysql.update(sql)
                    logger.info("[6] 更新视频状态为待转码成功 vid:%s" % vid)
                    post_data= {'aid': aid, 'sid': sid, 'path': path, 'name': '%s/%s' % (path, name), 'status': '2'}
                    self.sd.postData(post_data)
                    return True
            except:
                logger.error("[6] 获取视频信息失败 vid:%s" % vid)
            sql = "UPDATE video_info SET status = '2' WHERE vid = '%s'" % vid
            self.mysql.update(sql)
            logger.info("[6] 视频下载完成 vid:%s" % vid)
            post_data = {'aid': aid, 'sid': sid, 'path': path, 'name': '%s/%s' % (path, name), 'status': '2'}
            self.sd.postData(post_data)
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
        base_dir = self.img_save_path
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
        logger.debug("[7] ID: %s 截图已生成,图片时间:%s 位置 %s" % (vid, pic_time, pic_full_path))

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
            logger.debug("[8] 正在获取视频文件信息")
            file_size = int(os.path.getsize(name))
            file_size_unit = ['b', 'K', 'M', 'G']
            file_size_bit = 0
            while file_size > 1024:
                file_size = int(file_size / 1024)
                file_size_bit += 1
            file_size = int(file_size)
            sql = "UPDATE video_info SET size = '%s' WHERE vid = '%s'" % (str(os.path.getsize(name)), vid)
            self.mysql.update(sql)
            logger.debug("[8] 获取视频文件信息成功,文件大小:%s%s" % (file_size, file_size_unit[file_size_bit]))
            return file_size
        else:
            logger.debug("[8] 获取视频文件信息失败,文件不存在")
            return False


    def xiaokHealthCheck(self):
        tmp_file = "/var/run/video/tmp_file"
        cmd = "timeout 5 adb logcat > %s" % tmp_file
        os.system(cmd)
        file_size = os.path.getsize(tmp_file)
        with open(tmp_file,'w') as f:
            f.write("")
        if file_size > 1028 :
            return True
        else:
            return False

if __name__ == "__main__":
    pid = str(os.getpid())
    with open(os.path.join(conf("global","pid_dir"),"download.pid"),'w') as f:
        f.write(pid)

    down_monitor_times = 3
    adbtool = download()
    while 1:
        if not adbtool.xiaokHealthCheck():
            down_monitor_times -= 1
            time.sleep(1800)
        adbtool.runDownload()
        adbtool.demoStop()
        time.sleep(10)
