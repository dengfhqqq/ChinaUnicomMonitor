# ChinaUnicomMonitor (联通余量监控)

> **⚠️ 声明**：本项目基于网络公开的 JS 脚本逻辑重构，**全权由 AI (Gemini) 协助编写与优化**。本人（作者）仅做搬运、测试与维护，核心逻辑均源自原版思路。

## 📖 简介

这是一个运行在 **青龙面板** 等环境下的 Python 脚本，用于监控中国联通的话费与流量余额。
为了应对不同的使用场景，本项目提供了 **两个版本**（拉库时会自动同时下载）：

| 版本文件 | 核心凭证 | 优点 | 缺点 | 适用人群 |
| :--- | :--- | :--- | :--- | :--- |
| **`ChinaUnicom_Token.py`** | `token_online` | 理论上 Token 长期有效，不受切号影响 | 同一设备频繁运行/抓包易触发风控 (Code:3) | 单账号用户，或有多台设备抓包的用户 |
| **`ChinaUnicom_Cookie.py`** | `Cookie` | **极其安全**，不涉及登录操作，不易风控 | **APP 一旦切号，Cookie 立即失效**，需重抓 | 多账号频繁切换、已被风控的用户 |

---

## 🚀 青龙部署 (一键拉取双版本)

**直接在青龙面板添加一条【订阅/定时】任务：**

```bash
ql repo https://github.com/dengfhqqq/ChinaUnicomMonitor.git "ChinaUnicom_" "" "requirements.txt" "main"
说明：

此命令会自动拉取 Token版 和 Cookie版 两个脚本。

拉取完成后，请在定时任务列表中，启用你需要的那一个版本，禁用另一个即可。

建议定时规则：0 9,19 * * * (每天早晚9点运行)。

🛠 抓包与配置指南
🅰️ Token 版配置 (ChinaUnicom_Token.py)
1. 获取 Token (注意接口变化)

打开联通 APP -> 退出登录 -> 切换账号登录。

开启抓包工具 -> 使用 短信验证码 登录。

搜索接口：https://loginxhm.10010.com/mobileService/onLine.htm

在 请求体 (Body) 中找到 token_online 的值。

2. 环境变量

Bash

export chinaUnicomCookie="你的token"  # 多账号用 & 或换行隔开
export UNICOM_MONITOR_LIMIT="30"     # (可选) 开启免流跳点监控，单位MB
🅱️ Cookie 版配置 (ChinaUnicom_Cookie.py)
1. 获取 Cookie

打开联通 APP -> 登录账号。

开启抓包工具 -> 在首页随便点点（如查询余额）。

搜索接口：mobileService 或 balancenew。

在 请求头 (Header) 中复制完整的 Cookie 字符串。

2. 环境变量 (注意变量名不同)

Bash

# 格式：手机号&Cookie
export CHINA_UNICOM_COOKIES="186xxxx&JSESSIONID=..." 
✨ 通用功能 (两个版本都有)
进度条展示：[■■■■□] 实心代表已用，空心代表剩余。

Bark 防爆：支持逐条推送，防止多账号合并导致消息太长被丢弃。

分流推送：设置 UNICOM_PUSH_CFG="1,3" 可只推送第 1 和第 3 个账号，其他账号仅在日志显示。

⚠️ 免责声明
本项目仅供 Python 学习与技术交流，请勿用于商业用途。

脚本中涉及的 APP_ID 和 USER_AGENT 均为联通 APP 公开通用的客户端标识，不包含任何个人设备隐私信息。

使用本脚本产生的任何后果由使用者自行承担。