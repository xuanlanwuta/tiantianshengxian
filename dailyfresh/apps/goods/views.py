from django.shortcuts import render
from django.views.generic import View
from goods.models import GoodsCategory, IndexGoodsBanner, IndexPromotionBanner, IndexCategoryGoodsBanner
# Create your views here.
class IndexView(View):
    """首页"""

    def get(self, request):
        """查询首页页面需要的数据，构造上下文，渲染首页页面"""

        # 查询用户个人信息（request.user）

        # 查询商品分类信息
        categorys = GoodsCategory.objects.all()

        # 查询图片轮播信息:按照index进行排序
        banners = IndexGoodsBanner.objects.all().order_by('index')

        # 查询活动信息
        promotion_banners = IndexPromotionBanner.objects.all().order_by('index')

        # 查询分类商品信息
        for category in categorys:
            title_banners = IndexCategoryGoodsBanner.objects.filter(category=category, display_type=0).order_by('index')
            category.title_banners = title_banners

            image_banners = IndexCategoryGoodsBanner.objects.filter(category=category, display_type=1).order_by('index')
            category.image_banners = image_banners

        # 查询购物车信息
        cart_num = 0

        # 构造上下文:先处理购物车以外的上下文，并缓存
        context = {
            'categorys':categorys,
            'banners':banners,
            'promotion_banners':promotion_banners,
            'cart_num':cart_num
        }
        
        return render(request, 'index.html',context)