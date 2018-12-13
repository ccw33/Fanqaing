import json
import xmlrpc.client
from xmlrpc.client import MultiCall, Error, _Method,ServerProxy
from Utils.conf import Conf
from Utils.log_utils import logger

#枚举 rpc server
class SERVERS:
    DB='http://{0}:{1}'.format(Conf.get('DB','ip'),Conf.get('DB','port'))


class MyServerProxy(ServerProxy):
    pass
    # def __getattr__(self, name):
    #     # magic method dispatcher
    #     return _Method(self.__request, name)
    #
    # def __request(self, methodname, params):
    #     try:
    #         return ServerProxy._ServerProxy__request(self,methodname, params)
    #     except Exception as e:
    #         logger.error(e)


class Magic:
    def __init__(self, attr, params_list):
        self.attr = attr
        self.params_list = params_list

    def __getattr__(self, name):
        '''
        自动将server.a.b.c转成字符串
        :param name:
        :return:
        '''
        return Magic('%s.%s' % (self.attr, name),self.params_list)

    def __call__(self, *args, **kwargs):
        '''
        自动将server.A().B()转成字符串
        :param args:
        :param kwargs:
        :return:
        '''
        self.params_list.append({'args': args, 'kwargs': kwargs})
        return Magic('{0}()'.format(self.attr, ),self.params_list)

    def done(self):
        return self.attr, self.params_list

    def __str__(self):
        return self.attr

    def __repr__(self):
        return self.__str__()



class Transformer:

    def __getattr__(self, item):
        return Magic(item,[])


if __name__=="__main__":
    server = MyServerProxy(SERVERS.DB)
    # server = MyServerProxy(SERVERS.DB)
    # Print list of available methods
    print(server.system.listMethods())
    # print(server.system.methodHelp())
    # print(server.system.methodSignature())
    try:
        print(Transformer().Fanqiang().query().sort('time', 1).done())
        print(server.to_list(Transformer().Fanqiang().query().sort('time', 1).done()))
        print(server.run(Transformer().Fanqiang().query().sort('time', 1).done()))
    except Error as v:
        print("ERROR------------", v)

    # # 多个调用一次运行
    # multi = MultiCall(server)
    # multi.getData()
    # # multi.mul(2,3)
    # multi.add(1, 2)
    # try:
    #     for response in multi():
    #         print(response)
    # except Error as v:
    #     print("ERROR", v)
