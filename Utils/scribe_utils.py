# coding:utf-8
import threading

import requests
from bs4 import BeautifulSoup
# from selenium import webdriver
# from selenium.webdriver.common.proxy import Proxy, ProxyType
# from selenium.common import exceptions
# from selenium.webdriver.firefox.firefox_binary import FirefoxBinary
# from selenium.webdriver.common.by import By
# from selenium.webdriver.support.ui import WebDriverWait
# import pymongo

import random
import time
import logging
import re
from multiprocessing import Pool
import traceback
import functools
import pickle
import math

from Utils.log_utils import logger

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/64.0.3282.186 Safari/537.36"
}

lock = threading.Lock()
lock2 = threading.Lock()



class RobotException(Exception):
    '''
    需要机器人验证时抛出这个错
    '''
    def __init__(self, *args,message='需要机器人验证', **kwargs):
        super(RobotException,self).__init__(*args, **kwargs)
        self.message = message

class HashableDict(dict):
    def __eq__(self, other):
        return self['ip_with_port']==other['ip_with_port']

    def __ne__(self, other):
        return not self.__eq__(other)


    def __hash__(self):
        if 'ip_with_port' in self:
            return hash(self['ip_with_port'])
        else:
            raise Exception('dict对象' + self + '缺少key：ip_with_port')

def get_useful_ip(ip_with_port, proxy_type, ip_list=None, fanqiang_ip_list=None, timeout=10, type_get='request'):
    '''
    :param ip_with_port: Required
    :param proxy_type: Required
    :param ip_list: 如果传list，则会验证出普通ip_list,否则不会
    :param fanqiang_ip_list: 如果传list，则会验证出普通ip_list,否则不会
    :param timeout: 验证时的timeout时长，默认10
    :param type_get: 如果是’request'则是用requests来get，否则用selenium，默认request
    :return: ip_list,fanqiang_ip_list
    '''
    logger.debug('get_useful_ip:  ' + proxy_type + '-----' + ip_with_port)
    try:
        if isinstance(ip_list, list):
            resp = requests.get('http://www.baidu.com/', headers=headers,
                                proxies={'http': proxy_type + (
                                'h' if proxy_type == 'socks5' else '') + '://' + ip_with_port,
                                         'https': proxy_type + (
                                         'h' if proxy_type == 'socks5' else '') + '://' + ip_with_port},
                                timeout=timeout)
            use_time = resp.elapsed.microseconds/math.pow(10,6)
            if resp.status_code == 200:
                lock.acquire()
                try:
                    ip_list.append({'proxy_type': proxy_type, 'ip_with_port': ip_with_port,
                                    'time': use_time,'location':get_location(ip_with_port.split(':')[0])})
                    # ip_list.append({'proxy_type': proxy_type, 'ip_with_port': ip_with_port,
                    #                 'time': use_time})
                finally:
                    lock.release()
            else:
                logger.debug('失败：' + proxy_type + ':' + ip_with_port + ' status_code:' + str(resp.status_code))
                pass

        if isinstance(fanqiang_ip_list, list) and proxy_type == 'socks5':
            resp = requests.get('http://www.google.com/', headers=headers,
                                proxies={'http': proxy_type + (
                                'h' if proxy_type == 'socks5' else '') + '://' + ip_with_port,
                                         'https': proxy_type + (
                                         'h' if proxy_type == 'socks5' else '') + '://' + ip_with_port},
                                timeout=timeout)
            use_time = resp.elapsed.microseconds/math.pow(10,6)
            if resp.status_code == 200:
                lock2.acquire()
                try:
                    fanqiang_ip_list.append(
                        {'proxy_type': proxy_type, 'ip_with_port': ip_with_port,
                         'time': use_time,'location':get_location(ip_with_port.split(':')[0])})
                    # fanqiang_ip_list.append(
                    #     {'proxy_type': proxy_type, 'ip_with_port': ip_with_port,
                    #      'time': use_time})
                finally:
                    lock2.release()
            else:
                logger.debug('失败：' + proxy_type + ':' + ip_with_port + ' status_code:' + str(resp.status_code))
    except Exception as e:
        logger.debug('失败：' + proxy_type + ':' + ip_with_port + str(e))
        pass
    return ip_list, fanqiang_ip_list


# def get_ip_list(GFW=False):
#     # # 获取昨天爬取的ip
#     # yes_time = (datetime.datetime.now()+datetime.timedelta(days=-1)).strftime('%Y-%m-%d')
#     # a = ipsData.find_one({'date': yes_time,})
#
#     # url = 'http://www.66ip.cn/areaindex_35/1.html'
#     # selector = 'tr'
#     # ip_list = normal_scribe(url, selector)
#     # 获取最近爬到的ip
#     # 初始化数据库
#     # client = pymongo.MongoClient('localhost', 27017)
#     ips = client['ips']
#     ipsData = ips['ipsData']
#     ipsFanqiangData = ips['ipsFanqiangData']
#     client.close()
#     try:
#         a = list(ipsData.find() if not GFW else ipsFanqiangData.find())[-1]
#         return a['ip_list'] if not GFW else a['ip_fanqiang_list']
#     except IndexError as e:
#         #     没有已经爬到了的ｉｐ
#         url = 'http://www.66ip.cn/areaindex_35/1.html'
#         selector = 'tr'
#         ip_list, ip_fanqiang_list = normal_scribe(url, selector)
#         return ip_list if not GFW else ip_fanqiang_list


def normal_scribe(url, selector):
    ip_list = []
    resp = requests.get(url)
    soup = BeautifulSoup(resp.text, 'lxml')
    trs = soup.select(selector)
    new_ip_list = []
    new_fanqiang_list = []
    for tr in trs:
        ip = re.search(r'(?:>)(\d+\.){3}\d{1,3}(?:<)', str(tr), re.M)
        port = re.search(r'(?:>)\d{3,5}(?:<)', str(tr), re.M)
        if ip and port:
            ip = re.search(r'(\d+\.){3}\d{1,3}', ip.group())
            port = re.search(r'\d+', port.group())
            ip_with_port = ip.group() + ':' + port.group()
            get_useful_ip(ip_with_port, 'http', new_ip_list, new_fanqiang_list)
            # ip_list.append({'proxy_type': 'http', 'ip_with_port': ip_with_port})

    return new_ip_list, new_fanqiang_list


# ip_list = get_ip_list()


# ip定位：
def get_location(ip):
    '''
    ip定位并返回{'region': '地区：Europa(欧洲)', 'country': '国家：Russia(俄罗斯) ，简称:RU', 'province': '洲／省：Bashkortostan', 'city': '城市：Ufa', 'rect': '经度：56.0456，纬度54.7852', 'timezone': '时区：Asia/Yekaterinburg', 'postcode': '邮编:450068'}
    :param ip:
    :return:
    '''
    import geoip2.database
    reader = geoip2.database.Reader('file/GeoLite2-City_20180501/GeoLite2-City.mmdb')
    ip = ip
    response = reader.city(ip)
    # # 有多种语言，我们这里主要输出英文和中文
    # print("你查询的IP的地理位置是:")
    #
    # print("地区：{}({})".format(response.continent.names["es"],
    #                          response.continent.names["zh-CN"]))
    #
    # print("国家：{}({}) ，简称:{}".format(response.country.name,
    #                                 response.country.names["zh-CN"],
    #                                 response.country.iso_code))
    #
    # print("洲／省：{}({})".format(response.subdivisions.most_specific.name,
    #                           response.subdivisions.most_specific.names["zh-CN"]))
    #
    # print("城市：{}({})".format(response.city.name,
    #                          response.city.names["zh-CN"]))
    #
    # # print("洲／省：{}".format(response.subdivisions.most_specific.name))
    # #
    # # print("城市：{}".format(response.city.name))
    #
    # print("经度：{}，纬度{}".format(response.location.longitude,
    #                           response.location.latitude))
    #
    # print("时区：{}".format(response.location.time_zone))
    #
    # print("邮编:{}".format(response.postal.code))

    data = {
        'region': "地区：{}({})".format(response.continent.names["es"],
                                     response.continent.names["zh-CN"]),
        'country': "国家：{}({}) ，简称:{}".format(response.country.name,
                                             response.country.names["zh-CN"],
                                             response.country.iso_code),
        'province': "洲／省：{}".format(response.subdivisions.most_specific.name),
        'city': "城市：{}".format(response.city.name),
        'rect': "经度：{}，纬度{}".format(response.location.longitude,
                                    response.location.latitude),
        'timezone': "时区：{}".format(response.location.time_zone),
        'postcode': "邮编:{}".format(response.postal.code)
    }
    return data


def test_elite(ip_with_port,proxy_type)->dict or None:
    '''
    验证是否匿名
    :param ip_with_port: 如 '192.155.135.21:466'
    :param proxy_type: 如 'socks5'
    :return:
    '''
    try:
        resp = requests.get('https://whoer.net/zh', headers=headers,
                            proxies={'http': proxy_type + (
                                'h' if proxy_type == 'socks5' else '') + '://' + ip_with_port,
                                     'https': proxy_type + (
                                         'h' if proxy_type == 'socks5' else '') + '://' + ip_with_port},
                            timeout=10)
        soup = BeautifulSoup(resp.text, 'lxml')
        tags = soup.select('.your-ip')
        ip = tags[0].text
        if not ip:
            return
        the_ip = ip_with_port.split(':')[0]
        if not ip == the_ip:
            location = get_location(ip)
            print("%s匿名，表现地址为：%s" % (the_ip,ip))
            return {'ip':ip,'location':location}
        else:
            print("%s不匿名" % the_ip)
            return
    except (requests.exceptions.ConnectionError, requests.ReadTimeout \
                    , requests.exceptions.SSLError, RobotException) as e:
        print(str(e))
        return

def add_url_prefix(url, prefix='https:'):
    '''
    自动判断是否缺前缀，如果缺了就加上去并返回
    :param url:
    :param prefix:
    :return:
    '''
    return url if re.findall(re.compile(prefix), url) else prefix + url



