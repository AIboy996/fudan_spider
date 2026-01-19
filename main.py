import os
import re
from functools import wraps

from bark import bark
from rsa import rsa_encrypt

from requests import Session
from parsel import Selector


def retry(n: int):
    """如果遇到报错，重新尝试n次"""

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for i in range(1, n + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    # 重试了n次依然有错误，直接抛出一个错误
                    # 这会触发连锁的错误 During handling of the above exception, another exception occurred
                    if i == n:
                        raise Exception(
                            f"Retry for {n} times. Still get error: {repr(e)}"
                        )

        return wrapper

    return decorator


def warn_wrapper(threshold: float):
    """在函数返回值低于threshold的时候发出警告"""

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            name, value = func(*args, **kwargs)
            if value < threshold:
                bark(
                    title=name,
                    body=str(value),
                    group="FDU",
                    token=os.getenv("bark_token"),
                    icon="https://assets.elearning.fudan.edu.cn/cdn/brand/20200226/xiaohui.gif",
                )
            return name, value

        return wrapper

    return decorator


@retry(3)
def login(se: Session):
    res = se.get("https://uis.fudan.edu.cn/authserver/login")
    sel = Selector(res.text)
    hidden_input = dict(
        zip(
            sel.css("#casLoginForm > input[type=hidden]::attr(name)").getall(),
            sel.css("#casLoginForm > input[type=hidden]::attr(value)").getall(),
        )
    )
    res = se.post(
        url="https://uis.fudan.edu.cn/authserver/login",
        data={
            "username": os.getenv("fudan_username"),
            "password": os.getenv("fudan_password"),
            **hidden_input,
        },
    )
    assert "安全退出" in res.text, "登陆失败"


@retry(3)
@warn_wrapper(20)
def get_balance(se: Session):
    """
    获取一卡通余额
    """
    content = se.get("https://ecard.fudan.edu.cn/epay/myepay/index").text
    sel = Selector(text=content)
    name = sel.css(".custname::text").get()[3:].replace("！", "")
    balance = sel.css(
        "div.payway-box-bottom > div:nth-child(1) > p:nth-child(1)::text"
    ).get()
    return (name + "一卡通余额", float(balance))


@retry(3)
@warn_wrapper(30)
def get_dom_elec_surplus(se: Session):
    """
    查询宿舍电费余量
    示例输出：
    {
        'e': 0,
        'm': '操作成功',
        'd': {
            'xq': '北区',
            'ting': False,
            'xqid': '10',
            'roomid': '1173',
            'tingid': '',
            'realname': '张杨',
            'ssmc': '999号楼',
            'fjmc': '909A',
            'fj_update_time': '',
            'fj_used': 15788.2,
            'fj_all': 16016.4,
            'fj_surplus': 228.2,
            't_update_time': 0,
            't_used': 0,
            't_all': 0,
            't_surplus': 0
        }
    }
    """
    # 不断重定向，直到拿到lck参数
    res = se.get(
        r"https://zlapp.fudan.edu.cn/fudanelec/wap/default/info", allow_redirects=False
    )
    while res.status_code == 302 or res.status_code == 301:
        location = res.headers.get("Location")
        if "lck=" in location:
            break
        res = se.get(location, allow_redirects=False)
    # 提取lck参数
    location = res.headers.get("Location")
    lck = re.search("lck=(.*?)&", location).group(1)
    res = se.get(location)
    # 请求认证方法
    queryAuthMethods = se.post(
        "https://id.fudan.edu.cn/idp/authn/queryAuthMethods",
        json={"entityId": "https://zlapp.fudan.edu.cn", "lck": lck},
    )
    # 使用账号密码认证
    passwd_way = queryAuthMethods.json()["data"][0]
    assert passwd_way["moduleCode"] == "userAndPwd"
    authChainCode = passwd_way["authChainCode"]
    # 请求rsa公钥
    getJsPublicKey = se.get("https://id.fudan.edu.cn/idp/authn/getJsPublicKey")
    pub_key = getJsPublicKey.json()["data"]
    # 构造登录参数
    d = {
        "authModuleCode": "userAndPwd",
        "authChainCode": authChainCode,
        "entityId": "https://zlapp.fudan.edu.cn",
        "requestType": "chain_type",
        "lck": lck,
        "authPara": {
            "loginName": os.getenv("fudan_username"),
            "password": rsa_encrypt(os.getenv("fudan_password"), pub_key),
            "verifyCode": "",
        },
    }
    # 提交登录请求
    loginToken = se.post(
        "https://id.fudan.edu.cn/idp/authn/authExecute", json=d, allow_redirects=False
    )
    # 登录完成之后请求zlapp的授权
    res = se.post(
        "https://id.fudan.edu.cn/idp/authCenter/authnEngine?locale=zh-CN",
        data={"loginToken": loginToken.json()["loginToken"]},
    )
    # 授权平台会给我们一个直链
    auth_link = (
        re.search('locationValue = "(.*?)"', res.text).group(1).replace("&amp;", "&")
    )
    # 访问直链，获取电费信息
    res = se.get(auth_link).json()
    return (
        res["d"]["xq"] + res["d"]["ssmc"] + res["d"]["fjmc"] + "电量余量",
        float(res["d"]["fj_surplus"]),
    )


if __name__ == "__main__":
    se = Session()
    login(se)
    # print(get_balance(se))
    print(get_dom_elec_surplus(se))
