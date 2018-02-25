from django.conf.urls import  url
from apps.users import views

urlpatterns = [
    # url(r'^register$',views.register)
    url(r'^register$', views.RegisterView.as_view(),name='register'),
    url(r'^logout$', views.LogoutView.as_view(), name='logout'),
    url(r'^login$',views.LoginView.as_view(),name='login'),
    url(r'^address$',views.AddressView.as_view(),name='address')
]