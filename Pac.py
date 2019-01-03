# encoding:utf-8

# from model.fangqiang import ip
# from Server.Service import fanqiang_ip_service

import traceback
import random
import math
# import pymongo
import re
from functools import reduce

import pickle
import requests
import time
# from queue import Queue,Empty
from bs4 import BeautifulSoup
import queue
import threading
import logging

from RPC.RPC_Client import SERVERS_FOR_CLIENT
from Utils import scribe_utils, thread_utils, git_utils
from Utils.log_utils import logger
# from selenium.webdriver.common.keys import Keys
# from selenium.common import exceptions
import os

from RPC.RPC_Client import Transformer, MyServerProxy

db_client = MyServerProxy(SERVERS_FOR_CLIENT.DB)

Git = git_utils.Git()
# Fanqiang = ip.Fanqiang()

io_lock = threading.Lock()
lock = threading.Lock()

file_path = 'E:/git-repository/blog/ccw33.github.io/file/http_surge.pac'
file_path_chrome = 'E:/git-repository/blog/ccw33.github.io/file/OmegaProfile_auto_switch.pac'
file_path_chrome_socks = 'E:/git-repository/blog/ccw33.github.io/file/OmegaProfile_socks.pac'

is_ok_at_least_one = False

useful_proxy_in_mongo = []


def generate_replace_text(ip_fanqiang_list):
    new_proxy_list = ["%s%s = %s,%s\n" % (
        ip['proxy_type'], str(index), ip['proxy_type'] if ip['proxy_type'] == 'http' else 'socks5',
        ip['ip_with_port'].replace(':', ',')) for index, ip in enumerate(ip_fanqiang_list)]
    new_proxy_group = [s.split('=')[0] for s in new_proxy_list]
    return (reduce(lambda v1, v2: v1 + v2, new_proxy_list), reduce(lambda v1, v2: v1 + ',' + v2, new_proxy_group) + ',')


class FanqiangService():
    # 修改pac文件并commit到github

    def update_surge_pac(self):
        '''
        更新surge用的pac
        :return:
        '''
        #
        # ip_fanqiang_list = list(Fanqiang.query())
        # if len(ip_fanqiang_list) < 7:
        #     pass
        # else:
        #     start = math.floor(random.random() * len(ip_fanqiang_list))
        #     ip_fanqiang_list = ip_fanqiang_list[start:start + 5]

        if not useful_proxy_in_mongo:
            raise Exception("请先执行 update_chrome_pac 再执行 update_surge_pac")
        ip_fanqiang_list = useful_proxy_in_mongo

        # 读取文件
        old_text = ''
        new_text = ''
        with open(file_path, 'r', encoding='utf-8') as fr:
            try:
                old_text = fr.read()
                proxy_replace_text, group_replace_text = generate_replace_text(ip_fanqiang_list)
                new_text = old_text.replace(re.findall(r'\[Proxy\]\n((?:.+\n)+)Socks1',
                                                       old_text)[0], proxy_replace_text)
                new_text = new_text.replace(
                    re.findall(
                        r'\[Proxy Group\]\nProxy = url-test, (.+) url = http://www.google.com/generate_204\nSocks_Proxy',
                        new_text)[0], group_replace_text)
            finally:
                fr.close()

        # 修改文件
        with open(file_path, 'w', encoding='utf-8') as fw:
            try:
                fw.write(new_text)
            finally:
                fw.close()
        Git.git_push(file_path)

    def update_chrome_pac(self):
        '''
        检查mongodb里面的ip——port,调用update_chrome_pac_by_gatherproxy(),更新到数据库,并更新chrome用的pac
        :return:
        '''

        ip_fanqiang_list = list(db_client.run(Transformer().Fanqiang().query()).done())
        if len(ip_fanqiang_list) < 7:
            pass
        else:
            start = math.floor(random.random() * len(ip_fanqiang_list))
            ip_fanqiang_list = ip_fanqiang_list[start:]

        q = queue.Queue()
        for ip_dict in ip_fanqiang_list:
            q.put(ip_dict)
        for i in range(20):
            t = threading.Thread(target=self.__get_useful_fanqiang_ip_mongo_worker, args=(q,))
            t.start()
        q.join()

    def update_chrome_pac_by_gatherproxy(self):
        '''
        从proxies.txt里面检测ip_port，最后更新chrome用的pac
        :return:
        '''
        FileService.merge_proxy()
        with open('file/proxy_file/proxies.txt', 'r') as fr:
            try:
                ip_port_list = fr.read().split('\n')
            except Exception:
                logger.error(traceback.format_exc())
                return
            finally:
                fr.close()

        q = queue.Queue()
        ip_port_list = list(set(ip_port_list))  # 去重
        for ip_with_port in ip_port_list:
            ip_dict = {
                'ip_with_port': ip_with_port,
                'proxy_type': 'socks5',
            }
            q.put(ip_dict)

        for i in range(20):
            t = threading.Thread(target=self.__get_useful_fanqiang_ip_gatherproxy_worker, args=(q,))
            t.start()
        q.join()
        # 跑完，吧proxy文件删了
        os.remove('file/proxy_file/proxies.txt')

    @staticmethod
    def test_elite(ip_with_port, proxy_type) -> dict or None:
        '''
        验证是否匿名
        :param ip_with_port: 如 '192.155.135.21:466'
        :param proxy_type: 如 'socks5'
        :return:
        '''
        try:
            resp = requests.get('https://whoer.net/zh', headers=scribe_utils.headers,
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
                location = FanqiangService.get_location(ip)
                print("%s匿名，表现地址为：%s" % (the_ip, ip))
                return {'ip': ip, 'location': location}
            else:
                print("%s不匿名" % the_ip)
                return
        except (requests.exceptions.ConnectionError, requests.ReadTimeout \
                        , requests.exceptions.SSLError, scribe_utils.RobotException) as e:
            print(str(e))
            return

    @staticmethod
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

    def __get_useful_fanqiang_ip_mongo_worker(self, q):
        while not q.empty():
            driver = None

            try:
                ip_dict = q.get()
                proxy_type = ip_dict['proxy_type']
                ip_with_port = ip_dict['ip_with_port']
                logger.debug("开始测试" + ip_with_port)
                resp = requests.get('https://www.google.com/', headers=scribe_utils.headers,
                                    proxies={'http': proxy_type + (
                                        'h' if proxy_type == 'socks5' else '') + '://' + ip_with_port,
                                             'https': proxy_type + (
                                                 'h' if proxy_type == 'socks5' else '') + '://' + ip_with_port},
                                    timeout=10)
                try:
                    lock.acquire()
                    useful_proxy_in_mongo.append(ip_dict)
                finally:
                    lock.release()

                # if not re.findall(r'input value=\"Google',resp.text):
                #     raise scribe_utils.RobotException()

                # try:
                #     elite = FanqiangService.test_elite(ip_dict['ip_with_port'], ip_dict['proxy_type'])
                #     if elite:
                #         Fanqiang.update({'Elite': elite}, {'ip_with_port': ip_dict['ip_with_port']})
                # except Exception as e:
                #     logger.warning(traceback.format_exc())

                logger.debug(ip_with_port + "可用")
                self.modify_chrome_pac_file_and_push(ip_with_port)

            except (scribe_utils.RobotException, \
                    requests.exceptions.ConnectionError, requests.ReadTimeout, requests.exceptions.SSLError) as e:
                try:
                    lock.acquire()
                    new_disable_times = ip_dict['disable_times'] + 1
                    db_client.run(
                        Transformer().Fanqiang().update({'disable_times': new_disable_times},
                                                        {'_id': ip_dict['_id']}).done())
                except Exception as e:
                    logger.info(e)
                finally:
                    lock.release()
                continue
            except Exception as e:
                try:
                    lock.acquire()
                    new_disable_times = ip_dict['disable_times'] + 1
                    db_client.run(
                        Transformer().Fanqiang().update({'disable_times': new_disable_times},
                                                        {'_id': ip_dict['_id']}).done())
                except Exception as e:
                    logger.info(e)
                finally:
                    lock.release()
                if driver:
                    driver.quit()
                if re.findall(r'NoneType', str(e)):
                    continue
                if not isinstance(e, ValueError):
                    logger.warning(traceback.format_exc())
                continue
            finally:
                q.task_done()

    def __get_useful_fanqiang_ip_gatherproxy_worker(self, q):
        while not q.empty():
            driver = None
            try:
                ip_dict = q.get()
                proxy_type = ip_dict['proxy_type']
                ip_with_port = ip_dict['ip_with_port']
                logger.debug("开始测试" + ip_with_port)
                resp = requests.get('https://www.google.com/', headers=scribe_utils.headers,
                                    proxies={'http': proxy_type + (
                                        'h' if proxy_type == 'socks5' else '') + '://' + ip_with_port,
                                             'https': proxy_type + (
                                                 'h' if proxy_type == 'socks5' else '') + '://' + ip_with_port},
                                    timeout=10)
                # if not re.findall(r'input value=\"Google',resp.text):
                #     raise scribe_utils.RobotException()
                use_time = resp.elapsed.microseconds / math.pow(10, 6)

                logger.debug(ip_with_port + "可用")
                elite = FanqiangService.test_elite(ip_dict['ip_with_port'], ip_dict['proxy_type'])
                try:
                    lock.acquire()
                    if elite:
                        db_client.run(
                            Transformer().Fanqiang().save({'proxy_type': proxy_type, 'ip_with_port': ip_with_port,
                                                           'time': use_time,
                                                           'location': FanqiangService.get_location(
                                                               ip_with_port.split(':')[0]),
                                                           'Elite': elite}).done())
                    else:
                        db_client.run(
                            Transformer().Fanqiang().save({'proxy_type': proxy_type, 'ip_with_port': ip_with_port,
                                                           'time': use_time,
                                                           'location': FanqiangService.get_location(
                                                               ip_with_port.split(':')[0])}).done())
                except Exception as e:
                    logger.info(e)
                finally:
                    lock.release()
                    # 更新pac
                    # self.modify_chrome_pac_file_and_push(ip_with_port)

            except (requests.exceptions.ConnectionError, requests.ReadTimeout \
                            , requests.exceptions.SSLError, scribe_utils.RobotException) as e:
                continue
            # except exceptions.TimeoutException as e:  # 浏览器访问超时
            #     driver.quit()
            #     continue
            except Exception as e:
                if driver:
                    driver.quit()
                if re.findall(r'NoneType', str(e)):
                    continue
                if not isinstance(e, ValueError):
                    logger.warning(traceback.format_exc())
                continue
            finally:
                q.task_done()

    # -------------------------- 这里后面开始才是新版用到的 -------------------------------------

    def __disable_plus_1(self, ip_dict):
        '''
        mongodb中相应的数据不可用次数加一
        :param ip_dict:
        :return:
        '''
        new_disable_times = ip_dict['disable_times'] + 1
        db_client.run(
            Transformer().Fanqiang().update({'disable_times': new_disable_times},
                                            {'_id': ip_dict['_id']}).done())

    def __disable_minus_1(self, ip_dict):
        '''
        mongodb中相应的数据不可用次数加一
        :param ip_dict:
        :return:
        '''
        if ip_dict['disable_times']<=0:
            return
        new_disable_times = ip_dict['disable_times'] - 1
        db_client.run(
            Transformer().Fanqiang().update({'disable_times': new_disable_times},
                                            {'_id': ip_dict['_id']}).done())

    def test_useful_fanqiang(self, ip_dict):
        '''
        测试该代理能否翻墙（socks5代理）
        :return:
        '''
        try:
            proxy_type = ip_dict['proxy_type']
            ip_with_port = ip_dict['ip_with_port']
            logger.debug("开始测试" + ip_with_port)
            resp = requests.get('https://www.youtube.com/', headers=scribe_utils.headers,
                                proxies={'http': proxy_type + (
                                    'h' if proxy_type == 'socks5' else '') + '://' + ip_with_port,
                                         'https': proxy_type + (
                                             'h' if proxy_type == 'socks5' else '') + '://' + ip_with_port},
                                timeout=2)
            logger.debug(ip_with_port + "------------------可用")
            use_time = resp.elapsed.microseconds / math.pow(10, 6)
            ip_dict['time'] = use_time
            db_client.run(
                Transformer().Fanqiang().update(ip_dict,{'_id':ip_dict['_id']}).done())
            self.__disable_minus_1(ip_dict)
            return True
        except (scribe_utils.RobotException, \
                requests.exceptions.ConnectionError, requests.ReadTimeout, requests.exceptions.SSLError) as e:
            try:
                # if ip_dict['disable_times']>10:
                #     db_client.run(Transformer().Fanqiang().delete({'_id': ip_dict['_id']}).done())
                # else:
                    self.__disable_plus_1(ip_dict)
            except Exception as e:
                logger.info(e)
            finally:
                return False
        except Exception as e:
            try:
                # if ip_dict['disable_times']>10:
                #     db_client.run(Transformer().Fanqiang().delete({'_id': ip_dict['_id']}).done())
                # else:
                    self.__disable_plus_1(ip_dict)
            except Exception as e:
                logger.info(e)
            finally:
                return False

    def get_useful_fanqiang_ip_port_from_mongo(self, n) -> list:
        '''
        获取n个能翻墙的ip_dict(从mongo)
        :param n:
        :return:
        '''

        def put_to_chosen_if_useful(ip_port_dict):
            '''
            线程调用的函数，如果可用就放进chosen_list里面
            :param ip_port_dict:
            :param chosen_list:
            :return:
            '''
            if self.test_useful_fanqiang(ip_port_dict):
                chosen_list.append(ip_port_dict)

        # ip_fanqiang_list = pickle.loads(db_client.to_list(Transformer().Fanqiang().query({'disable_times':{'$lt':10}}).done()).data)
        ip_fanqiang_list = pickle.loads(db_client.to_list(Transformer().Fanqiang().query().done()).data)
        list_len = len(ip_fanqiang_list)
        chosen_list = []
        picked_index = []
        try_times = 0
        max_try_times = list_len//(n*3)
        while n-len(chosen_list)>0:#循环是因为不一定一遍就抓完n条可用的
            try_times+=1
            threads = []
            # 获取n条可用的ip_port_dict
            for i in range(n*3):
                index = math.floor(random.random() * list_len)
                while index in picked_index:
                    index += 1
                    if index >= list_len - 1:
                        index = 0
                picked_index.append(index)
                # 测试是否可用,可用就自动放进chosen_list
                t = threading.Thread(target=put_to_chosen_if_useful, args=(ip_fanqiang_list[index],))
                threads.append(t)
            for t in threads:
                t.start()
            for t in threads:
                t.join()
            if try_times>max_try_times:
                break
        chosen_list =sorted(chosen_list,key=lambda x:x['time'])
        return chosen_list[:n]





class FileService():
    '''
    专门处理文件读写
    '''

    def save_all_from_gatherproxy_to_db(self):
        '''
        保存收集到的所有的gather_proxydoa数据库，不筛选
        :return:
        '''
        self.merge_proxy()
        with open('file/proxy_file/proxies.txt', 'r') as fr:
            try:
                ip_port_list = fr.read().split('\n')
            except Exception:
                logger.error(traceback.format_exc())
                return
            finally:
                fr.close()

        def save(ip_with_port, proxy_type):
            try:
                elite = FanqiangService.test_elite(ip_with_port, proxy_type)
            except Exception as e:
                logger.info(str(e))
                return

            try:
                lock.acquire()
                if elite:
                    db_client.run(Transformer().Fanqiang().save({'proxy_type': proxy_type, 'ip_with_port': ip_with_port,
                                                                 'time': 0.00, 'location': FanqiangService.get_location(
                            ip_with_port.split(':')[0]),
                                                                 'Elite': elite}).done())
                else:
                    db_client.run(Transformer().Fanqiang().save({'proxy_type': proxy_type, 'ip_with_port': ip_with_port,
                                                                 'time': 0.00, 'location': FanqiangService.get_location(
                            ip_with_port.split(':')[0])}).done())
            except Exception as e:
                logger.error(e)
            finally:
                lock.release()

        q = queue.Queue()
        tf = thread_utils.ThreadFactory()
        for i in range(20):
            t = threading.Thread(target=tf.queue_threads_worker, args=(q, save))
            t.start()
        for ip_with_port in ip_port_list:
            q.put({'ip_with_port': ip_with_port, 'proxy_type': 'socks5'})
        q.join()
        tf.all_task_done = True
        os.remove('file/proxy_file/proxies.txt')

    def modify_chrome_pac_file_and_push(self, ip_with_port):
        '''
        更新pac文件并提交（加锁）
        :param ip_with_port:
        :return:
        '''

        def modify_chrome_file(file_path, ip_with_port):
            # 替换ip和port
            new_text = ''
            with open(file_path,
                      'r', encoding='utf-8') as fr:
                try:
                    old_text = fr.read()
                    new_text = old_text.replace(re.findall(r'(?:SOCKS |SOCKS5 )(\d+\.\d+\.\d+\.\d+:\d+)', old_text)[0],
                                                ip_with_port)
                    new_text = new_text.replace(re.findall(r'(?:SOCKS |SOCKS5 )(\d+\.\d+\.\d+\.\d+:\d+)', old_text)[1],
                                                ip_with_port)
                finally:
                    fr.close()

            with open(file_path,
                      'w', encoding='utf-8') as fw:
                try:
                    fw.write(new_text)
                finally:
                    fw.close()
            logger.debug("已更新文件 %s,ip_port为：%s" % (file_path, ip_with_port))

        try:
            io_lock.acquire()
            global is_ok_at_least_one
            if is_ok_at_least_one:
                return
            modify_chrome_file(file_path_chrome, ip_with_port)
            modify_chrome_file(file_path_chrome_socks, ip_with_port)

            Git.git_push(file_path_chrome)
            Git.git_push(file_path_chrome_socks)

            is_ok_at_least_one = True
            return

        except Exception:
            logger.error(traceback.format_exc())
        finally:
            io_lock.release()

    @staticmethod
    def merge_proxy():
        '''
        合并proxy文件
        :return:
        '''

        for root, dirs, files in os.walk("file/proxy_file"):
            logger.debug(root)  # 当前目录路径
            logger.debug(dirs)  # 当前路径下所有子目录
            logger.debug(files)  # 当前路径下所有非目录子文件
            with open(root + '/proxies.txt',
                      'a+', encoding='utf-8') as fw:
                try:
                    all_ip_port_list = []
                    for file_name in files:
                        if file_name == 'proxies.txt':
                            continue
                        with open(root + "/" + file_name,
                                  'r', encoding='utf-8') as fr:
                            try:
                                all_ip_port_list.extend(fr.readlines())
                            finally:
                                fr.close()
                        os.remove(root + "/" + file_name)
                    all_ip_port_list = list(set(all_ip_port_list))  # 去重
                    fw.writelines(all_ip_port_list)
                finally:
                    fw.close()


if __name__ == "__main__":
    # while True:
    #     update_surge_pac()
    #     update_chrome_pac()
    #     update_chrome_pac_by_gatherproxy()
    #     logger.debug('DONE!!!')
    #     time.sleep(3600*6)

    # fanqiang = FanqiangService()
    # fanqiang.update_chrome_pac()
    # update_chrome_pac_by_gatherproxy()
    # fanqiang.update_chrome_pac_by_gatherproxy()
    # fanqiang.update_surge_pac()

    # file_service = FileService()
    # file_service.save_all_from_gatherproxy_to_db()
    # logger.debug('DONE!!!')
    # a = db_client.to_list(Transformer().Fanqiang().query().done())
    # b = pickle.loads(a.data)
    fanqiang_list = FanqiangService().get_useful_fanqiang_ip_port_from_mongo(7)
    a = 2
