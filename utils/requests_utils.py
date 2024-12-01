# From sniper970119/dianping_spider

import os
import sys
import time
import json
import requests
from tqdm import tqdm
from faker import Factory

from utils.cache import cache
import utils.cache as cachefile
from utils.get_file_map import get_map


class RequestsUtils():
    """
    请求工具类，用于完成全部的请求相关的操作，并进行全局防ban sleep
    """

    def __init__(self):
        self.ua = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
        self.ua_engine = Factory.create()
        if self.ua is None:
            print('user agent 暂时不支持为空')
            sys.exit()

        try:
            self.stop_times = self.parse_stop_time("1,2;3,5;10,50")
        except:
            sys.exit()
        self.global_time = 0

    def create_dir(self, file_name):
        """
        创建文件夹
        :param file_name:
        :return:
        """
        if os.path.exists(file_name):
            return
        else:
            os.mkdir(file_name)

    def parse_stop_time(self, requests_times):
        """
        解析暂停时间
        :param requests_times:
        :return:
        """
        each_stop = requests_times.split(';')
        stop_time = []
        for i in range(len(each_stop) - 1, -1, -1):
            stop_time.append(each_stop[i].split(','))
        return stop_time

    def get_requests(self, url, request_type):
        """
        获取请求
        :param url:
        :return:
        """
        assert request_type in ['no header', 'no proxy, cookie', 'no proxy, no cookie', 'proxy, no cookie',
                                'proxy, cookie']

        # 不需要请求头的请求不计入统计（比如字体文件下载）
        if request_type == 'no header':
            r = requests.get(url=url)
            return r

        # 所有本地ip的请求都进入全局监控，no header由于只用于字体文件下载，不计入监控
        if 'no proxy' in request_type:
            self.freeze_time()

            if request_type == 'no proxy, no cookie':
                r = requests.get(url, headers=self.get_header(cookie=None, need_cookie=False))

            if request_type == 'no proxy, cookie':
                cur_cookie = self.get_cookie(url)
                r = requests.get(url, headers=self.get_header(cookie=cur_cookie, need_cookie=True))

            return self.handle_verify(r=r, url=url, request_type=request_type)

        """
        下面两个虽然标记使用代理，但是依然判断。
        使用这种标记的意味着这些请求可以由代理完成，但是理所应当可以不用代理。
        当然，建议使用代理。
        """
        if request_type == 'proxy, no cookie':
            if self.ip_proxy:
                # 这个while是处理代理失效的问题（通常是超时等问题）
                r = requests.get(url, headers=self.get_header(None, False), proxies=self.get_proxy(), timeout=10)
                # 接口专属请求做过重试了（max retry），因此这里的while暂时不用
            else:
                r = requests.get(url, headers=self.get_header(None, False))
            return self.handle_verify(r, url, request_type)

        if request_type == 'proxy, cookie':
            # 对于携带cookie的请求，依然计入全局监控
            self.freeze_time()

            cur_cookie = self.get_cookie(url)
            header = self.get_header(cookie=cur_cookie, need_cookie=True)
            r = requests.get(url, headers=header)

            return self.handle_verify(r, url, request_type)
        # 其他
        raise AttributeError

    def freeze_time(self):
        """
        时间暂停术！
        @return:
        """
        self.global_time += 1
        if self.global_time != 1:
            for each_stop_time in self.stop_times:
                if self.global_time % int(each_stop_time[0]) == 0:
                    until = time.time() + float(each_stop_time[1])
                    while time.time() < until:
                        import random
                        cachefile.current_substep = f"(Waiting for {int(until-time.time())}s)"
                        sleep_time = 0.001 + (random.randint(1, 10) / 5000)
                        time.sleep(sleep_time)
                        cachefile.print_bar()
            cachefile.current_substep = f"(Fetching data...)"
            cachefile.print_bar()

    def handle_verify(self, r, url, request_type):
        # 这里只做验证码处理，不做其他判断（例如403）
        # 原因是很多地方需要不同的处理方法，全部移到这里基于现有架构代价有点大
        if 'verify' in r.url:
            """
            不管是使用真实ip还是真实cookie，都对验证码进行处理
            这里有一个问题，就是cookie池到底处不处理验证码，如果处理，
            一定程度上丧失了cookie池的意义，如果不处理，失效的太快。
            暂时处理
            """
            print("\n\033[33m请点击下方链接并处理验证码，完成后按下回车继续:\nhttps://www.dianping.com/search/keyword/2/0_hi/p2")
            input()
            return self.get_requests(url, request_type)
        else:
            return r

    def get_retry_time(self):
        """
        获取ip重试次数
        @return:
        """
        # 这里处理解决请求会异常的问题,允许恰巧当前ip出问题，多试一条
        return 5

    def get_request_for_interface(self, url):
        """
        专属于接口的请求方法，可以保证返回的都是“正确”的
        @param url:
        @return:
        """
        retry_time = self.get_retry_time()
        while True:
            retry_time -= 1
            r = requests_util.get_requests(url, request_type='proxy, no cookie')
            try:
                # request handle v2
                r_json = json.loads(r.text)
                if r_json['code'] == 406:
                    # 处理代理模式冷启动时，首条需要验证
                    # （虽然我也不知道为什么首条要验证，本质上切换ip都是首条。但是这样做有效）
                    if cache.is_cold_start is True:
                        print('处理验证码,按任意键回车继续:', r_json['customData']['verifyPageUrl'])
                        input()
                        r = requests_util.get_requests(url, request_type='proxy, no cookie')
                        cache.is_cold_start = False
                # 前置验证码过滤
                if r_json['code'] == 200:
                    break
                if retry_time <= 0:
                    print('替换tsv和uuid，或者代理质量较低')
                    exit()
            except:
                pass
        return r

    def get_cookie(self, url):
        return cachefile.cookie

    def judge_request_type(self, url):
        """
        判断请求类型，由于cookie池是分开维护的，搜索、详情、评论也不是一起被ban的，
        需要对每个cookie的每个页面进行分类
        @param url:
        @return:
        """
        if 'shop' in url:
            return 'detail'
        elif 'review' in url:
            return 'review'
        else:
            return 'search'

    def get_header(self, cookie, need_cookie=True):
        """
        获取请求头
        :return:
        """
        if self.ua is not None:
            ua = self.ua
        else:
            ua = self.ua_engine.user_agent()

        # cookie选择
        if cookie is None:
            cookie = self.cookie

        if need_cookie:
            header = {
              'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
              'Accept-Language': 'en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7',
              'Cache-Control': 'max-age=0',
              'Connection': 'keep-alive',
              'Cookie': cookie,
              'Sec-Fetch-Dest': 'document',
              'Sec-Fetch-Mode': 'navigate',
              'Sec-Fetch-Site': 'none',
              'Sec-Fetch-User': '?1',
              'Upgrade-Insecure-Requests': '1',
              'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
              'sec-ch-ua': '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
              'sec-ch-ua-mobile': '?0',
              'sec-ch-ua-platform': '"macOS"'
            }
        else:
            header = {
                'User-Agent': ua,
            }
        return header

    def get_proxy(self):
        """
        获取代理
        """
        repeat_nub = spider_config.REPEAT_NUMBER
        # http 提取模式
        if spider_config.HTTP_EXTRACT:
            # 代理池为空，提取代理
            if len(self.proxy_pool) == 0:
                proxy_url = spider_config.HTTP_LINK
                r = requests.get(proxy_url)
                r_json = r.json()
                # json解析方式替换
                # for proxy in r_json['Data']:
                for proxy in r_json:
                    # 重复添加，多次利用
                    for _ in range(repeat_nub):
                        # self.proxy_pool.append([proxy['Ip'], proxy['Port']])
                        self.proxy_pool.append([proxy['ip'], proxy['port']])
            # 获取ip
            proxies = self.http_proxy_utils(self.proxy_pool[0][0], self.proxy_pool[0][1])
            self.proxy_pool.remove(self.proxy_pool[0])
            return proxies
        # 秘钥提取模式
        elif spider_config.KEY_EXTRACT:
            proxies = self.key_proxy_utils()
            return proxies
        else:
            print('使用代理时，必须选择http提取或秘钥提取中的一个')
            exit()
        pass

    def http_proxy_utils(self, ip, port):
        """
        专属http链接的代理格式
        @param ip:
        @param port:
        @return:
        """
        proxyMeta = "http://%(host)s:%(port)s" % {

            "host": ip,
            "port": port,
        }

        proxies = {

            "http": proxyMeta,
            "https": proxyMeta
        }
        return proxies

    def key_proxy_utils(self):
        """
        专属http链接的代理格式
        @param ip:
        @param port:
        @return:
        """

        proxyMeta = "http://%(user)s:%(pass)s@%(host)s:%(port)s" % {
            "host": spider_config.PROXY_HOST,
            "port": spider_config.PROXY_PORT,
            "user": spider_config.KEY_ID,
            "pass": spider_config.KEY_KEY,
        }

        proxies = {
            "http": proxyMeta,
            "https": proxyMeta,
        }
        return proxies

    def replace_search_html(self, page_source, file_map):
        """
        替换html文本，根据加密字体文件映射替换page source加密代码
        :param page_source:
        :param file_map:
        :return:
        """
        for k_f, v_f in file_map.items():
            font_map = get_map(v_f)
            for k, v in font_map.items():
                key = str(k).replace('uni', '&#x')
                key = '"' + str(k_f) + '">' + key + ';'
                value = '"' + str(k_f) + '">' + v
                page_source = page_source.replace(key, value)
        return page_source

    def replace_review_html(self, page_source, file_map):
        """
        替换html文本，根据加密字体文件映射替换page source加密代码
        :param page_source:
        :param file_map:
        :return:
        """
        for k_f, v_f in file_map.items():
            font_map = get_map(v_f)
            for k, v in font_map.items():
                key = str(k).replace('uni', '&#x')
                key = '"' + str(k) + '"><'
                value = '"' + str(k) + '">' + str(v) + '<'
                page_source = page_source.replace(key, value)
        return page_source

    def replace_json_text(self, json_text, file_map):
        """
        替换json文本，根据加密字体文件映射替换json加密文本
        :param page_source:
        :param file_map:
        :return:
        """
        for k_f, v_f in file_map.items():
            font_map = get_map(v_f)
            for k, v in font_map.items():
                key = str(k).replace('uni', '&#x')
                key = '\\"' + str(k_f) + '\\">' + key + ';'
                value = '\\"' + str(k_f) + '\\">' + v
                json_text = json_text.replace(key, value)
        return json_text

    def update_cookie(self):
        self.cookie = global_config.getRaw('config', 'Cookie')


requests_util = RequestsUtils()
