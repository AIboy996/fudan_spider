import os
from functools import wraps

from bark import bark

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
    示例输出：
    {
        'draw': 0,
        'recordsTotal': 1,
        'recordsFiltered': 1,
        'data': [['xxxx', # 学号
                'xx', # 姓名
                '正常',
                '是(江湾;枫林;张江;邯郸)',
                '2026-07-15',
                '64.90']]
    }
    """
    # set headers
    se.post("https://my.fudan.edu.cn/data_tables/ykt_xx.json")
    # true request
    res = se.post("https://my.fudan.edu.cn/data_tables/ykt_xx.json").json()
    return (res["data"][0][1] + "一卡通余额", float(res["data"][0][-1]))


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
    res = se.get("https://zlapp.fudan.edu.cn/fudanelec/wap/default/info").json()
    return (
        res["d"]["xq"] + res["d"]["ssmc"] + res["d"]["fjmc"] + "电量余量",
        float(res["d"]["fj_surplus"]),
    )


if __name__ == "__main__":
    se = Session()
    login(se)
    print(get_balance(se))
    print(get_dom_elec_surplus(se))
