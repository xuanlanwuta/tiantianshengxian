from django.contrib.auth.decorators import login_required

class LoginRequiredMixin(object):
    """封装login_required装饰器装饰类视图调用as_view()的结果"""

    @classmethod
    def as_view(cls, **initkwargs):
        """重写父类的as_view()"""

        # 得到类视图调用as_view()后的结果
        view = super().as_view(**initkwargs)
        # login_required装饰器进行装饰
        return login_required(view)