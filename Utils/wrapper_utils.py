#encoding:utf-8
'''
装饰器类都在这
'''

import functools

from Server.Service import user_service

from flask import Response


def login_checker(request):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kw):
            # 验证用户
            account = request.args['account']
            password = request.args['password']
            vertify_pass, not_pass_reason = user_service.vertify_user(account, password)[:2]
            if not vertify_pass:
                return Response(not_pass_reason, status=401)
            return func(*args, **kw)

        return wrapper

    return decorator

class RequestWrapperFactory():

    @staticmethod
    def login_checker(request):
        def decorator(func):
            @functools.wraps(func)
            def wrapper(*args, **kw):
                # 验证用户
                account = request.args['account']
                password = request.args['password']
                vertify_pass, not_pass_reason = user_service.vertify_user(account, password)[:2]
                if not vertify_pass:
                    return Response(not_pass_reason, status=401)
                return func(*args, **kw)
            return wrapper
        return decorator