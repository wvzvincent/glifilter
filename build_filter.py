#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_filter.py
----------------
抓取「中国大陆通常无法直连(走代理)」类别的上游 Surge 规则集,
解析并转换为 GL.iNet 路由器在线文本文件所支持的格式:
  - 域名 / 子域名 (来自 DOMAIN / DOMAIN-SUFFIX)
  - IPv4 与 CIDR    (来自 IP-CIDR)
严格校验、去重后输出为单一文件。

GL.iNet 导入校验的已知限制(本脚本据此过滤,避免「invalid line」报错):
  1) 不接受注释行 / 空行 —— 因此输出文件不含任何 # 注释或空行。
  2) 不接受以数字开头的域名(如 10.tt / 000webhost.com)—— 会被丢弃。
  3) 不支持关键字匹配(DOMAIN-KEYWORD)与 IPv6 —— 会被跳过。

输出:
  - gl-inet-proxy-filter.txt : 域名 + IPv4/CIDR (用于 VPN 策略)
  - gl-inet-proxy-domains.txt: 仅域名/子域名 (VPN 策略 + 家长控制通用)
"""

import re
import sys
import time
import urllib.request
import urllib.error

# ---- 代理类别上游规则源(= 中国大陆无法直连的流量)----
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

# ---- 额外手动添加的 IP/网段 ----
# 局域网 192.168.5.0/24「整段但排除 192.168.5.238」。
# 纯文本列表无排除语法,故将 /24 拆成若干 CIDR,覆盖 0-237 与 239-255(跳过 .238)。
EXTRA_IPS = [
    "192.168.5.0/25",     # .0   - .127
    "192.168.5.128/26",   # .128 - .191
    "192.168.5.192/27",   # .192 - .223
    "192.168.5.224/29",   # .224 - .231
    "192.168.5.232/30",   # .232 - .235
    "192.168.5.236/31",   # .236 - .237
    "192.168.5.239/32",   # .239
    "192.168.5.240/28",   # .240 - .255
]

UA = "Mozilla/5.0 (gl-inet-filter-builder)"

# 合法域名:整体以字母开头(GL.iNet 不接受数字开头),每个标签 1-63 字符,
# 末级 TLD 为纯字母 2+ 位。总长 <= 253。
DOMAIN_RE = re.compile(
    r"^(?=.{1,253}$)"
    r"[a-z]([a-z0-9-]{0,61}[a-z0-9])?"          # 首标签,字母开头
    r"(\.[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?)*"  # 中间标签
    r"\.[a-z]{2,}$"                              # TLD
)
_OCTET = r"(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)"
IPV4_RE = re.compile(r"^" + _OCTET + r"(\." + _OCTET + r"){3}$")
CIDR_RE = re.compile(r"^" + _OCTET + r"(\." + _OCTET + r"){3}/(3[0-2]|[12]?\d)$")


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
        if not line or line.startswith(("#", ";", "//")):
            continue
        parts = [p.strip() for p in line.split(",")]
        rtype = parts[0].upper()

        if rtype in ("DOMAIN", "DOMAIN-SUFFIX"):
            if len(parts) >= 2 and parts[1]:
                domains.add(parts[1].lower().strip("."))
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
    domains, ips = set(), set()
    stats = {"keyword_skipped": 0, "ipv6_skipped": 0, "other_skipped": 0}

    for name, url in SOURCES:
        print(f"抓取 {name} ...")
        text = fetch(url)
        bd, bi = len(domains), len(ips)
        parse(text, domains, ips, stats)
        print(f"  + 域名 {len(domains)-bd}, IP {len(ips)-bi}")

    # 加入手动指定的网段(局域网 192.168.5.0/24 排除 .238)
    ips.update(EXTRA_IPS)

    # ---- 严格校验过滤 ----
    valid_domains = sorted(d for d in domains if DOMAIN_RE.match(d))
    valid_ips = sorted(ip for ip in ips if IPV4_RE.match(ip) or CIDR_RE.match(ip))

    dropped_d = len(domains) - len(valid_domains)
    dropped_i = len(ips) - len(valid_ips)

    # 输出:纯条目,无注释、无空行(GL.iNet 要求)
    with open(DOMAIN_OUT, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(valid_domains) + "\n")

    with open(FULL_OUT, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(valid_domains + valid_ips) + "\n")

    print("-" * 50)
    print(f"有效域名: {len(valid_domains)}  (丢弃 {dropped_d}: 数字开头/非法格式)")
    print(f"有效 IPv4/CIDR: {len(valid_ips)}  (丢弃 {dropped_i})")
    print(f"解析时跳过 关键字: {stats['keyword_skipped']}  IPv6: {stats['ipv6_skipped']}  其他: {stats['other_skipped']}")
    print(f"已写出: {DOMAIN_OUT}, {FULL_OUT}")


if __name__ == "__main__":
    main()
