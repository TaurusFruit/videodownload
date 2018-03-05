#!/usr/bin/env python3

devices_log = "/Data/webapps/video_log/device.log"

with open(devices_log) as f:
        fd = f.readlines()

import re

url_compile = re.compile(r'^\d+.+?D/VooleEpg2.+AdPlayer.+\[CDATA\[(?P<url>http://.+aid\":\"(?P<aid>\w+)\".+\"sid\":\"(?P<sid>\w+).+proto=5&up=\'ua=\w+&ub=\w+&ud=\w+&ug=\w+\')\]\].+$')

for i in fd:
        u_data = url_compile.match(i)
        if u_data:
                video_data = u_data.groupdict()

print(video_data)
import requests

try:
        h_res = requests.get(video_data['url'].replace("127.0.0.1","10.20.40.214"),timeout=10)
        print(h_res.text)
except:
        print('null')
