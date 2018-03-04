from django.conf.urls import url
from orders import views


urlpatterns = [
    # 订单确认 : http://127.0.0.1:8000/orders/place (需要的sku_id和count存放在post请求体中)
    url(r'^place$', views.PlaceOrderView.as_view(), name='place')
]
