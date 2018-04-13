from email.header import Header
from email.mime.text import MIMEText
from email.utils import parseaddr,formataddr
import smtplib
from datetime import datetime,timedelta
# from basescr import Mysql
import sys


def getData():
    mysql = Mysql()
    sql = "SELECT video_info.status FROM `video`.`video_info` " \
          "WHERE `c_times` >= '%s 00:00:01' AND `c_times` <= '%s 00:00:01'" % (
        (datetime.today()+timedelta(days=-1)).strftime("%Y-%m-%d"),
        datetime.today().strftime("%Y-%m-%d")
    )
    res = mysql.select(sql)
    if len(res) <= 0 : return
    status = {}
    for i in res:
        status_code = i.pop("status",'null')
        status.setdefault(status_code,1)
        status[status_code]+=1

    status_map = {
        '1':"新增记录,等待下载",
        '2':"下载成功",
        '3':"下载成功,等待转码",
        '4':"下载失败,解析下载地址错误",
        '5':"下载失败,下载地址未能成功下载",
        '6':"正在转码",
        '7':"下载成功,正在转码",
        '8':"下载成功,转码失败",
        '9':"正在下载",
        '10':"下载失败,未从小K获取到日志"
    }
    data_string = "下载详情为:\n"+"".join(list(map(lambda x:"%s: \t%s部\n" % (status_map[x],status[x]),status)))
    return data_string


def sendMail(**kwargs):
    '''
    发送邮件方法
    :param kwargs:
    :return:
    '''

    default_addr = "zhanglei@tansuotv.com"           # 默认收件邮箱
    to_addr = kwargs.pop("receivers",[default_addr]) # 获取收件人邮箱
    if not isinstance(to_addr,list):
        to_addr = [to_addr]

    print(to_addr)

    msg_detail = kwargs.pop("msg","未获取到下载日报内容,请联系管理员")

    from_addr = kwargs.pop("s_addr")
    password = kwargs.pop("s_pwd")
    smtp_server = "mail.tansuotv.com"


    msg = MIMEText(msg_detail, 'plain', 'utf-8')
    msg['From'] = formataddr(parseaddr('小K视频监控 <%s>' % from_addr))
    msg["To"] = formataddr(parseaddr(to_addr))
    msg['Subject'] = Header('小K下载日报 - %s' % (datetime.now() + timedelta(days=-1)).strftime("%Y-%m-%d"), 'utf-8').encode()

    server = smtplib.SMTP(smtp_server, 25)
    server.login(from_addr, password)
    server.sendmail(from_addr, to_addr, msg.as_string())
    server.quit()


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: python3 %s sender@hostname sender_password receivers1 receivers2" % sys.argv[0])
        sys.exit(1)
    s_addr,s_pwd = sys.argv[1:3]
    receivers = sys.argv[3:]
    sendMail(s_addr=s_addr,s_pwd=s_pwd,receivers=receivers,msg=getData())