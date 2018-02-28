from django.core.files.storage import Storage
from fdfs_client.client import Fdfs_client
from django.conf import settings


class FastDFSStorage(Storage):
    """自定义文件存储系统"""

    def __init__(self, client_conf=None, server_ip=None):
        """初始化方法"""

        if client_conf is None:
            client_conf = settings.CLIENT_CONF
        self.client_conf = client_conf

        if server_ip is None:
            server_ip = settings.SERVER_IP
        self.server_ip = server_ip

    def _open(self, name, mode='rb'):
        """读取文件时调用：这里处理的是存储，所以关于读取直接pass"""
        pass

    def _save(self, name, content):
        """存储文件时调用:name是文件名，content是File类型的对象"""

        # 创建fdfs客户端
        client = Fdfs_client(self.client_conf)

        # 获取要上传的文件内容
        file_data = content.read()
        # django借助fdfs_client实现文件上传
        try:
            ret = client.upload_by_buffer(file_data)
        except Exception as e:
            print(e) # 自己调试打印
            raise # 得到什么异常，就抛出什么异常，谁使用谁处理异常

        # 判断上传是否成功
        if ret.get('Status') == 'Upload successed.':
            # 上传成功后，获取file_id
            file_id = ret.get('Remote file_id')
            # 保存file_id到数据库表：reture即可
            return file_id
        else:
            # 开发工具类时，出现异常不要擅自处理，交给使用者处理
            raise Exception('上传到FastDFS失败')

    def exists(self, name):
        """用来判断文件是否存在"""

        # 文件不存储在Django中，返回False，会使用自定义的文件存储系统存储到fdfs
        return False

    def url(self, name):
        """可以访问到name引用的文件"""

        # 向外界调用者，返回name引用的文件的地址:server_ip+name
        # http://192.168.243.193:8888/group1/M00/00/01/wKjzwVouQn6AfD6ZAALb6Vx4KgI81.jpeg
        return self.server_ip + name