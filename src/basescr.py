#!/usr/bin/env python3

import logging
import sys
import yaml
import datetime
import os
import requests
import pymysql


def conf(*args):
    '''
    获取配置
    :param args:
    :return:
    '''
    CONF_FILE = '/Data/webapps/videodownload/config/vconf.yml'
    with open(CONF_FILE) as f:
        config_data = yaml.load(f)
    try:
        return config_data[args[0]][args[1]]
    except:
        return False

logger = logging.getLogger('video')
log_level = {
    'debug':logging.DEBUG,
    'info':logging.INFO,
    'warn':logging.WARN,
    'error':logging.ERROR,
    'fatal':logging.FATAL,
    'critical':logging.CRITICAL
}
#设置日志级别
logger.setLevel(log_level[conf('log','level')])
# 设置日志文件位置
try:
    log_file = datetime.datetime.now().strftime(conf('log','download'))
except:
    log_file = conf('log','download')
log_path = os.path.join(conf('log','dir'),log_file)
# 设置文件handler
log_fh = logging.FileHandler(log_path)
console_handler = logging.StreamHandler(sys.stdout)

# 设置日志格式
fmt = "[%(asctime)-15s] [%(levelname)-8s] [%(name)s] %(message)s"
datefmt = "%Y-%m-%d %H:%M:%S"
formatter = logging.Formatter(fmt, datefmt)

# 给logger添加handler 和 formatter
logger.addHandler(log_fh)
log_fh.setFormatter(formatter)
# 判断是否终端打印
if conf('log','console_print') == True:
    logger.addHandler(console_handler)
    console_handler.setFormatter(formatter)

class Mysql(object):
    def __init__(self):
        self.__conf = {
            'host':conf('db','host'),
            'port':conf('db','port'),
            'user':conf('db','user'),
            'passwd':conf('db','passwd'),
            'db':conf('db','name')
        }

    def __conn(self):
        self.conn = pymysql.connect(**self.__conf)
        cursor = self.conn.cursor(cursor = pymysql.cursors.DictCursor)
        if cursor:
            return cursor
        else:
            return False

    def insert(self,sql):
        cursor = self.__conn()
        try:
            cursor.execute(sql)
            self.conn.commit()
            self.conn.close()
            info_log = "数据更新成功"
            debug_log = "更新SQL: %s" % sql
            logger.info(info_log)
            logger.debug(debug_log)
            return True
        except:
            self.conn.rollback()
            self.conn.close()
            logger.error("数据插入失败,SQL:%s"%sql)
            return False

    def select(self,sql):
        cursor = self.__conn()
        try:
            cursor.execute(sql)
            results = cursor.fetchall()
            self.conn.close()
            info_log = "数据查询成功"
            debug_log = "查询SQL: %s" % sql
            logger.info(info_log)
            logger.debug(debug_log)
            return results
        except:
            self.conn.close()
            logger.error("数据查询失败,SQL: %s" %sql)
            return False

    def update(self,sql):
        return self.insert(sql)


class FileHandle():
    def __init__(self,filename):
        self.filename = filename

    def write(self,data):
        try:
            with open(self.filename,'w') as f:
                f.writelines(data)
            logger.debug("写入文件成功,文件名:%s" % self.filename)
            return True
        except:
            logger.error("写入文件失败,文件名:%s" % self.filename)
            return False

    def add(self,data):
        try:
            with open(self.filename,'a') as f:
                f.writelines(data)
            logger.info("追加文件内容成功,文件名:%s" % self.filename)
            return True
        except:
            logger.error("追加文件内容失败,文件名:%s" % self.filename)
            return False

    def read(self):
        try:
            with open(self.filename) as f:
                fd = f.readlines()
            logger.debug("读取文件成功,文件名:%s" % self.filename)
            return fd
        except:
            logger.debug("读取文件失败,文件名:%s" % self.filename)
            return False

class ServerData(object):
    def __init__(self):
        self.get_data_url = conf('global','server_current_url')
        self.post_data_url = conf('global','server_post_url')
        self.get_lasttime_url = conf('global','server_lasttime_url')

    def getData(self):
        try:
            data = requests.get(self.get_data_url,timeout=10)
            logger.debug("获取服务器下载列表成功")
            return data.json()['data'][0]
        except:
            logger.error("获取服务器下载列表失败")
            return False

    def postData(self,data):
        try:
            res = requests.post(self.post_data_url,data=data)
            logger.debug("数据发送成功 : %s" % str(data))
            logger.debug("服务器返回数据: %s" % str(data))
            return True
        except:
            logger.error("数据发送失败: %s" % str(data))
            return False

