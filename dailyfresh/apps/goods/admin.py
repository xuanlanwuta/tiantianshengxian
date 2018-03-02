from django.contrib import admin
from goods.models import GoodsCategory, Goods, GoodsSKU, IndexPromotionBanner
from celery_tasks.tasks import generate_static_index_html
from django.core.cache import cache


# Register your models here.


class BaseAdmin(admin.ModelAdmin):
    """模型管理类的基类"""

    def save_model(self, request, obj, form, change):
        """保存数据时调用"""

        # 保存数据
        obj.save()
        # 异步生成静态页面
        generate_static_index_html.delay()
        # 清除缓存
        cache.delete('index_page_data')


    def delete_model(self, request, obj):
        """删除数据时调用的"""

        # 删除数据
        obj.delete()
        # 异步生成静态页面
        generate_static_index_html.delay()
        # 清除缓存
        cache.delete('index_page_data')


class IndexPromotionBannerAdmin(BaseAdmin):
    """主页商品活动模型类的管理类"""

    pass


admin.site.register(GoodsCategory)
admin.site.register(Goods)
admin.site.register(GoodsSKU)
admin.site.register(IndexPromotionBanner, IndexPromotionBannerAdmin)