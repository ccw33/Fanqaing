import json
import xmlrpc.client
from xmlrpc.client import MultiCall, Error, _Method


class _MyMethod(_Method):
    # def __init__(self,send, name):
    #     super(_MyMethod,self).__init__(send, name)

    def __init__(self, send, name):
        '''

        :param send:
        :param name:
        :param args:
        :param kwargs: 目前这个参数没用，因为xmlrpc不支持
        '''
        self.__send = send
        self.__name = name
        # self._args = args
        # self._kwargs = kwargs

    def __getattr__(self, name):
        '''
        自动将server.a.b.c转成字符串
        :param name:
        :return:
        '''
        return _MyMethod(self.__send, "%s.%s" % (self.__name, name))

    def __call__(self, *args, **kwargs):
        '''
        自动将server.A().B()转成字符串
        :param args:
        :param kwargs: 目前这个参数没用，因为xmlrpc不支持
        :return:
        '''
        # 为了能兼容父类方法，send和name都用私有的，所以获取的时候会有类前缀
        name = self._MyMethod__name
        try:
            name.index(')', -1, len(name))
        except ValueError:
            # 如果不是类似server.A()()的调用，就直接返回"server.A()"
            return _MyMethod(self.__send,
                             '{0}({1}{2})'.format(name,
                                                  ','.join([json.dumps(arg) for arg in args]),
                                                  '{0}{1}'.format(',' if kwargs else '', ','.join(
                                                      ['{0}={1}'.format(k, v) for k, v in
                                                       kwargs.items()]))))
        # 如果是类似server.A()()的调用，就调用远程的server.A()

        return self.__send(name[0:-2], args)

    def __repr__(self):
        return self.__name


class MyServerProxy(xmlrpc.client.ServerProxy):

    def __getattr__(self, name):
        # magic method dispatcher #强制调用父类方法
        return _MyMethod(super(MyServerProxy, self)._ServerProxy__request, name)


# server = MyServerProxy('http://119.29.134.163:9017')


server = xmlrpc.client.ServerProxy('http://119.29.134.163:9080')


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




# Print list of available methods
print(server.system.listMethods())
# print(server.system.methodHelp())
# print(server.system.methodSignature())
try:
    print(Transformer().A().a.done())
    print(Transformer().A().aa('你麻痹').done())
    print(server.run(Transformer().A().a.done()))
    print(server.run(Transformer().A().aa('你他妈').done()))
    print(server.run(Transformer().ss.done()))

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
