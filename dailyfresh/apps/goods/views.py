from django.shortcuts import render, redirect
from django.views.generic import View
from goods.models import Goods, GoodsCategory, GoodsSKU, IndexGoodsBanner, IndexPromotionBanner, IndexCategoryGoodsBanner
from django.core.cache import cache
from django_redis import get_redis_connection
from django.core.urlresolvers import reverse
from django.core.paginator import Paginator, EmptyPage


# Create your views here.


class ListView(View):
    """商品列表页"""

    def get(self, request, category_id, page_num):
        """提供商品列表页面"""

        # 获取排序方式:如果不存在就取默认default
        sort = request.GET.get('sort', 'default')

        # 查询需要展示的商品列表属于的商品分类，检验category_id是否正确
        try:
            category = GoodsCategory.objects.get(id=category_id)
        except GoodsCategory.DoesNotExist:
            return redirect(reverse('goods:index'))

        # 查询所有分类信息
        categorys = GoodsCategory.objects.all()

        # 查询新品推荐
        new_skus = GoodsSKU.objects.filter(category=category).order_by('-create_time')[:2]

        # 查询商品列表信息
        if sort == 'price':
            # 按照价格从低到高排序
            skus = GoodsSKU.objects.filter(category=category).order_by('price')
        elif sort == 'hot':
            # 按照销量从高到低排序
            skus = GoodsSKU.objects.filter(category=category).order_by('-sales')
        else:
            # 默认排序
            skus = GoodsSKU.objects.filter(category=category)
            # 当用户传入的是default或者是price和hot以外的其他无效数据，都重置为default
            sort = 'default'

        # 创建商品分页数据
        # 获取用户传入的page_num
        page_num = int(page_num)
        # 创建分页器,每页两条数据
        paginator = Paginator(skus, 2)
        # 获取page_num对应的page对象
        try:
            page_skus = paginator.page(page_num)
        except EmptyPage:
            page_skus = paginator.page(1)

        # 获取分页索引列表
        page_list = paginator.page_range

        # 如果已登录，查询购物车数据
        cart_num = 0

        if request.user.is_authenticated():

            # 获取redis链接对象
            redis_conn = get_redis_connection('default')
            # 获取user_id
            user_id = request.user.id
            # 查询出购物车数据
            cart_dict = redis_conn.hgetall('cart_%s' % user_id)
            # 遍历购物车字典:val默认是字节类型的
            for val in cart_dict.values():
                cart_num += int(val)

        # 构造上下文
        context = {
            'sort':sort,
            'category':category,
            'categorys':categorys,
            'new_skus':new_skus,
            'page_skus':page_skus,
            'page_list':page_list,
            'cart_num':cart_num,
        }

        return render(request, 'list.html', context)


class DetailView(View):
    """详情页"""

    def get(self, request, sku_id):
        """提供详情页面"""

        # 读取缓存数据
        context = cache.get('detail_%s'%sku_id)
        if context is None:

            try:
                # 获取商品信息
                sku = GoodsSKU.objects.get(id=sku_id)
            except GoodsSKU.DoesNotExist:
                # from django.http import Http404
                # raise Http404("商品不存在!")
                return redirect(reverse("goods:index"))

            # 获取类别
            categorys = GoodsCategory.objects.all()

            # 从订单中获取评论信息
            sku_orders = sku.ordergoods_set.all().order_by('-create_time')[:30]
            if sku_orders:
                for sku_order in sku_orders:
                    sku_order.ctime = sku_order.create_time.strftime('%Y-%m-%d %H:%M:%S')
                    sku_order.username = sku_order.order.user.username
            else:
                sku_orders = []

            # 获取最新推荐
            new_skus = GoodsSKU.objects.filter(category=sku.category).order_by("-create_time")[:2]

            # 获取其他规格的商品
            other_skus = sku.goods.goodssku_set.exclude(id=sku_id)

            context = {
                "categorys": categorys,
                "sku": sku,
                "orders": sku_orders,
                "new_skus": new_skus,
                "other_skus": other_skus
            }

            # 缓存详情页数据
            cache.set('detail_%s'%sku_id, context, 3600)

        # 如果已登录，查询购物车数据
        cart_num = 0

        if request.user.is_authenticated():

            # 获取redis链接对象
            redis_conn = get_redis_connection('default')
            # 获取user_id
            user_id = request.user.id
            # 查询出购物车数据
            cart_dict = redis_conn.hgetall('cart_%s' % user_id)
            # 遍历购物车字典:val默认是字节类型的
            for val in cart_dict.values():
                cart_num += int(val)

            # 如果用户已登录，保存浏览记录数据
            # 去重:在保存商品浏览记录之前先把重复去掉
            redis_conn.lrem('history_%s'%user_id, 0, sku_id)
            # 添加浏览记录到redis数据库
            redis_conn.lpush('history_%s'%user_id, sku_id)
            # 截取0-4的五条记录
            redis_conn.ltrim('history_%s'%user_id, 0, 4)

        # 更新context
        context.update(cart_num=cart_num)

        return render(request, 'detail.html', context)


class IndexView(View):
    """主页"""

    def get(self, request):
        """提供主页页面"""

        # 先查询是否有缓存，如果有缓存直接读取缓存数据
        context = cache.get('index_page_data')
        if context is None:

            # 查询商品分类信息
            categorys = GoodsCategory.objects.all()

            # 查询图片轮播信息
            index_banners = IndexGoodsBanner.objects.all().order_by('index')

            # 查询商品活动信息
            promotion_banners = IndexPromotionBanner.objects.all().order_by('index')

            # 查询商品分类列表信息
            for category in categorys:
                # 查询标题类型展示的商品
                title_banners = IndexCategoryGoodsBanner.objects.filter(category=category, display_type=0)
                category.title_banners = title_banners

                # 查询图片类型展示的商品
                image_banners = IndexCategoryGoodsBanner.objects.filter(category=category, display_type=1)
                category.image_banners = image_banners

            # 构造上下文
            context = {
                'categorys':categorys,
                'index_banners':index_banners,
                'promotion_banners':promotion_banners,
            }

            # 设置缓存，存储主页查询出来的数据:key，内容，有效期
            cache.set('index_page_data', context, 3600)

        # 查询购物车信息:购物车不能被缓存
        cart_num = 0

        # 当用户登陆时，在获取购物车数据
        if request.user.is_authenticated():
            # 获取redis链接对象
            redis_conn = get_redis_connection('default')
            # 获取user_id
            user_id = request.user.id
            # 查询出购物车数据
            cart_dict = redis_conn.hgetall('cart_%s'%user_id)
            # 遍历购物车字典:val默认是字节类型的
            for val in cart_dict.values():
                cart_num += int(val)

        # 更新context
        context.update(cart_num=cart_num)

        return render(request, 'index.html', context)