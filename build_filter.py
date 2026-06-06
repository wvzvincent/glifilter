#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_filter.py
----------------
抓取「中国大陆通常无法直连(走代理)」类别的上游 Surge 规则集,
解析并转换为 GL.iNet 路由器在线文本文件所支持的格式:
  - 域名 / 子域名 (来自 DOMAIN / DOMAIN-SUFFIX)
  - IPv4 与 CIDR    (来自 IP-CIDR)
去重后输出为单一文件 gl-inet-proxy-filter.txt。

GL.iNet「VPN 策略(基于目标域名或 IP)」支持: 域名 / 子域名 / IPv4 / CIDR。
GL.iNet「家长控制 规则集」仅支持: 域名 / 子域名 (不支持 IP)。
因此本脚本另外输出一个只含域名的文件 gl-inet-proxy-domains.txt,供家长控制使用。

注意: GL.iNet 不支持 DOMAIN-KEYWORD(关键字匹配),这类规则会被跳过并计数。
IPv6(IP-CIDR6)也不被支持,同样跳过。
"""

import sys
import time
import urllib.request
import urllib.error

# ---- 代理类别上游规则源(= 中国大陆无法直连的流量)----
# 仅收录配置中指向代理/分流策略的类别;走 DIRECT 的(China / ChinaMedia /
# BiliBili / Apple / Microsoft / Gamer)不包含在内。
SOURCES = [
    ("OpenAI",      "https://raw.githubusercontent.com/EAlyce/conf/refs/heads/main/Rule/OpenAI.list"),
    ("GitHub",      "https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/rule/Surge/GitHub/GitHub.list"),
    ("Telegram",    "https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/rule/Surge/Telegram/Telegram.list"),
    ("YouTube",     "https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/rule/Surge/YouTube/YouTube.list"),
    ("Netflix",     "https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/rule/Surge/Netflix/Netflix.list"),
    ("Disney",      "https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/rule/Surge/Disney/Disney.list"),
    ("Spotify",     "https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/rule/Surge/Spotify/Spotify.list"),
    ("TikTok",      "https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/rule/Surge/TikTok/TikTok.list"),
    ("GlobalMedia", "https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/rule/Surge/GlobalMedia/GlobalMedia_All_No_Resolve.list"),
    ("Proxy",       "https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/rule/Surge/Proxy/Proxy_All_No_Resolve.list"),
]

DOMAIN_OUT = "gl-inet-proxy-domains.txt"   # 仅域名(VPN 策略 + 家长控制通用)
FULL_OUT   = "gl-inet-proxy-filter.txt"    # 域名 + IPv4/CIDR(仅 VPN 策略)

UA = "Mozilla/5.0 (gl-inet-filter-builder)"


def fetch(url, retries=3, timeout=30):
    last_err = None
    for attempt in range(1, retries + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read().decode("utf-8", errors="ignore")
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as e:
            last_err = e
            print(f"  ! 第 {attempt} 次抓取失败: {e}", file=sys.stderr)
            time.sleep(2 * attempt)
    raise RuntimeError(f"抓取失败 {url}: {last_err}")


def parse(text, domains, ips, stats):
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or line.startswith(";") or line.startswith("//"):
            continue
        parts = [p.strip() for p in line.split(",")]
        rtype = parts[0].upper()

        if rtype in ("DOMAIN", "DOMAIN-SUFFIX"):
            if len(parts) >= 2 and parts[1]:
                domains.add(parts[1].lower().lstrip("."))
        elif rtype == "IP-CIDR":
            if len(parts) >= 2 and parts[1]:
                ips.add(parts[1])
        elif rtype == "DOMAIN-KEYWORD":
            stats["keyword_skipped"] += 1
        elif rtype in ("IP-CIDR6", "IP6-CIDR"):
            stats["ipv6_skipped"] += 1
        else:
            stats["other_skipped"] += 1


def main():
    domains = set()
    ips = set()
    stats = {"keyword_skipped": 0, "ipv6_skipped": 0, "other_skipped": 0}

    for name, url in SOURCES:
        print(f"抓取 {name} ...")
        text = fetch(url)
        before_d, before_i = len(domains), len(ips)
        parse(text, domains, ips, stats)
        print(f"  + 域名 {len(domains)-before_d}, IP {len(ips)-before_i}")

    domains_sorted = sorted(domains)
    ips_sorted = sorted(ips)

    header = (
        "# GL.iNet 域名/IP 过滤列表 — 自动生成,请勿手动编辑\n"
        f"# 生成时间(UTC): {time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime())}\n"
        "# 来源: Rabbit-Spec/Surge 配置中所有走代理(中国大陆无法直连)的类别\n"
        "# 每行一条规则\n"
    )

    with open(DOMAIN_OUT, "w", encoding="utf-8") as f:
        f.write(header)
        f.write(f"# 内容: 仅域名/子域名 ({len(domains_sorted)} 条) — 适用 VPN 策略与家长控制\n")
        for d in domains_sorted:
            f.write(d + "\n")

    with open(FULL_OUT, "w", encoding="utf-8") as f:
        f.write(header)
        f.write(f"# 内容: 域名 {len(domains_sorted)} 条 + IPv4/CIDR {len(ips_sorted)} 条 — 仅适用 VPN 策略\n")
        for d in domains_sorted:
            f.write(d + "\n")
        for ip in ips_sorted:
            f.write(ip + "\n")

    print("-" * 50)
    print(f"域名: {len(domains_sorted)}  IPv4/CIDR: {len(ips_sorted)}")
    print(f"跳过 关键字: {stats['keyword_skipped']}  IPv6: {stats['ipv6_skipped']}  其他: {stats['other_skipped']}")
    print(f"已写出: {DOMAIN_OUT}, {FULL_OUT}")


if __name__ == "__main__":
    main()
