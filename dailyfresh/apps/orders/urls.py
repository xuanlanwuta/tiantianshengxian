from django.conf.urls import url
from orders import views

urlpatterns = [
    # 订单确认
    url(r'^place$', views.PlaceOrderView.as_view(), name='place'),
    # 订单提交
    url(r'^commit$', views.CommitOrderView.as_view(), name='commit'),
    # 订单信息页面
    url(r'^(?P<page>\d+)$', views.UserOrdersView.as_view(), name='info'),
    # 订单支付
    url(r'^pay$', views.PayOrderView.as_view(), name='pay'),
    # 订单查询
    url(r'^checkpay$',views.CheckOrderView.as_view(), name='checkpay'),
    # 订单评论
    url(r'^comment/(?P<order_id>\d+)$', views.CommentOrderView.as_view(), name='comment')

]