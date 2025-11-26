# -*- coding: utf-8 -*-
"""
cron: 0 9,21 * * *
new Env('联通余量(Token版)');

【版本说明】
这是 [Token版] 脚本。
优点：Token 寿命长，理论上不受 APP 切号影响。
缺点：同一设备频繁抓取/运行可能触发 Code:3 风控。
建议：仅单账号，或多台设备分别抓包者使用。

【环境变量】
export chinaUnicomCookie="token1&token2"
export UNICOM_PUSH_CFG="1"      (可选: 只推第1个号)
export UNICOM_MONITOR_LIMIT="30" (可选: 免流监控阈值MB)
"""

import requests
import time
import os
import re
import json
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
# 【重要】更新后的登录接口
API_LOGIN = 'https://loginxhm.10010.com/mobileService/onLine.htm'

# --- 环境变量读取 ---
def get_env_config():
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
    
    push_cfg_str = os.getenv('UNICOM_PUSH_CFG', '')
    push_indices = []
    if push_cfg_str:
        try:
            push_indices = [int(x) for x in re.split(r'[,，]', push_cfg_str) if x.strip()]
        except: pass
            
    is_detailed = os.getenv('UNICOM_DETAIL_LEVEL', '0') == '1'
    monitor_limit_str = os.getenv('UNICOM_MONITOR_LIMIT', '')
    monitor_limit = float(monitor_limit_str) if monitor_limit_str else 0

    return token_list, push_indices, is_detailed, monitor_limit

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
        # 使用更新后的接口
        resp = session.post(API_LOGIN, headers=headers, data=data, timeout=15)
        res = resp.json()
        if res.get('code') == '0': 
            return session, res.get('desmobile', '未知号码')
        else:
            print(f"❌ 登录失败: {res.get('dsc') or res.get('msg')}")
    except Exception as e:
        print(f"❌ 登录异常: {e}")
    return None, None

def fetch_data(session):
    h = {"User-Agent": USER_AGENT, "Referer": "https://img.client.10010.com/"}
    fee, flow = None, None
    try:
        fee = session.post('https://m.client.10010.com/servicequerybusiness/balancenew/accountBalancenew.htm', headers=h, timeout=10).json()
    except: pass
    try:
        flow = session.post('https://m.client.10010.com/servicequerybusiness/operationservice/queryOcsPackageFlowLeftContentRevisedInJune', headers=h, timeout=10).json()
    except: pass
    return fee, flow

# --- 视觉工具 ---
def format_flow(size_mb):
    try:
        size_mb = float(size_mb)
        if size_mb >= 1024: return f"{size_mb / 1024:.2f}GB"
        return f"{size_mb:.2f}MB"
    except: return "0MB"

def make_bar(percent_used, length=10):
    try:
        percent = max(0, min(100, float(percent_used)))
        fill = int(length * percent / 100)
        return f"[{'■'*fill}{'□'*(length-fill)}]"
    except:
        return f"[{'□'*length}]"

# --- 数据解析 ---
def parse_report_and_check(fee_data, flow_data, is_detailed, monitor_limit):
    msgs = []
    alert_triggered = False 
    general_used_total = 0 
    
    if fee_data and fee_data.get('code') == '0000':
        balance = float(fee_data.get('curntbalancecust', '0'))
        msgs.append(f"💰 话费余额: {balance:.2f}元")
    else:
        msgs.append("⚠️ 话费数据获取失败")
    msgs.append("-" * 15)

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
                name = item.get('feePolicyName') or item.get('addUpItemName', '未知包')
                
                if monitor_limit > 0:
                    if any(k in name for k in ['通用', '国内', '结转']) and not any(k in name for k in ['定向', '专属', '视频', '游戏', '免流']):
                        general_used_total += u

                if is_detailed or t > 2048: 
                    pct_used = (u / t * 100) if t > 0 else 0
                    bar = make_bar(pct_used, 8)
                    pkg_details.append(f"📦 {name}")
                    pkg_details.append(f"{bar} 用{pct_used:.1f}% 余{format_flow(r)}")

        if monitor_limit > 0 and general_used_total > monitor_limit:
            alert_triggered = True
            msgs.insert(0, f"🚨 【免流跳点报警】 🚨")
            msgs.insert(1, f"通用流量已跑: {general_used_total:.2f}MB ‼️")
            msgs.insert(2, "-" * 15)

        all_pct_used = ((total_all - total_left) / total_all * 100) if total_all > 0 else 0
        all_bar = make_bar(all_pct_used, 10)
        msgs.append(f"📊 总流量: {format_flow(total_left)}")
        msgs.append(f"{all_bar} 用{all_pct_used:.1f}%")
        
        if pkg_details:
            msgs.append("") 
            msgs.extend(pkg_details)
    else:
        msgs.append("⚠️ 流量数据获取失败")
    return msgs, alert_triggered

# --- 主程序 ---
def main():
    tokens, push_indices, is_detailed, monitor_limit = get_env_config()
    if not tokens:
        print("❌ 未找到 chinaUnicomCookie 环境变量")
        return

    mode_str = f"监控模式({monitor_limit}MB)" if monitor_limit > 0 else "日报模式"
    print(f"=== 联通(Token版) | {mode_str} | 账号数:{len(tokens)} ===")

    for i, token in enumerate(tokens):
        idx = i + 1
        print(f"\n--- 处理第 {idx} 个账号 ---")
        session, mobile = unicom_login(token)
        if not session:
            print(f"❌ 登录失败")
            continue
            
        print(f"✅ 登录成功: {mobile}")
        fee, flow = fetch_data(session)
        lines, is_alert = parse_report_and_check(fee, flow, is_detailed, monitor_limit)
        content = "\n".join(lines)
        
        should_send = False
        user_allowed = idx in push_indices if push_indices else True

        if monitor_limit > 0:
            if is_alert:
                should_send = True
                title = f"🚨 联通报警: {mobile[-4:]}"
            else:
                print("✅ 流量正常，静默")
        else:
            if user_allowed:
                should_send = True
                title = f"联通: {mobile[-4:]}"
            else:
                print("🚫 白名单限制，不推送")

        print(content)
        if should_send: send(title, content)
        time.sleep(1.5)

if __name__ == "__main__":
    main()