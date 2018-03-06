from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from functools import wraps
from django.db import transaction


class LoginRequiredMixin(object):
    """封装login_required装饰器装饰类视图调用as_view()的结果"""

    @classmethod
    def as_view(cls, **initkwargs):
        """重写父类的as_view()"""

        # 得到类视图调用as_view()后的结果
        view = super().as_view(**initkwargs)
        # login_required装饰器进行装饰
        return login_required(view)


def login_required_json(view_func):
    """自定义跟json交互的LoginRequired装饰器"""

    @wraps(view_func)
    def wrapper(request, *args, **kwargs):

        if not request.user.is_authenticated():
            # 如果用户未登录，响应json给前端,引导用户到登陆页面
            return JsonResponse({'code':1, 'message':'用户未登录'})
        else:
            # 如果用户已登录，执行视图内部的逻辑
            return view_func(request, *args, **kwargs)

    return wrapper


class LoginRequiredJsonMixin(object):
    """封装跟json交互的LoginRequired装饰器的类"""

    @classmethod
    def as_view(cls, **initkwargs):
        """重写父类的as_view()"""

        view = super().as_view(**initkwargs)
        return login_required_json(view)


class TransactionAtomicMixin(object):
    """事务装饰器的类"""

    @classmethod
    def as_view(cls, **initkwargs):
        """重写父类的as_view()"""

        view = super().as_view(**initkwargs)
        return transaction.atomic(view)