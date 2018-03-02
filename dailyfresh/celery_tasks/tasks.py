
from celery import Celery
from django.core.mail import send_mail
from django.conf import settings
from goods.models import GoodsCategory, IndexPromotionBanner, IndexGoodsBanner, IndexCategoryGoodsBanner
from django.template import loader
# 创建celery应用对象
app = Celery ('celery_tasks.tasks' , broker='redis://192.168.0.22:6379/4')


@app.task
def send_active_email(to_email , user_name , token):
    """发送激活邮件"""

    subject = "天天生鲜用户激活"  # 标题
    body = ""  # 文本邮件体
    sender = settings.EMAIL_FROM  # 发件人
    receiver = [to_email]  # 接收人
    html_body = '<h1>尊敬的用户 %s, 感谢您注册天天生鲜！</h1>' \
                '<br/><p>请点击此链接激活您的帐号<a href="http://127.0.0.1:8000/users/active/%s">' \
                'http://127.0.0.1:8000/users/active/%s</a></p>' % (user_name , token , token)
    send_mail (subject , body , sender , receiver , html_message=html_body)


@app.task
def generate_static_index_html():
    """生成静态主页"""

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

    # 查询购物车信息
    cart_num = 0

    # 构造上下文
    context = {
        'categorys': categorys,
        'index_banners': index_banners,
        'promotion_banners': promotion_banners,
        'cart_num': cart_num
    }

    # 加载模板
    print('static_index')
    template = loader.get_template('static_index.html')
    # 上下文渲染模板，得到html数据
    html_data = template.render(context)

    # 获取静态文件路径
    file_path = os.path.join(settings.STATICFILES_DIRS[0], 'index.html')
    # 将生成的html数据，存储到静态文件夹
    with open(file_path, 'w') as file:
        file.write(html_data)
