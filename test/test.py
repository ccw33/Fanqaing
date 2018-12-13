#encoding:utf-8
import math
import re

import requests

from Utils import scribe_utils


proxy_type='socks5'
ip_with_port='216.144.230.233:15993' # 连接不是隐私连接
ip_with_port='123.206.56.247:1080' # 成功但认为是机器人
# ip_with_port='125.227.69.220:3347' # 成功
# ip_with_port='103.216.82.148:6667' # 超时
# ip_with_port = '91.142.208.125:9910' #机器人验证
# ip_with_port = '188.120.239.196:12249' #机器人验证,但是检测不到
ip_with_port = '188.120.228.252:32773'


def test():
    resp = requests.get('https://www.google.com/', headers=scribe_utils.headers,
                        proxies={'http': proxy_type + (
                            'h' if proxy_type == 'socks5' else '') + '://' + ip_with_port,
                                 'https': proxy_type + (
                                     'h' if proxy_type == 'socks5' else '') + '://' + ip_with_port},
                        timeout=10)
    # if not re.findall(r'input value=\"Google',resp.text):
    #     raise scribe_utils.RobotException()

    use_time = resp.elapsed.microseconds / math.pow(10, 6)
    location = scribe_utils.get_location(ip_with_port.split(':')[0])
    a = 1

if __name__ == "__main__":
    test()