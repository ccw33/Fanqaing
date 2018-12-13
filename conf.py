# encoding:utf-8
import platform
from configparser import ConfigParser

import os


# driver_type = 'chrome'
# mode = 'product'  # mode: 如果为‘debug’显示浏览器，如果为‘product’则不像是浏览器


class ConfigClass:
    def __init__(self, path):
        self.path = path
        self.cf = ConfigParser()
        self.cf.read(self.path)

    def get(self, field, key):
        self.cf.read(self.path)
        result = self.cf.get(field, key)
        return result

    def set(self, field, key, value):
        self.cf.set(field, key, value)
        self.cf.write(open(self.path, 'w'))
        return True

    # def __getattr__(self, key):
    #     '''
    #     通过Conf.获取的时候，就是读取默认配置
    #     :param attr:
    #     :return:
    #     '''
    #     self.get(self.cf.default_section, key)
    #
    # def __setattr__(self, key, value):
    #     '''
    #     通过Conf.设置的时候，就是设置默认配置
    #     :param key:
    #     :param value:
    #     :return:
    #     '''
    #     self.set(self.cf.default_section,key,value)

    def get_system(self):
        return platform.system().lower()


Conf = ConfigClass('{0}/config.ini'.format(os.getcwd()))
