# coding:utf-8

'''
@author = super_fazai
@File    : my_requests.py
@Time    : 2017/3/22 10:13
@connect : superonesfazai@gmail.com
'''

import requests
from random import randint
from my_ip_pools import MyIpPools
import re, gc
from pprint import pprint

__all__ = [
    'MyRequests',
]

class MyRequests(object):
    def __init__(self):
        super().__init__()

    @classmethod
    def get_url_body(cls, url, headers:dict, params:dict=None, had_referer=False):
        '''
        根据url得到body
        :param tmp_url:
        :return: '' 表示出错退出 | body 类型str
        '''
        # 设置代理ip
        ip_object = MyIpPools()
        proxies = ip_object.get_proxy_ip_from_ip_pool()  # {'http': ['xx', 'yy', ...]}
        proxy = proxies['http'][randint(0, len(proxies) - 1)]

        tmp_proxies = {
            'http': proxy,
        }
        # print('------>>>| 正在使用代理ip: {} 进行爬取... |<<<------'.format(self.proxy))

        tmp_headers = headers
        tmp_headers['Host'] = re.compile(r'://(.*?)/').findall(url)[0]
        if had_referer:
            if re.compile(r'https').findall(url) != []:
                tmp_headers['Referer'] = 'https://' + tmp_headers['Host'] + '/'
            else:
                tmp_headers['Referer'] = 'http://' + tmp_headers['Host'] + '/'

        s = requests.session()
        try:
            if params is not None:
                response = s.get(url, headers=tmp_headers, params=params, proxies=tmp_proxies, timeout=12)  # 在requests里面传数据，在构造头时，注意在url外头的&xxx=也得先构造
            else:
                response = s.get(url, headers=tmp_headers, proxies=tmp_proxies, timeout=12)  # 在requests里面传数据，在构造头时，注意在url外头的&xxx=也得先构造
            body = response.content.decode('utf-8')

            body = re.compile('\t').sub('', body)
            body = re.compile('  ').sub('', body)
            body = re.compile('\r\n').sub('', body)
            body = re.compile('\n').sub('', body)
            # print(body)
        except Exception:
            print('requests.get()请求超时....')
            print('data为空!')
            body = ''

        return body

    def __del__(self):
        gc.collect()

def test():
    url = 'http://s.h5.jumei.com/yiqituan/ajaxDetail'
    headers = {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9',
        'Cache-Control': 'max-age=0',
        'Connection': 'keep-alive',
        'Host': 's.h5.jumei.com',
        'Referer': 'http://s.h5.jumei.com/yiqituan/detail?item_id=ht180321p2453550t4&type=global_deal',
        'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 10_3_3 like Mac OS X) AppleWebKit/603.3.8 (KHTML, like Gecko) Mobile/14G60 MicroMessenger/6.5.18 NetType/WIFI Language/en',
        'X-Requested-With': 'XMLHttpRequest',
        'Cookie': '__utmz=154994554.1521857121.1.1.utmcsr=(direct)|utmccn=(direct)|utmcmd=(none);__utmc=154994554;__utmb=154994554.1.10.1521857121;__utma=154994554.1748749410.1521857121.1521857121.1521857121.1;__utmt=1;Hm_lpvt_884477732c15fb2f2416fb892282394b=1521857121;Hm_lvt_884477732c15fb2f2416fb892282394b=1521518580,1521857121;device_platform=other;has_download=1;guide_download_show=1;referer_site_cps=wap_touch_;referer_site=wap_touch_;sid=591dae285c6f5fba895afe3e8688247d;PHPSESSID=591dae285c6f5fba895afe3e8688247d;',
    }

    params = {
        'item_id': 'ht180321p2453550t4',
        'type': 'global_deal',
    }

    body = MyRequests().get_url_body(url=url, headers=headers, params=params)
    print(body)

test()
