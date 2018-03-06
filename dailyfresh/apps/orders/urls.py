from django.conf.urls import url
from orders import views

urlpatterns = [
    # 订单确认
    url(r'^place$', views.PlaceOrderView.as_view(), name='place'),
    # 订单提交
    url(r'^commit$', views.CommitOrderView.as_view(), name='commit'),
    # 订单信息页面
    url(r'^(?P<page>\d+)$', views.UserOrdersView.as_view(), name='info')

]