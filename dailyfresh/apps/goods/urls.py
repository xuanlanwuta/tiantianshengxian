from django.conf.urls import url
from goods import views


urlpatterns = [
    # 主页
    url(r'^$', views.IndexView.as_view(), name='index'),
    # 详情页
    url(r'^detail/(?P<sku_id>\d+)$', views.DetailView.as_view(), name='detail'),
    # 列表页
    url(r'^list/(?P<category_id>\d+)/(?P<page_num>\d+)$', views.ListView.as_view(), name='list')

]