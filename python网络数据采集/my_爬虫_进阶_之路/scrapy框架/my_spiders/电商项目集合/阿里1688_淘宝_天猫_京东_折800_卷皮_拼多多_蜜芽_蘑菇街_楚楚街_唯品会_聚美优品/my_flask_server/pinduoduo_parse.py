# coding:utf-8

'''
@author = super_fazai
@File    : pinduoduo_parse.py
@Time    : 2017/11/24 14:58
@connect : superonesfazai@gmail.com
'''

"""
拼多多页面采集系统(官网地址: http://mobile.yangkeduo.com/)
由于拼多多的pc站，官方早已放弃维护，专注做移动端，所以下面的都是基于移动端地址进行的爬取
直接requests开始时是可以的，后面就只返回错误的信息，估计将我IP过滤了
"""

import time
from random import randint
import json
import requests
import re
from pprint import pprint
from decimal import Decimal
from time import sleep
import datetime
import re
import gc
import pytz

from settings import HEADERS
from selenium import webdriver
import selenium.webdriver.support.ui as ui
from settings import PHANTOMJS_DRIVER_PATH
from my_ip_pools import MyIpPools

# phantomjs驱动地址
EXECUTABLE_PATH = PHANTOMJS_DRIVER_PATH

class PinduoduoParse(object):
    def __init__(self):
        self.headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            # 'Accept-Encoding:': 'gzip',
            'Accept-Language': 'zh-CN,zh;q=0.8',
            'Cache-Control': 'max-age=0',
            'Connection': 'keep-alive',
            'Host': 'mobile.yangkeduo.com',
            'User-Agent': HEADERS[randint(0, 34)],  # 随机一个请求头
            # 'Cookie': 'api_uid=rBQh+FoXerAjQWaAEOcpAg==;',      # 分析发现需要这个cookie值
        }
        self.result_data = {}
        # self.set_cookies_key_api_uid()  # 设置cookie中的api_uid的值
        self.init_phantomjs()

    def get_goods_data(self, goods_id):
        '''
        模拟构造得到data的url
        :param goods_id:
        :return: data   类型dict
        '''
        if goods_id == '':
            self.result_data = {}  # 重置下，避免存入时影响下面爬取的赋值
            return {}
        else:
            tmp_url = 'http://mobile.yangkeduo.com/goods.html?goods_id=' + str(goods_id)
            print('------>>>| 得到的商品手机版地址为: ', tmp_url)

            '''
            1.采用requests，由于经常返回错误的body(即requests.get返回的为空的html), So pass
            '''
            # body = self.get_url_body_by_requests(tmp_url=tmp_url)

            '''
            2.采用phantomjs来获取
            '''
            body = self.get_url_body(tmp_url=tmp_url)

            if body == '':
                print('body中re匹配到的data为空!')
                self.result_data = {}  # 重置下，避免存入时影响下面爬取的赋值
                return {}

            data = re.compile(r'window.rawData= (.*?);</script>').findall(body)  # 贪婪匹配匹配所有

            if data != []:
                data = data[0]
                try:
                    data = json.loads(data)
                except Exception:
                    self.result_data = {}  # 重置下，避免存入时影响下面爬取的赋值
                    return {}
                # pprint(data)

                try:
                    data['goods'].pop('localGroups')
                    data['goods'].pop('mallService')
                    data.pop('reviews')             # 评价信息跟相关统计
                except:
                    pass
                # pprint(data)

                '''
                处理detailGallery转换成能被html显示页面信息
                '''
                detail_data = data.get('goods', {}).get('detailGallery', [])
                tmp_div_desc = ''
                if detail_data != []:
                    for index in range(0, len(detail_data)):
                        if index == 0:      # 跳过拼多多的提示
                            pass
                        else:
                            tmp = ''
                            tmp_img_url = detail_data[index].get('url')
                            tmp = r'<img src="{}" style="height:auto;width:100%;"/>'.format(tmp_img_url)
                            tmp_div_desc += tmp

                    detail_data = '<div>' + tmp_div_desc + '</div>'

                else:
                    detail_data = ''
                # print(detail_data)
                try:
                    data['goods'].pop('detailGallery')  # 删除图文介绍的无第二次用途的信息
                except:
                    pass
                data['div_desc'] = detail_data

                # pprint(data)
                self.result_data = data
                return data

            else:
                print('data为空!')
                self.result_data = {}  # 重置下，避免存入时影响下面爬取的赋值
                return {}

    def deal_with_data(self):
        '''
        处理result_data, 返回需要的信息
        :return: 字典类型
        '''
        data = self.result_data
        if data != {}:
            # 店铺名称
            if data.get('mall') is not None:
                shop_name = data.get('mall', {}).get('mallName', '')
            else:
                shop_name = ''

            # 掌柜
            account = ''

            # 商品名称
            title = data.get('goods', {}).get('goodsName', '')

            # 子标题
            sub_title = ''

            # 商品库存
            # 商品标签属性对应的值

            # 商品标签属性名称
            if data.get('goods', {}).get('skus', []) == []:
                detail_name_list = []
            else:
                if data.get('goods', {}).get('skus', [])[0].get('specs') == []:
                    detail_name_list = []
                else:
                    detail_name_list = [{'spec_name': item.get('spec_key')} for item in data.get('goods', {}).get('skus', [])[0].get('specs')]
            # print(detail_name_list)

            # 要存储的每个标签对应规格的价格及其库存
            skus = data.get('goods', {}).get('skus', [])
            # pprint(skus)
            price_info_list = []
            if skus != []:          # ** 注意: 拼多多商品只有一个规格时skus也不会为空的 **
                for index in range(0, len(skus)):
                    tmp = {}
                    price = skus[index].get('groupPrice', '')          # 拼团价
                    normal_price = skus[index].get('normalPrice', '')  # 单独购买价格
                    spec_value = [item.get('spec_value') for item in data.get('goods', {}).get('skus', [])[index].get('specs')]
                    spec_value = '|'.join(spec_value)
                    img_url = skus[index].get('thumbUrl', '')
                    rest_number = skus[index].get('quantity', 0)  # 剩余库存
                    is_on_sale = skus[index].get('isOnSale', 0)        # 用于判断是否在特价销售，1:特价 0:原价(normal_price)
                    tmp['spec_value'] = spec_value
                    tmp['detail_price'] = price
                    tmp['normal_price'] = normal_price
                    tmp['img_url'] = img_url
                    if rest_number <= 0:
                        tmp['rest_number'] = 0
                    else:
                        tmp['rest_number'] = rest_number
                    tmp['is_on_sale'] = is_on_sale
                    price_info_list.append(tmp)

            if price_info_list == []:
                print('price_info_list为空值')
                return {}

            # 商品价格和淘宝价
            tmp_price_list = sorted([round(float(item.get('detail_price', '')), 2) for item in price_info_list])
            price = tmp_price_list[-1]  # 商品价格
            taobao_price = tmp_price_list[0]  # 淘宝价

            if detail_name_list == []:
                print('## detail_name_list为空值 ##')
                price_info_list = []

            # print('最高价为: ', price)
            # print('最低价为: ', taobao_price)
            # print(len(price_info_list))
            # pprint(price_info_list)

            # 所有示例图片地址
            all_img_url = [{'img_url': item} for item in data.get('goods', {}).get('topGallery', [])]
            # print(all_img_url)

            # 详细信息标签名对应属性
            tmp_p_value = re.compile(r'\n').sub('', data.get('goods', {}).get('goodsDesc', ''))
            tmp_p_value = re.compile(r'\t').sub('', tmp_p_value)
            tmp_p_value = re.compile(r'  ').sub('', tmp_p_value)
            p_info = [{'p_name': '商品描述', 'p_value': tmp_p_value}]
            # print(p_info)

            # 总销量
            all_sell_count = data.get('goods', {}).get('sales', 0)

            # div_desc
            div_desc = data.get('div_desc', '')

            # 商品销售时间区间
            schedule = [{
                'begin_time': self.timestamp_to_regulartime(data.get('goods', {}).get('groupTypes', [])[0].get('startTime')),
                'end_time': self.timestamp_to_regulartime(data.get('goods', {}).get('groupTypes', [])[0].get('endTime')),
            }]
            # pprint(schedule)

            # 用于判断商品是否已经下架
            is_delete = 0

            result = {
                'shop_name': shop_name,                 # 店铺名称
                'account': account,                     # 掌柜
                'title': title,                         # 商品名称
                'sub_title': sub_title,                 # 子标题
                # 'shop_name_url': shop_name_url,        # 店铺主页地址
                'price': price,                         # 商品价格
                'taobao_price': taobao_price,           # 淘宝价
                # 'goods_stock': goods_stock,            # 商品库存
                'detail_name_list': detail_name_list,   # 商品标签属性名称
                # 'detail_value_list': detail_value_list,# 商品标签属性对应的值
                'price_info_list': price_info_list,     # 要存储的每个标签对应规格的价格及其库存
                'all_img_url': all_img_url,             # 所有示例图片地址
                'p_info': p_info,                       # 详细信息标签名对应属性
                'div_desc': div_desc,                   # div_desc
                'schedule': schedule,                   # 商品开卖时间和结束开卖时间
                'all_sell_count': all_sell_count,       # 商品总销售量
                'is_delete': is_delete                  # 用于判断商品是否已经下架
            }
            # pprint(result)
            # print(result)
            # wait_to_send_data = {
            #     'reason': 'success',
            #     'data': result,
            #     'code': 1
            # }
            # json_data = json.dumps(wait_to_send_data, ensure_ascii=False)
            # print(json_data)
            return result

        else:
            print('待处理的data为空的dict, 该商品可能已经转移或者下架')
            return {}

    def to_right_and_update_data(self, data, pipeline):
        data_list = data
        tmp = {}
        tmp['goods_id'] = data_list['goods_id']  # 官方商品id

        '''
        时区处理，时间处理到上海时间
        '''
        tz = pytz.timezone('Asia/Shanghai')  # 创建时区对象
        now_time = datetime.datetime.now(tz)
        # 处理为精确到秒位，删除时区信息
        now_time = re.compile(r'\..*').sub('', str(now_time))
        # 将字符串类型转换为datetime类型
        now_time = datetime.datetime.strptime(now_time, '%Y-%m-%d %H:%M:%S')

        tmp['modfiy_time'] = now_time  # 修改时间

        tmp['shop_name'] = data_list['shop_name']  # 公司名称
        tmp['title'] = data_list['title']  # 商品名称
        tmp['sub_title'] = data_list['sub_title']  # 商品子标题
        tmp['link_name'] = ''  # 卖家姓名
        tmp['account'] = data_list['account']  # 掌柜名称

        # 设置最高价price， 最低价taobao_price
        tmp['price'] = Decimal(data_list['price']).__round__(2)
        tmp['taobao_price'] = Decimal(data_list['taobao_price']).__round__(2)
        tmp['price_info'] = []  # 价格信息

        tmp['detail_name_list'] = data_list['detail_name_list']  # 标签属性名称

        """
        得到sku_map
        """
        tmp['price_info_list'] = data_list.get('price_info_list')  # 每个规格对应价格及其库存

        tmp['all_img_url'] = data_list.get('all_img_url')  # 所有示例图片地址

        tmp['p_info'] = data_list.get('p_info')  # 详细信息
        tmp['div_desc'] = data_list.get('div_desc')  # 下方div

        tmp['schedule'] = data_list.get('schedule')

        # 采集的来源地
        # tmp['site_id'] = 13  # 采集来源地(拼多多常规商品)

        tmp['is_delete'] = data_list.get('is_delete')  # 逻辑删除, 未删除为0, 删除为1
        tmp['my_shelf_and_down_time'] = data_list.get('my_shelf_and_down_time')
        tmp['delete_time'] = data_list.get('delete_time')
        tmp['all_sell_count'] = str(data_list.get('all_sell_count'))

        pipeline.update_pinduoduo_table(item=tmp)

    def insert_into_pinduoduo_xianshimiaosha_table(self, data, pipeline):
        data_list = data
        tmp = {}
        tmp['goods_id'] = data_list['goods_id']  # 官方商品id
        tmp['spider_url'] = data_list['spider_url']  # 商品地址
        tmp['username'] = data_list['username']  # 操作人员username

        '''
        时区处理，时间处理到上海时间
        '''
        tz = pytz.timezone('Asia/Shanghai')  # 创建时区对象
        now_time = datetime.datetime.now(tz)
        # 处理为精确到秒位，删除时区信息
        now_time = re.compile(r'\..*').sub('', str(now_time))
        # 将字符串类型转换为datetime类型
        now_time = datetime.datetime.strptime(now_time, '%Y-%m-%d %H:%M:%S')

        tmp['deal_with_time'] = now_time  # 操作时间
        tmp['modfiy_time'] = now_time  # 修改时间

        tmp['shop_name'] = data_list['shop_name']  # 公司名称
        tmp['title'] = data_list['title']  # 商品名称
        tmp['sub_title'] = data_list['sub_title']  # 商品子标题

        # 设置最高价price， 最低价taobao_price
        tmp['price'] = Decimal(data_list['price']).__round__(2)
        tmp['taobao_price'] = Decimal(data_list['taobao_price']).__round__(2)

        tmp['detail_name_list'] = data_list['detail_name_list']  # 标签属性名称

        """
        得到sku_map
        """
        tmp['price_info_list'] = data_list.get('price_info_list')  # 每个规格对应价格及其库存

        tmp['all_img_url'] = data_list.get('all_img_url')  # 所有示例图片地址

        tmp['p_info'] = data_list.get('p_info')  # 详细信息
        tmp['div_desc'] = data_list.get('div_desc')  # 下方div

        tmp['schedule'] = data_list.get('schedule')
        tmp['stock_info'] = data_list.get('stock_info')
        tmp['miaosha_time'] = data_list.get('miaosha_time')
        tmp['miaosha_begin_time'] = data_list.get('miaosha_begin_time')
        tmp['miaosha_end_time'] = data_list.get('miaosha_end_time')

        # 采集的来源地
        tmp['site_id'] = 16  # 采集来源地(卷皮秒杀商品)

        tmp['is_delete'] = data_list.get('is_delete')  # 逻辑删除, 未删除为0, 删除为1
        # print('is_delete=', tmp['is_delete'])

        # print('------>>>| 待存储的数据信息为: |', tmp)
        print('------>>>| 待存储的数据信息为: ', tmp.get('goods_id'))

        pipeline.insert_into_pinduoduo_xianshimiaosha_table(item=tmp)

    def to_update_pinduoduo_xianshimiaosha_table(self, data, pipeline):
        data_list = data
        tmp = {}
        tmp['goods_id'] = data_list['goods_id']  # 官方商品id

        '''
        时区处理，时间处理到上海时间
        '''
        tz = pytz.timezone('Asia/Shanghai')  # 创建时区对象
        now_time = datetime.datetime.now(tz)
        # 处理为精确到秒位，删除时区信息
        now_time = re.compile(r'\..*').sub('', str(now_time))
        # 将字符串类型转换为datetime类型
        now_time = datetime.datetime.strptime(now_time, '%Y-%m-%d %H:%M:%S')

        tmp['modfiy_time'] = now_time  # 修改时间

        tmp['shop_name'] = data_list['shop_name']  # 公司名称
        tmp['title'] = data_list['title']  # 商品名称
        tmp['sub_title'] = data_list['sub_title']

        # 设置最高价price， 最低价taobao_price
        tmp['price'] = Decimal(data_list['price']).__round__(2)
        tmp['taobao_price'] = Decimal(data_list['taobao_price']).__round__(2)

        tmp['detail_name_list'] = data_list['detail_name_list']  # 标签属性名称

        """
        得到sku_map
        """
        tmp['price_info_list'] = data_list.get('price_info_list')  # 每个规格对应价格及其库存

        tmp['all_img_url'] = data_list.get('all_img_url')  # 所有示例图片地址

        tmp['p_info'] = data_list.get('p_info')  # 详细信息
        tmp['div_desc'] = data_list.get('div_desc')  # 下方div

        tmp['schedule'] = data_list.get('schedule')
        tmp['stock_info'] = data_list.get('stock_info')
        tmp['miaosha_time'] = data_list.get('miaosha_time')
        tmp['miaosha_begin_time'] = data_list.get('miaosha_begin_time')
        tmp['miaosha_end_time'] = data_list.get('miaosha_end_time')

        tmp['is_delete'] = data_list.get('is_delete')  # 逻辑删除, 未删除为0, 删除为1
        # print('is_delete=', tmp['is_delete'])

        # print('------>>> | 待存储的数据信息为: |', tmp)
        print('------>>>| 待存储的数据信息为: |', tmp.get('goods_id'))

        pipeline.update_pinduoduo_xianshimiaosha_table(tmp)

    def get_url_body_by_requests(self, tmp_url):
        '''
        返回给与url的body
        :param tmp_url:
        :return: str
        '''
        # 设置代理ip
        ip_object = MyIpPools()
        self.proxies = ip_object.get_proxy_ip_from_ip_pool()  # {'http': ['xx', 'yy', ...]}
        self.proxy = self.proxies['http'][randint(0, len(self.proxies) - 1)]

        tmp_proxies = {
            'http': self.proxy,
        }
        # print('------>>>| 正在使用代理ip: {} 进行爬取... |<<<------'.format(self.proxy))

        try:
            response = requests.get(tmp_url, headers=self.headers, proxies=tmp_proxies, timeout=10)  # 在requests里面传数据，在构造头时，注意在url外头的&xxx=也得先构造
            body = response.content.decode('utf-8')
            # print(body)

            # 过滤
            body = re.compile(r'\n').sub('', body)
            body = re.compile(r'\t').sub('', body)
            body = re.compile(r'  ').sub('', body)
            # print(body)
        except Exception:
            print('requests.get()请求超时....')
            self.result_data = {}  # 重置下，避免存入时影响下面爬取的赋值
            body = ''

        return body

    def get_url_body(self, tmp_url):
        '''
        返回给与的url的body
        :param tmp_url:
        :return: str
        '''
        tmp = self.from_ip_pool_set_proxy_ip_to_phantomjs()
        if tmp == '':
            return ''
        self.driver.set_page_load_timeout(10)  # 设置成10秒避免数据出错

        try:
            self.driver.get(tmp_url)
            self.driver.implicitly_wait(15)
            body = self.driver.page_source
            body = re.compile(r'\n').sub('', body)
            body = re.compile(r'\t').sub('', body)
            body = re.compile(r'  ').sub('', body)
            # print(body)

        except Exception as e:  # 如果超时, 终止加载并继续后续操作
            print('-->>time out after 10 seconds when loading page')
            try:
                self.driver.execute_script('window.stop()')  # 当页面加载时间超过设定时间，通过执行Javascript来stop加载，即可执行后续动作
            except:
                pass
            body = ''

        return body

    def init_phantomjs(self):
        """
        初始化带cookie的驱动，之所以用phantomjs是因为其加载速度很快(快过chrome驱动太多)
        """
        '''
        研究发现, 必须以浏览器的形式进行访问才能返回需要的东西
        常规requests模拟请求会被服务器过滤, 并返回请求过于频繁的无用页面
        '''
        print('--->>>初始化phantomjs驱动中<<<---')
        cap = webdriver.DesiredCapabilities.PHANTOMJS
        cap['phantomjs.page.settings.resourceTimeout'] = 1000  # 1秒
        cap['phantomjs.page.settings.loadImages'] = False
        cap['phantomjs.page.settings.disk-cache'] = True
        cap['phantomjs.page.settings.userAgent'] = HEADERS[randint(0, 34)]  # 随机一个请求头
        # cap['phantomjs.page.customHeaders.Cookie'] = cookies

        self.driver = webdriver.PhantomJS(executable_path=EXECUTABLE_PATH, desired_capabilities=cap)

        wait = ui.WebDriverWait(self.driver, 15)  # 显示等待n秒, 每过0.5检查一次页面是否加载完毕
        print('------->>>初始化完毕<<<-------')

    def from_ip_pool_set_proxy_ip_to_phantomjs(self):
        ip_object = MyIpPools()
        ip_list = ip_object.get_proxy_ip_from_ip_pool().get('http')
        proxy_ip = ''
        try:
            proxy_ip = ip_list[randint(0, len(ip_list) - 1)]        # 随机一个代理ip
        except Exception:
            print('从ip池获取随机ip失败...正在使用本机ip进行爬取!')
        # print('------>>>| 正在使用的代理ip: {} 进行爬取... |<<<------'.format(proxy_ip))
        proxy_ip = re.compile(r'http://').sub('', proxy_ip)     # 过滤'http://'
        proxy_ip = proxy_ip.split(':')                          # 切割成['xxxx', '端口']

        try:
            tmp_js = {
                'script': 'phantom.setProxy({}, {});'.format(proxy_ip[0], proxy_ip[1]),
                'args': []
            }
            self.driver.command_executor._commands['executePhantomScript'] = ('POST', '/session/$sessionId/phantom/execute')
            self.driver.execute('executePhantomScript', tmp_js)
        except Exception:
            print('动态切换ip失败')
            return ''
            pass

    def set_cookies_key_api_uid(self):
        '''
        给headers增加一个cookie, 里面有个key名字为api_uid
        :return:
        '''
        # 设置代理ip
        ip_object = MyIpPools()
        self.proxies = ip_object.get_proxy_ip_from_ip_pool()  # {'http': ['xx', 'yy', ...]}
        self.proxy = self.proxies['http'][randint(0, len(self.proxies) - 1)]

        tmp_proxies = {
            'http': self.proxy,
        }
        # 得到cookie中的key名为api_uid的值
        host_url = 'http://mobile.yangkeduo.com'
        try:
            response = requests.get(host_url, headers=self.headers, proxies=tmp_proxies, timeout=10)  # 在requests里面传数据，在构造头时，注意在url外头的&xxx=也得先构造
            api_uid = response.cookies.get('api_uid')
            # print(response.cookies.items())
            # if api_uid is None:
            #     api_uid = 'rBQh+FoXerAjQWaAEOcpAg=='
            self.headers['Cookie'] = 'api_uid=' + str(api_uid) + ';'
            # print(api_uid)
        except Exception:
            print('requests.get()请求超时....')
            pass

    def timestamp_to_regulartime(self, timestamp):
        '''
        将时间戳转换成时间
        '''
        # 利用localtime()函数将时间戳转化成localtime的格式
        # 利用strftime()函数重新格式化时间

        # 转换成localtime
        time_local = time.localtime(timestamp)
        # 转换成新的时间格式(2016-05-05 20:28:54)
        dt = time.strftime("%Y-%m-%d %H:%M:%S", time_local)

        return dt

    def get_goods_id_from_url(self, pinduoduo_url):
        '''
        得到goods_id
        :param pinduoduo_url:
        :return: goods_id (类型str)
        '''
        is_pinduoduo_url = re.compile(r'http://mobile.yangkeduo.com/goods.html.*?').findall(pinduoduo_url)
        if is_pinduoduo_url != []:
            if re.compile(r'http://mobile.yangkeduo.com/goods.html\?.*?goods_id=(\d+).*?').findall(pinduoduo_url) != []:
                tmp_pinduoduo_url = re.compile(r'http://mobile.yangkeduo.com/goods.html\?.*?goods_id=(\d+).*?').findall(pinduoduo_url)[0]
                if tmp_pinduoduo_url != '':
                    goods_id = tmp_pinduoduo_url
                else:   # 只是为了在pycharm里面测试，可以不加
                    pinduoduo_url = re.compile(r';').sub('', pinduoduo_url)
                    goods_id = re.compile(r'http://mobile.yangkeduo.com/goods.html\?.*?goods_id=(\d+).*?').findall(pinduoduo_url)[0]
                print('------>>>| 得到的拼多多商品id为:', goods_id)
                return goods_id
            else:
                pass
        else:
            print('拼多多商品url错误, 非正规的url, 请参照格式(http://mobile.yangkeduo.com/goods.html)开头的...')
            return ''

    def __del__(self):
        try:
            self.driver.quit()
        except:
            pass
        gc.collect()

if __name__ == '__main__':
    pinduoduo = PinduoduoParse()
    while True:
        pinduoduo_url = input('请输入待爬取的拼多多商品地址: ')
        pinduoduo_url.strip('\n').strip(';')
        goods_id = pinduoduo.get_goods_id_from_url(pinduoduo_url)
        data = pinduoduo.get_goods_data(goods_id=goods_id)
        pinduoduo.deal_with_data()