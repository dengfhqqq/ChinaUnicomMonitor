# encoding: utf-8
"""
cron: 0 9,21 * * *
new Env('联通余量监控');
"""

import requests
联通余量查询 (进度条反转 + 日志增强版)

【更新说明】
1. 进度条逻辑: 实心(■)=已用，空心(□)=剩余。
   - 例子: 用了90% -> [■■■■■■■■■□]
2. 日志输出: 无论是否推送，青龙面板日志都会打印详细信息。
3. 兼容性: 沿用 chinaUnicomCookie 变量和 Token 登录。

【环境变量】
export chinaUnicomCookie="token1&token2"
export UNICOM_PUSH_CFG="1,2"   (可选: 指定推送第几个号)
export UNICOM_DETAIL_LEVEL="1" (可选: 1=显示详细流量包，不创建或者0=简约版)
"""

import requests
import time
import os
import re
from datetime import datetime

# 尝试导入 notify
try:
    from notify import send
except ImportError:
    def send(title, content):
        print(f"\n【推送预览】{title}\n{content}")

# --- 配置区 ---
USER_AGENT = "Mozilla/5.0 (iPhone; CPU iPhone OS 16_1_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 unicom{version:iphone_c@11.0503}"
APP_ID = "86b8be06f56ba55e9fa7dff134c6b16c62ca7f319da4a958dd0afa0bf9f36f1daa9922869a8d2313b6f2f9f3b57f2901f0021c4575e4b6949ae18b7f6761d465c12321788dcd980aa1a641789d1188bb"
APP_VERSION = "iphone_c@11.0503"

# --- 环境变量读取 ---
def get_env_config():
    # 1. 获取 Token
    tokens_env = os.getenv('chinaUnicomCookie')
    token_list = []
    if tokens_env:
        raw_items = re.split(r'[&\n@]', tokens_env)
        for item in raw_items:
            item = item.strip()
            if not item: continue
            token = item.split('#')[0].strip()
            if token:
                token_list.append(token)
    
    # 2. 推送配置
    push_cfg_str = os.getenv('UNICOM_PUSH_CFG', '')
    push_indices = []
    if push_cfg_str:
        try:
            push_indices = [int(x) for x in re.split(r'[,，]', push_cfg_str) if x.strip()]
        except:
            print("⚠️ 推送配置格式错误，默认全部推送")
            
    # 3. 详细模式
    is_detailed = os.getenv('UNICOM_DETAIL_LEVEL', '0') == '1'

    return token_list, push_indices, is_detailed

# --- 核心功能 ---
def unicom_login(token):
    session = requests.Session()
    headers = {"User-Agent": USER_AGENT, "Content-Type": "application/x-www-form-urlencoded"}
    data = {
        "token_online": token,
        "reqtime": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "appId": APP_ID, "version": APP_VERSION, "step": "bindlist", "isFirstInstall": 0, "deviceModel": "iPhone"
    }
    try:
        resp = session.post('https://m.client.10010.com/mobileService/onLine.htm', headers=headers, data=data, timeout=15)
        res = resp.json()
        if res.get('code') == '0': return session, res.get('desmobile', '未知号码')
    except: pass
    return None, None

def fetch_data(session):
    h = {"User-Agent": USER_AGENT, "Referer": "https://img.client.10010.com/"}
    try: fee = session.post('https://m.client.10010.com/servicequerybusiness/balancenew/accountBalancenew.htm', headers=h, timeout=10).json()
    except: fee = None
    try: flow = session.post('https://m.client.10010.com/servicequerybusiness/operationservice/queryOcsPackageFlowLeftContentRevisedInJune', headers=h, timeout=10).json()
    except: flow = None
    return fee, flow

# --- 视觉工具 (进度条逻辑已反转) ---
def format_flow(size_mb):
    try:
        size_mb = float(size_mb)
        if size_mb >= 1024: return f"{size_mb / 1024:.2f}GB"
        return f"{size_mb:.2f}MB"
    except: return "0MB"

def make_bar(percent_used, length=10):
    """
    生成进度条: 实心代表【已用】，空心代表【剩余】
    percent_used: 已使用的百分比 (0-100)
    """
    try:
        percent = max(0, min(100, float(percent_used)))
        fill = int(length * percent / 100)
        # ■ = 已用, □ = 剩余
        return f"[{'■'*fill}{'□'*(length-fill)}]"
    except:
        return f"[{'□'*length}]"

# --- 数据解析 ---
def parse_report(fee_data, flow_data, is_detailed):
    msgs = []
    
    # 1. 话费
    if fee_data and fee_data.get('code') == '0000':
        balance = float(fee_data.get('curntbalancecust', '0'))
        spent = float(fee_data.get('realfeecustnew', '0'))
        msgs.append(f"💰 话费余额: {balance:.2f}元")
        msgs.append(f"💸 本月已消: {spent:.2f}元")
    else:
        msgs.append("⚠️ 话费数据获取失败")
        
    msgs.append("-" * 15)

    # 2. 流量
    if flow_data and flow_data.get('code') == '0000':
        resources = flow_data.get('resources', [])
        flow_res = [r for r in resources if r.get('type') == 'flow']
        
        total_left = 0
        total_all = 0
        pkg_details = []
        
        for res in flow_res:
            for item in res.get('details', []):
                t = float(item.get('total', 0))
                r = float(item.get('remain', 0))
                u = float(item.get('use', 0))
                total_all += t
                total_left += r
                
                # 仅在详细模式或大流量包显示
                if is_detailed or t > 2048: 
                    # 计算【使用】百分比
                    pct_used = (u / t * 100) if t > 0 else 0
                    bar = make_bar(pct_used, 8)
                    
                    name = item.get('feePolicyName') or item.get('addUpItemName', '未知包')
                    pkg_details.append(f"📦 {name}")
                    # 显示格式: [■■□□] 已用50% 余1GB
                    pkg_details.append(f"{bar} 用{pct_used:.1f}% 余{format_flow(r)}")

        # 总汇总
        all_pct_used = ((total_all - total_left) / total_all * 100) if total_all > 0 else 0
        all_bar = make_bar(all_pct_used, 10)
        
        msgs.append(f"📊 总流量: {format_flow(total_left)}")
        msgs.append(f"{all_bar} 用{all_pct_used:.1f}%")
        
        if pkg_details:
            msgs.append("") 
            msgs.extend(pkg_details)
            
    else:
        msgs.append("⚠️ 流量数据获取失败")
        
    return msgs

# --- 主程序 ---
def main():
    tokens, push_indices, is_detailed = get_env_config()
    
    if not tokens:
        print("❌ 未找到 chinaUnicomCookie 环境变量")
        return

    print(f"=== 联通余量(进度条反转版) | 账号数:{len(tokens)} ===")
    if push_indices:
        print(f"📝 推送策略: 只推第 {push_indices} 个账号")
    else:
        print(f"📝 推送策略: 全部推送")

    for i, token in enumerate(tokens):
        idx = i + 1
        print(f"\n━━━━━━━━ 正在处理第 {idx} 个账号 ━━━━━━━━")
        
        session, mobile = unicom_login(token)
        if not session:
            print(f"❌ 登录失败，跳过")
            continue
            
        print(f"✅ 登录成功: {mobile}")
        fee, flow = fetch_data(session)
        
        # 获取处理好的文本行
        lines = parse_report(fee, flow, is_detailed)
        
        # 【关键修改】无论是否推送，都在日志里打印详细内容
        content = "\n".join(lines)
        print(content) 
        
        # 判断推送逻辑
        should_push = False
        if not push_indices: 
            should_push = True
        elif idx in push_indices:
            should_push = True
            
        if should_push:
            title = f"联通: {mobile[-4:]}"
            print("   -> 📤 已加入推送队列")
            send(title, content)
        else:
            print("   -> 🚫 仅日志显示，不推送")
            
        time.sleep(1.5)

if __name__ == "__main__":
    main()