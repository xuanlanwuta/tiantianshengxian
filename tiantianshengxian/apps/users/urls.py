from django.conf.urls import  url
from apps.users import views

urlpatterns = [
    url(r'^register$',views.register)
]