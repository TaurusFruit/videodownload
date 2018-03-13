#!/usr/bin/env bash

export python3="/usr/bin/env python3"

base_dir="/Data/webapps/videodownload"
pid="/var/run/video/download.pid"

function status(){
        if [ -f $pid ];then
                file_path=`ps aux|grep ffmpeg|grep -v grep|grep ".mp4$"|awk '{print $NF}'`
                if [ ! -z $file_path ];then
                        echo "Downloading file: ${file_path}"
                fi
                echo "VideoDownload is running, pid :`cat ${pid}`"
        else
                echo "VideoDownload is stop"
        fi
}

function start(){
        if [ -f "${pid}" ];then
                echo "VideoDownload already running,pid `cat ${pid}`"
                exit
        else
                mkdir -p /Data/webapps/video_log/logs
                nohup python3 ${base_dir}/src/down.py > /Data/webapps/video_log/logs/script.log 2>&1 &
                #nohup python3 ${base_dir}/scripts/transcoding.py >/Data/webapps/video_log/logs/trans.log 2>&1 &
                #nohup sh /Data/webapps/VideoDownload/DownloadMonitor.sh >> /Data/webapps/VideoDownload/logs/downloadmonitor.log 2>&1 &
                echo "start ok"
        fi
}

function check_ffmpeg(){
        file_path=`ps aux|grep ffmpeg|grep -v grep|grep ".mp4$"|awk '{print $NF}'`
        if [ ! -z $file_path ];then
                for i in `ps aux|grep ffmpeg|grep -v grep|awk '{print $2}'`;do kill -9 $i;done
                rm -f $file_path
                echo "stop ffmpeg ok"
                echo "delect file ${file_path} ok"
        fi
}

function stop(){
        if [ ! -f "${pid}" ];then
            echo "VideoDownload not running"
        else
            kill -9 `ps axu|grep logcat|grep -v grep|awk '{print $2}'`
            kill -9 `cat ${pid}`
            rm -f $pid

        #kill -9 `cat /Data/webapps/VideoDownload/tmp/trans.pid`
         #       kill -9 `cat /Data/webapps/VideoDownload/tmp/downloadmonitor.pid`
          #      rm -f /Data/webapps/VideoDownload/tmp/downloadmonitor.pid
           #     rm -f /Data/webapps/VideoDownload/tmp/trans.pid
            #    check_ffmpeg
             #   rm -f ${pid}
                echo "stop ok"
        fi
}

case $1 in
start)
        start
;;
stop)
        stop
;;
status)
        status
;;
restart)
        stop
        start
;;
*)
echo "./start.sh {start|stop|restart|status}"
;;
esac