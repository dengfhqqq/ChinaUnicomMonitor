# -*- coding: utf-8 -*-
"""
cron: 0 9,21 * * *
new Env('联通余量(Cookie版)');

【版本说明】
这是 [Cookie版] 脚本。
优点：不执行登录操作，极度安全，不易风控。
缺点：APP一旦切换账号，Cookie 立即失效，需重新抓取。
建议：适合多账号频繁切换、或已被 Code:3 风控的用户。

【环境变量】
export CHINA_UNICOM_COOKIES="手机号1&Cookie1
手机号2&Cookie2"
export UNICOM_PUSH_CFG="1"      (可选: 只推第1个号)
"""

import requests
import time
import os
import re

# 尝试导入 notify
try:
    from notify import send
except ImportError:
    def send(title, content):
        print(f"\n【推送预览】{title}\n{content}")

# --- 配置区 ---
ENV_COOKIES = 'CHINA_UNICOM_COOKIES'
ENV_PUSH_CFG = 'UNICOM_PUSH_CFG'
ENV_LEVEL = 'UNICOM_DETAIL_LEVEL'

API_FLOW = 'https://m.client.10010.com/servicequerybusiness/operationservice/queryOcsPackageFlowLeftContentRevisedInJune'
API_FEE = 'https://m.client.10010.com/servicequerybusiness/balancenew/accountBalancenew.htm'

# --- 工具函数 ---
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
    except: return f"[{'□'*length}]"

def get_env_config():
    cookies_env = os.getenv(ENV_COOKIES)
    accounts = []
    if cookies_env:
        items = cookies_env.split('\n') if '\n' in cookies_env else cookies_env.split('#')
        for item in items:
            item = item.strip()
            if not item: continue
            if '&' in item:
                parts = item.split('&', 1)
                accounts.append({'mobile': parts[0], 'cookie': parts[1]})
    
    push_cfg_str = os.getenv(ENV_PUSH_CFG, '')
    push_indices = []
    if push_cfg_str:
        try:
            push_indices = [int(x) for x in re.split(r'[,，]', push_cfg_str) if x.strip()]
        except: pass
    
    is_detailed = os.getenv(ENV_LEVEL, '0') == '1'
    return accounts, push_indices, is_detailed

def fetch_data(api, cookie):
    headers = {
        "Host": "m.client.10010.com",
        "Content-Type": "application/x-www-form-urlencoded",
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_1_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 unicom{version:iphone_c@12.0800};ltst;OSVersion/16.1.2",
        "Cookie": cookie,
        "Referer": "https://img.client.10010.com/"
    }
    try:
        resp = requests.post(api, headers=headers, data={}, timeout=15)
        if resp.status_code == 200:
            try: return resp.json()
            except: return None
    except: pass
    return None

def parse_account(fee_data, flow_data, is_detailed):
    msgs = []
    # 话费
    if fee_data and fee_data.get('code') == '0000':
        balance = float(fee_data.get('curntbalancecust', '0'))
        spent = float(fee_data.get('realfeecustnew', '0'))
        msgs.append(f"💰 话费余额: {balance:.2f}元")
        msgs.append(f"💸 本月已消: {spent:.2f}元")
    else:
        msgs.append("⚠️ 话费数据获取失败")
    msgs.append("-" * 15)

    # 流量
    if flow_data and flow_data.get('code') == '0000':
        resources = flow_data.get('resources', [])
        flow_res = [r for r in resources if r.get('type') == 'flow']
        total_left = 0
        total_all = 0
        pkg_lines = []
        for res in flow_res:
            for item in res.get('details', []):
                t = float(item.get('total', 0))
                r = float(item.get('remain', 0))
                u = float(item.get('use', 0))
                total_all += t
                total_left += r
                
                if t > 1024 or is_detailed:
                    pct_used = (u / t * 100) if t > 0 else 0
                    bar = make_bar(pct_used, 8)
                    name = item.get('feePolicyName') or item.get('addUpItemName', '未知包')
                    pkg_lines.append(f"📦 {name}")
                    pkg_lines.append(f"{bar} 用{pct_used:.1f}% 余{format_flow(r)}")

        all_pct_used = ((total_all - total_left) / total_all * 100) if total_all > 0 else 0
        all_bar = make_bar(all_pct_used, 10)
        msgs.append(f"📊 总流量: {format_flow(total_left)}")
        msgs.append(f"{all_bar} 用{all_pct_used:.1f}%")
        if pkg_lines:
            msgs.append("")
            msgs.extend(pkg_lines)
    else:
        msgs.append("⚠️ 流量数据获取异常")
    return msgs

def main():
    accounts, push_indices, is_detailed = get_env_config()
    if not accounts:
        print(f"❌ 未找到环境变量 {ENV_COOKIES}")
        return
        
    print(f"=== 联通(Cookie版) | 账号数:{len(accounts)} ===")
    for i, acc in enumerate(accounts):
        idx = i + 1
        mobile = acc['mobile']
        print(f"\n--- 处理第 {idx} 个账号: {mobile} ---")
        
        fee = fetch_data(API_FEE, acc['cookie'])
        flow = fetch_data(API_FLOW, acc['cookie'])
        lines = parse_account(fee, flow, is_detailed)
        content = "\n".join(lines).strip()
        print(content)
        
        should_push = idx in push_indices if push_indices else True
        if should_push:
            send(f"联通: {mobile[-4:]}", content)
        else:
            print("🚫 仅日志显示，不推送")
        time.sleep(1.5)

if __name__ == "__main__":
    main()