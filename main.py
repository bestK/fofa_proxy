import asyncio
import os
import requests
from bs4 import BeautifulSoup

import base64
import aiohttp


def encode_to_base64(plain_text):
    """
    将明文字符串编码为Base64
    """
    base64_bytes = base64.b64encode(plain_text.encode("utf-8"))
    return base64_bytes.decode("utf-8")


def fofa_query(plain_text):
    """
    获取使用明文参数构建的URL中所有 span.hsxa-host > a 元素的 href 属性

    :param plain_text: 明文参数
    :return: href 属性列表
    """
    base64_param = encode_to_base64(plain_text)
    url = f"https://fofa.info/result?qbase64={base64_param}"

    try:
        # 发送HTTP请求
        response = requests.get(url)
        response.raise_for_status()  # 检查请求是否成功

        # 解析网页内容
        soup = BeautifulSoup(response.content, "html.parser")

        # 查找所有 span.hsxa-host > a 元素
        links = soup.select("span.hsxa-host > a")

        # 提取 href 属性
        hrefs = [link.get("href") for link in links]

        return hrefs

    except requests.RequestException as e:
        print(f"请求错误: {e}")
        return []


async def check_proxy(session, proxy, test_url):
    """
    检查单个代理是否可用
    """
    try:
        proxies = {
            "http": proxy,
            "https": proxy,
        }

        async with session.get(test_url, proxy=proxies, timeout=5) as response:
            return response.status == 200
    except requests.RequestException:
        return False


async def check_proxies(proxies, test_url):
    """
    异步检查代理是否可用
    """
    valid_proxies = []
    async with aiohttp.ClientSession() as session:
        tasks = [check_proxy(session, proxy, test_url) for proxy in proxies]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for proxy, result in zip(proxies, results):
            if result:
                valid_proxies.append(proxy)
                print(f"{proxy} 可用")
            else:
                print(f"{proxy} 不可用")
    return valid_proxies


async def parse_proxy(hrefs):
    """
    检查链接中的代理是否可用
    """
    all_proxies = []

    for href in hrefs:
        try:
            response = requests.get(f"{href}/all", timeout=5)
            response.raise_for_status()  # 检查响应是否成功
            proxys = response.json()
            proxy_list = [p["proxy"] for p in proxys]
            valid_proxies = await check_proxies(proxy_list, "http://www.baidu.com")
            all_proxies.extend(valid_proxies)
        except requests.RequestException as e:
            print(f"请求错误: {e}")

    return all_proxies


if __name__ == "__main__":
    # 使用示例
    plain_text = 'body="get all proxy from proxy pool"'
    hrefs = fofa_query(plain_text)

    valid_proxies = asyncio.run(parse_proxy(hrefs))

    file_path = "latest.txt"

    if not os.path.exists(file_path):
        with open(file_path, "w") as f:
            f.write("")
        print(f"文件 {file_path} 已创建")

    # 读取 proxy.txt
    with open(file_path, "r+") as f:
        valid_proxies_old = f.read().splitlines()
        valid_proxies.extend(
            asyncio.run(check_proxies(valid_proxies_old, "http://www.baidu.com"))
        )
        # 清空文件
        f.seek(0)
        f.truncate()
        for proxy in valid_proxies:
            f.write(proxy + "\n")
