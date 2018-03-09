from django.shortcuts import render, redirect
from utils.views import LoginRequiredMixin,LoginRequiredJsonMixin,TransactionAtomicMixin
from django.views.generic import View
from django.core.urlresolvers import reverse
from goods.models import GoodsSKU
from django_redis import get_redis_connection
from users.models import Address
from django.http import JsonResponse
from orders.models import OrderInfo,OrderGoods
from django.utils import timezone
from django.db import transaction
from django.core.paginator import Paginator,EmptyPage
from alipay import AliPay
from django.conf import settings
from django.core.cache import cache


# Create your views here.


class CommentOrderView(LoginRequiredMixin, View):
    """评论"""

    def get(self, request, order_id):
        """提供评论页面"""

        user = request.user
        try:
            order = OrderInfo.objects.get(order_id=order_id, user=user)
        except OrderInfo.DoesNotExist:
            return redirect(reverse("orders:info"))

        order.status_name = OrderInfo.ORDER_STATUS[order.status]
        order.skus = []
        order_skus = order.ordergoods_set.all()
        for order_sku in order_skus:
            sku = order_sku.sku
            sku.count = order_sku.count
            sku.amount = sku.price * sku.count
            order.skus.append(sku)

        return render(request, "order_comment.html", {"order": order})

    def post(self, request, order_id):
        """处理评论信息"""

        user = request.user
        try:
            order = OrderInfo.objects.get(order_id=order_id, user=user)
        except OrderInfo.DoesNotExist:
            return redirect(reverse("orders:info"))

        # 获取评论条数
        total_count = request.POST.get("total_count")
        total_count = int(total_count)

        for i in range(1, total_count + 1):
            sku_id = request.POST.get("sku_%d" % i)
            content = request.POST.get('content_%d' % i, '')
            try:
                order_goods = OrderGoods.objects.get(order=order, sku_id=sku_id)
            except OrderGoods.DoesNotExist:
                continue

            order_goods.comment = content
            order_goods.save()

            # 清除商品详情缓存
            cache.delete("detail_%s" % sku_id)

        order.status = OrderInfo.ORDER_STATUS_ENUM["FINISHED"]
        order.save()

        return redirect(reverse("orders:info", kwargs={"page": 1}))


class CheckOrderView(LoginRequiredJsonMixin, View):
    """查询订单状态"""

    def get(self, request):
        """处理支付订单查询逻辑"""

        # 获取订单id
        order_id = request.GET.get('order_id')

        # 校验订单id
        if not order_id:
            return JsonResponse({'code': 2, 'message': '缺少订单id'})

        # 获取订单信息:状态是待支付，支付方式是支付宝
        try:
            order = OrderInfo.objects.get(
                order_id=order_id,
                user=request.user,
                status=OrderInfo.ORDER_STATUS_ENUM["UNPAID"],
                pay_method=OrderInfo.PAY_METHODS_ENUM["ALIPAY"]
            )
        except OrderInfo.DoesNotExist:
            return JsonResponse({'code': 3, 'message': '订单不存在'})

        # 创建用于支付宝支付的对象
        alipay = AliPay(
            appid=settings.ALIPAY_APPID,
            app_notify_url=None,  # 默认回调url
            # 自己生产的私钥
            app_private_key_path=settings.APP_PRIVATE_KEY_PATH,
            # 支付宝的公钥，验证支付宝回传消息使用，不是你自己的公钥,
            alipay_public_key_path=settings.ALIPAY_PUBLIC_KEY_PATH,
            sign_type="RSA2",  # RSA 或者 RSA2
            debug=True  # 默认False 配合沙箱模式使用
        )

        while True:

            # 查询支付结果
            response = alipay.api_alipay_trade_query(order_id)

            # 判断支付结果
            code = response.get('code') # 获取状态码
            trade_status = response.get('trade_status') # 获取状态描述

            # 判断用户支付成功
            if code == '10000' and trade_status == 'TRADE_SUCCESS':
                # 设置订单的支付状态为待评论
                order.status = OrderInfo.ORDER_STATUS_ENUM["UNCOMMENT"]
                # 设置支付宝对应的订单编号
                order.trade_id = response.get('trade_no')
                order.save()

                return JsonResponse({'code': 0, 'message': '支付成功'})

            elif code == '40004' or (code == '10000' and trade_status == 'WAIT_BUYER_PAY'):
                # 判断用户其他支付状态，订单支付会有延迟，有些状态会暂时出错
                continue
            else:
                # 判断用户支付失败
                # 返回失败结果
                return JsonResponse({'code': 4, 'message': '支付失败'})


class PayOrderView(LoginRequiredJsonMixin, View):
    """订单支付"""

    def post(self, request):
        """处理对接支付宝逻辑"""

        # 获取订单id
        order_id = request.POST.get('order_id')

        # 校验订单id
        if not order_id:
            return JsonResponse({'code':2, 'message':'缺少订单id'})

        # 获取订单信息:状态是待支付，支付方式是支付宝
        try:
            order = OrderInfo.objects.get(
                order_id = order_id,
                user = request.user,
                status = OrderInfo.ORDER_STATUS_ENUM["UNPAID"],
                pay_method = OrderInfo.PAY_METHODS_ENUM["ALIPAY"]
            )
        except OrderInfo.DoesNotExist:
            return JsonResponse({'code':3, 'message':'订单不存在'})

        # 创建用于支付宝支付的对象
        alipay = AliPay(
            appid=settings.ALIPAY_APPID,
            app_notify_url=None,  # 默认回调url
            # 自己生产的私钥
            app_private_key_path=settings.APP_PRIVATE_KEY_PATH,
            # 支付宝的公钥，验证支付宝回传消息使用，不是你自己的公钥,
            alipay_public_key_path=settings.ALIPAY_PUBLIC_KEY_PATH,
            sign_type="RSA2",  # RSA 或者 RSA2
            debug=True  # 默认False 配合沙箱模式使用
        )

        # 电脑网站支付，需要跳转到https://openapi.alipay.com/gateway.do? + order_string
        order_string = alipay.api_alipay_trade_page_pay(
            out_trade_no=order_id,
            total_amount=str(order.total_amount),  # 将浮点数转成字符串
            subject='头条生鲜',
            return_url=None,
            notify_url=None  # 可选, 不填则使用默认notify url
        )

        # 生成url:让用户进入支付宝页面的支付网址
        url = settings.ALIPAY_URL + '?' + order_string

        # 响应结果
        return JsonResponse({'code':0, 'message':'支付成功', 'url':url})


class UserOrdersView(LoginRequiredMixin, View):
    """订单信息页面"""

    def get(self, request, page):
        """提供订单信息页面"""

        # 获取用户
        user = request.user
        # 查询订单
        orders = user.orderinfo_set.all().order_by("-create_time")

        # 遍历所有订单
        for order in orders:
            # 绑定订单状态
            order.status_name = OrderInfo.ORDER_STATUS[order.status]
            # 绑定支付方式
            order.pay_method_name = OrderInfo.PAY_METHODS[order.pay_method]
            order.skus = []
            # 查询订单商品
            order_skus = order.ordergoods_set.all()
            # 遍历订单商品
            for order_sku in order_skus:
                sku = order_sku.sku
                sku.count = order_sku.count
                sku.amount = sku.price * sku.count
                order.skus.append(sku)

        # 分页
        page = int(page)
        try:
            paginator = Paginator(orders, 2)
            page_orders = paginator.page(page)
        except EmptyPage:
            # 如果传入的页数不存在，就默认给第1页
            page_orders = paginator.page(1)
            page = 1

        # 页数
        page_list = paginator.page_range

        context = {
            "orders": page_orders,
            "page": page,
            "page_list": page_list,
        }

        return render(request, "user_center_order.html", context)


class CommitOrderView(LoginRequiredJsonMixin, TransactionAtomicMixin, View):
    """订单提交"""

    def post(self, request):
        """处理订单提交逻辑"""

        # 获取参数：user,address_id,pay_method,sku_ids,count
        user = request.user
        address_id = request.POST.get('address_id')
        pay_method = request.POST.get('pay_method')
        sku_ids = request.POST.get('sku_ids')

        # 校验参数：all([address_id, sku_ids, pay_method])
        if not all([address_id, sku_ids, pay_method]):
            return JsonResponse({'code':2, 'message':'缺少参数'})

        # 判断地址
        try:
            address = Address.objects.get(id=address_id)
        except Address.DoesNotExist:
            return JsonResponse({'code': 3, 'message': '地址不存在'})

        # 判断支付方式:默认只支持支付宝
        if pay_method not in OrderInfo.PAY_METHOD:
            return JsonResponse({'code': 4, 'message': '支付方式错误'})

        # 生成时间戳形式的订单id
        order_id = timezone.now().strftime('%Y%m%d%H%M%S')+str(user.id)

        # 在操作数据库之前创建事务保存点
        save_point = transaction.savepoint()

        # 暴力回滚
        try:

            # 先创建商品订单信息
            order = OrderInfo.objects.create(
                order_id = order_id,
                user = user,
                address = address,
                total_amount = 0,
                trans_cost = 10,
                pay_method = pay_method
            )

            # 定义临时变量
            total_count = 0
            total_amount = 0

            # 创建redis连接对象
            redis_conn = get_redis_connection('default')
            cart_dict = redis_conn.hgetall('cart_%s'%user.id)

            # 截取sku_ids列表
            sku_ids = sku_ids.split(',')
            # 遍历sku_ids
            for sku_id in sku_ids:

                # 每种商品有三次下单机会
                for i in range(3):

                    # 循环取出sku判断商品是否存在
                    try:
                        sku = GoodsSKU.objects.get(id=sku_id)
                    except GoodsSKU.DoesNotExist:
                        # 异常，回滚
                        transaction.savepoint_rollback(save_point)
                        return JsonResponse({'code': 5, 'message': '商品不存在'})

                    # 获取商品数量，判断库存 (redis)
                    sku_count = cart_dict.get(sku_id.encode())
                    sku_count = int(sku_count)
                    if sku_count > sku.stock:
                        # 异常，回滚
                        transaction.savepoint_rollback(save_point)
                        return JsonResponse({'code': 6, 'message': '库存不足'})

                    # 测试并发和乐观锁
                    # import time
                    # time.sleep(10)

                    # 减少sku库存
                    origin_stock = sku.stock
                    new_stock = origin_stock - sku_count
                    # 增加sku销量
                    new_sales = sku.sales + sku_count
                    # 乐观锁更新库存和销量
                    result = GoodsSKU.objects.filter(id=sku_id,stock=origin_stock).update(stock=new_stock, sales=new_sales)
                    if 0 == result and i < 2:
                        # 不足三次，继续下单
                        continue
                    elif 0 == request and i == 2:
                        # 异常，回滚
                        transaction.savepoint_rollback(save_point)
                        return JsonResponse({'code': 8, 'message': '下单失败'})

                    # 保存订单商品数据OrderGoods(能执行到这里说明无异常)
                    OrderGoods.objects.create(
                        order = order,
                        sku = sku,
                        count = sku_count,
                        price = sku.price,
                    )

                    # 计算总数和总金额
                    total_count += sku_count
                    total_amount += sku_count * sku.price + 10

                    # 如果成功，跳出循环
                    break

            # 修改订单信息里面的总数和总金额(OrderInfo)
            order.total_count = total_count
            order.total_amount = total_amount
            order.save()

        except Exception:
            # 异常，回滚
            transaction.savepoint_rollback(save_point)
            return JsonResponse({'code': 7, 'message': '下单失败'})

        # 没有异常，手动提交
        transaction.savepoint_commit(save_point)

        # 订单生成后删除购物车(hdel)
        # redis_conn.hdel('cart_%s'%user.id, *sku_ids)

        # 响应结果
        return JsonResponse({'code': 0, 'message': '提交订单成功'})


class PlaceOrderView(LoginRequiredMixin, View):
    """订单确认"""

    def post(self, request):
        """处理去结算和立即购买逻辑"""

        # 获取参数：user, sku_ids, count
        sku_ids = request.POST.getlist('sku_ids')
        count = request.POST.get('count')

        # 校验sku_ids参数：not
        if not sku_ids:
            return redirect(reverse('cart:info'))

        # 定义临时容器
        skus = []
        total_count = 0
        total_sku_amount = 0
        trans_cost = 10
        total_amount = 0

        # 创建redis连接对象
        redis_conn = get_redis_connection('default')
        user_id = request.user.id
        # redis中取count
        cart_dict = redis_conn.hgetall('cart_%s' % user_id)

        # 查询商品数据
        if count is None:

            # 如果是从购物车页面过来，商品的数量从redis中获取
            for sku_id in sku_ids:

                # 查询商品
                try:
                    sku = GoodsSKU.objects.get(id=sku_id)
                except GoodsSKU.DoesNotExist:
                    return redirect(reverse('cart:info'))

                # 获取count
                sku_count = cart_dict.get(sku_id.encode())
                sku_count = int(sku_count)

                # 计算小计
                amount = sku_count * sku.price
                # 动态绑定属性
                sku.count = sku_count
                sku.amount = amount
                # 记录sku对象
                skus.append(sku)
                # 累计求和
                total_count += sku_count
                total_sku_amount += amount

        else:
            # 如果是从详情页面过来，商品的数量从request中获取
            for sku_id in sku_ids:
                try:
                    sku = GoodsSKU.objects.get(id=sku_id)
                except GoodsSKU.DoesNotExist:
                    # 重定向到购物车
                    return redirect(reverse('cart:info'))

                # 校验count
                try:
                    sku_count = int(count)
                except Exception:
                    return redirect(reverse('goods:detail', args=sku_id))

                # 判断库存：立即购买没有判断库存
                if sku_count > sku.stock:
                    return redirect(reverse('goods:detail', args=sku_id))

                # 计算小计
                amount = sku_count * sku.price
                # 动态绑定属性
                sku.count = sku_count
                sku.amount = amount
                # 记录sku对象
                skus.append(sku)
                # 累计求和
                total_count += sku_count
                total_sku_amount += amount

                # 为了方便提交订单时，获取商品数量，立即加入购物车时，将商品添加到redis中
                redis_conn.hset('cart_%s'%user_id, sku_id, sku_count)

        # 实付款
        total_amount = total_sku_amount + trans_cost

        # 查询用户地址信息
        try:
            address = Address.objects.filter(user=request.user).latest('create_time')
        except Address.DoesNotExist:
            # 如果地址为空，渲染模板时会判断，并跳转到地址编辑页面
            address = None

        # 构造上下文
        context = {
            'skus':skus,
            'total_count':total_count,
            'total_sku_amount':total_sku_amount,
            'trans_cost': trans_cost,
            'total_amount':total_amount,
            'address':address,
            'sku_ids':','.join(sku_ids)
        }

        # 响应结果:html页面
        return render(request, 'place_order.html', context)