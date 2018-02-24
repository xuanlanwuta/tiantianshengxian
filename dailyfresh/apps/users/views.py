from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.views.generic import View
from django.core.urlresolvers import reverse
import re
from django import db
# Create your views here.


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
        if not all(user_name, user_pwd, email):
            return redirect(reverse('users:register'))

        if not re.match(r"^[a-z0-9][\w\.\-]*@[a-z0-9\-]+(\.[a-z]{2,5}){1,2}$", email):
            return render(request, 'register.html', {'error': '邮箱格式不正确'})

        if allow != 'on':
            return render(request, 'register.html', {'error': '请勾选用户协议'})

        try:
            user = User.objects.create_user(user_name, user_pwd, email)

        except db.IntegrityError:
            return render (request , 'register.html' , {'error': '用户名已注册'})

        user.is_active = False
        user.save()




        return HttpResponse('收到POST请求，需要处理注册逻辑')


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
