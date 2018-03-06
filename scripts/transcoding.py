#!/usr/bin/env python3

from scripts.base import *


class transcoding(object):
    def __init__(self):
        pass

    def getTransList(self):
        '''
        获取待转码视频列表
        :return:
        '''
        select_sql = "SELECT * FROM video_info WHERE status = 3"
        db_res = DB(select_sql)
        if not db_res:
            return True
        else:
            info_log = "[20] 获取转码列表成功，共计 %s 部视频需要转码" % (str(len(db_res)))
            SaveLog(info_log)
        return db_res

    def transCoding(self):
        trans_list = self.getTransList()
        if not trans_list:return False

        for each_video in trans_list:
            vid = each_video['vid']
            aid = each_video['aid']
            sid = each_video['sid']
            dir_path = os.path.join(config_data['video']['root'], each_video['path'].lstrip('/'))
            file_path = os.path.join(dir_path, each_video['name'])
            temp_path = os.path.join(dir_path, "tmp_%s" % each_video['name'])
            cmd = "ffmpeg -i %s -strict -2 %s >> %s/logs/trans.log 2>&1" % (file_path, temp_path,config_data['log']['root'])
            SaveLog("[21] " + cmd)
            update_sql = "UPDATE video_info SET status = 3 WHERE vid = '%s' " % vid
            if DB(update_sql,'insert'):
                SaveLog("[21] ID: %s 开始转码" % vid)
                sql = "UPDATE video_info SET status = 6 WHERE vid = '%s' " % vid
                DB(sql,'insert')
                cmd_status = os.system(cmd)
                if cmd_status == 0:
                    SaveLog("[21] ID: %s 转码成功" % vid)
                    os.popen('echo y |mv %s %s' % (temp_path, file_path))
                    sql = "UPDATE video_info SET status = 2 WHERE vid = '%s' " % vid
                    post_data = {'aid': aid, 'sid': sid, 'path': each_video['path'],
                                 'name': "%s/%s" % (each_video['path'], each_video['name']), 'status': '2'}
                else:
                    SaveLog("ID: %s 转码失败,状态码 %s" % (vid, cmd_status))
                    sql = "UPDATE video_info SET status = 8 WHERE vid = '%s' " % vid
                    post_data = {'aid': aid, 'sid': sid, 'path': each_video['path'],
                                 'name': "%s/%s" % (each_video['path'], each_video['name']), 'status': '3'}
                DB(sql,'insert')
                try:
                    req = PostData(post_data)
                    SaveLog(("[21] ID: %s 数据发送成功 %s" % (vid,post_data)))
                    SaveLog("[21] ID: %s 服务器返回数据 %s" % req.json())
                except:
                    SaveLog("[21] ID: %s 数据发送失败 %s" % (vid, post_data), 3)
            else:
                SaveLog("[21] ID: %s 更改视频状态失败" % vid)
        return True

if __name__ == '__main__':
    pid = str(os.getpid())
    with open('/var/run/video/trans.pid','w') as f:
        f.write(pid)
    trans = transcoding()
    while 1:
        trans.transCoding()
        time.sleep(60)







