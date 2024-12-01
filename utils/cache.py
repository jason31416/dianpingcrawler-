# From sniper970119/dianping_spider


class Cache():
    """
    全局热缓存，用来缓存比如：字体文件映射这类信息
    """

    def __init__(self):
        # 字体映射，用来解析接口的加密信息
        self.search_font_map = {}
        # 是否为冷启动，通过实验发现，即使是代理模式，第一条也需要验证码验证
        self.is_cold_start = True
        pass


cache = Cache()

current_substep = ""
print_bar = None
cookie = ""