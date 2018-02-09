from django.db import models

class BaseModel(models.Model):

    create_time = models.DateTimeField(auto_created=True,verbose_name='建立时间')
    uptate_time = models.DateTimeField(auto_created=True,verbose_name='更新时间')