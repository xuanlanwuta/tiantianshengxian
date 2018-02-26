from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.views.generic import View
from django.core.urlresolvers import reverse
import re
from django import db
from users.models import User, Address
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from django.conf import settings
from itsdangerous import SignatureExpired
from django.contrib.auth import authenticate, login, logout
from celery_tasks.tasks import send_active_email
from utils.views import LoginRequiredMixin


# Create your views here.
class UserInfoView(LoginRequiredMixin, View):
    """用户中心"""

    def get(self, request):
        """查询用户信息和地址信息"""

        # 从request中获取user对象，中间件从验证请求中的用户，所以request中带有user
        user = request.user

        try:
            # 查询用户地址：根据创建时间排序，取第1个地址
            address = user.address_set.latest('create_time')
        except Address.DoesNotExist:
            # 如果地址信息不存在
            address = None

        # 构造上下文
        context = {
            'address': address
        }

        # 渲染模板
        return render(request, 'user_center_info.html', context)

class AddressView(LoginRequiredMixin, View):
    """用户地址信息"""

    def get(self, request):
        """提供用户地址界面"""
        # 获取用户信息user：登陆的用户，django用户认证系统会自动把user存储在request中
        user = request.user
        # 使用user查询其关联的地址信息address,需求是按照时间倒序排序
        try:
            # address = Address.objects.filter(user=user).order_by('-create_time')[0]
            # address = user.address_set.order_by('-create_time')[0]
            address = user.address_set.latest('create_time')
        except Address.DoesNotExist:
            address = None
        # 构造上下文
        context = {
            # request信息中自带user,所以不需要传递
            # 'user':user,
            'address': address
        }
        # 渲染模板
        return render(request, 'user_center_site.html', context)

    def post(self, request):
        """处理用户提交地址逻辑"""
        # 接收用户修改地址信息的请求参数
        recv_name = request.POST.get('recv_name')
        addr = request.POST.get('addr')
        zip_code = request.POST.get('zip_code')
        recv_mobile = request.POST.get('recv_mobile')
        # 校验参数：all()
        if all([recv_name, addr, zip_code, recv_mobile]):
            # 保存用户地址信息
            Address.objects.create(
                user=request.user,
                receiver_name=recv_name,
                receiver_mobile=recv_mobile,
                detail_addr=addr,
                zip_code=zip_code
            )
        # 响应结果：此处的处理重新刷新一下页面，顺便测试新修改的地址是否成功
        return redirect(reverse('users:address'))


class RegisterView(View):
    """类视图：注册"""

    def get(self, request):
        """提供注册页面"""
        return render(request, 'register.html')

    def post(self, request):
        """处理注册逻辑"""
        """获取数据"""
        user_name = request.POST.get('user_name')
        user_pwd = request.POST.get('pwd')
        email = request.POST.get('email')
        allow = request.POST.get('allow')
        """验证"""
        if not all([user_name, user_pwd, email]):
            return redirect(reverse('users:register'))

        if not re.match(r"^[a-z0-9][\w\.\-]*@[a-z0-9\-]+(\.[a-z]{2,5}){1,2}$", email):
            return render(request, 'register.html', {'error': '邮箱格式不正确'})

        if allow != 'on':
            return render(request, 'register.html', {'error': '请勾选用户协议'})

        try:
            user = User.objects.create_user(user_name, email, user_pwd)

        except db.IntegrityError:
            return render(request, 'register.html', {'error': '用户名已注册'})
        print(email)
        user.is_active = False
        user.save()

        token = user.generate_active_token()

        # 8.celery异步发送激活邮件
        send_active_email.delay(email, user_name, token)
        return HttpResponse('收到POST请求，需要处理注册逻辑')


class Activevies(View):
    def get(self, request, token):
        '''获取封装的字典带有user_id'''
        serializer = Serializer(settings.SECRET_KEY, 3600)
        # 解出字典内容
        try:
            result = serializer.load(token)
        except SignatureExpired:  # 签名过期
            return HttpResponse('激活已过期')

        # 获取id
        user_id = result.get('confirm')
        # 查询id
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:  # 用户不存在的异常
            return HttpResponse('用户不存在')
        # 重置激活状态
        user.is_active = True
        user.save()
        return redirect(reverse('users:login'))


class LoginView(View):
    def get(self, request):
        return render(request, 'login.html')

    def post(self, request):
        """处理登陆逻辑"""

        # 1.获取用户登陆数据
        username = request.POST.get('username')
        userpwd = request.POST.get('pwd')
        remembered = request.POST.get('remembered')

        # 2.校验用户登陆数据
        if not all([username, userpwd]):
            return redirect(reverse('users:login'))

        # 3.使用django用户认证系统验证用户
        user = authenticate(username=username, password=userpwd)

        # 4.判断用户是否存在
        if user is None:
            return render(request, 'login.html', {'error': '用户名或密码错误'})

        # 5.验证用户是否是激活用户
        if user.is_active is False:
            return render(request, 'login.html', {'error': '请先激活'})

        # 6.验证用户通过后，登入该用户
        login(request, user)
        remembered = request.POST.get('remembered')
        # 7.记住用户
        if remembered != 'on':
            # 没有记住用户：浏览器关闭就过期
            request.session.set_expiry(0)
        else:
            # 记住用户：None表示两周后过期
            request.session.set_expiry(None)
        next = request.GET.get('next')
        if next == None:
        # 8.响应结果: 重定向到主页
            return redirect(reverse('goods:index'))
        else:
            return reverse(reverse(next))

class LogoutView(View):
    """退出登录"""

    def get(self, request):
        """处理退出登录逻辑"""

        # 由Django用户认证系统完成：需要清理cookie和session,request参数中有user对象
        logout(request)
        # 退出后跳转：由产品经理设计
        return redirect(reverse('goods:index'))

# def register(request):
#     """函数视图：注册"""
#
#     if request.method == 'GET':
#         # 提供注册页面
#         return render(request, 'register.html')
#
#     if request.method == 'POST':
#         # 处理注册逻辑
#         return HttpResponse('收到POST请求，需要处理注册逻辑')
