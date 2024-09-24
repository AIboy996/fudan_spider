# fudan spider
> 基于[Bark](https://bark.day.app/#/)

## 功能
定时查询：
- 宿舍电量余额
    - 低于30kwh触发Bark通知
- 一卡通余额
    - 低于20元触发Bark通知

Bark通知示例：

<img src="assets/2024-09-25-01-58-22.png" width="300">

## 使用方法

1. Fork本仓库
2. 添加Environments
![](assets/2024-09-25-02-10-15.png)
3. 配置环境变量

- FUDAN_USERNAME: UIS学号
- FUDAN_PASSWORD: UIS密码
- BARK_TOKEN: bark通知的token

![](assets/2024-09-25-02-10-40.png)

## TODO

- 增加更多定时查询内容
    - 绩点？
- 增加更多通知方式
    - 邮件？
