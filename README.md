# GL.iNet 分流过滤列表(自动更新)

把 [Rabbit-Spec/Surge](https://github.com/Rabbit-Spec/Surge) 配置中**所有走代理(即中国大陆通常无法直连)** 的类别,合并成一个 GL.iNet 路由器可直接读取的纯文本文件,并通过 GitHub Actions **每天自动更新**。

## 收录范围

走代理(已收录,= 无法直连):OpenAI、GitHub、Telegram、YouTube、Netflix、Disney+、Spotify、TikTok、GlobalMedia(海外流媒体)、通用 Proxy 列表。

走直连(未收录):China、ChinaMedia、BiliBili、Apple、Microsoft、Gamer —— 这些在大陆可直连,不属于"无法访问"。

## 生成的文件

| 文件 | 内容 | 适用功能 |
|---|---|---|
| `gl-inet-proxy-filter.txt` | 域名 + IPv4/CIDR | **VPN 策略**(基于目标域名或 IP) |
| `gl-inet-proxy-domains.txt` | 仅域名/子域名 | VPN 策略 **和** 家长控制规则集 |

> GL.iNet 的 VPN 策略支持 域名/子域名/IPv4/CIDR;家长控制规则集**只支持域名/子域名**,不支持 IP。所以家长控制请用 `gl-inet-proxy-domains.txt`。
>
> GL.iNet 不支持关键字匹配(DOMAIN-KEYWORD)和 IPv6,脚本会自动跳过这些规则。

---

## 一、用你自己的 GitHub 账号建立这个仓库

1. 登录 GitHub,点右上角 **+ → New repository**。
2. 仓库名随意(例如 `gl-inet-filter`),选择 **Public**(GL.iNet 要抓取 raw 链接,需公开),点 **Create repository**。
3. 把本文件夹里的三样东西上传到仓库根目录(可在网页点 **Add file → Upload files** 拖拽上传):
   - `build_filter.py`
   - `README.md`
   - `.github/workflows/update.yml`(`.github/workflows/` 目录结构要保留)

   > 网页上传无法直接创建带子目录的文件时,先上传 `build_filter.py`,再点 **Add file → Create new file**,在文件名框输入 `.github/workflows/update.yml`(输入 `/` 会自动建子目录),把 `update.yml` 内容粘贴进去保存。

## 二、开启 Actions 写入权限

1. 进入仓库 **Settings → Actions → General**。
2. 拉到底部 **Workflow permissions**,选 **Read and write permissions**,保存。
   (否则工作流无法把生成的文件提交回仓库。)

## 三、首次运行生成文件

1. 进入仓库 **Actions** 标签页,若提示启用 workflow 就点启用。
2. 左侧选 **Update GL.iNet filter list**,右侧点 **Run workflow → Run workflow**。
3. 等约 1 分钟,跑完后仓库根目录会出现 `gl-inet-proxy-filter.txt` 和 `gl-inet-proxy-domains.txt`。

之后每天 UTC 18:00(北京时间次日 02:00)会自动重跑更新;也可随时手动 Run workflow。

## 四、获取符合 GL.iNet 要求的 raw 链接

把网页地址里的用户名和仓库名替换成你的,得到 **raw 原始内容链接**(注意是 `raw.githubusercontent.com`,不是 `github.com`):

```
https://raw.githubusercontent.com/<你的用户名>/<仓库名>/main/gl-inet-proxy-filter.txt
```

例如用户名 `vincent`、仓库 `gl-inet-filter`:

```
https://raw.githubusercontent.com/vincent/gl-inet-filter/main/gl-inet-proxy-filter.txt
```

> 验证:把该链接贴到浏览器,如果直接显示一行行域名(没有网页框架),就说明格式正确,可被 GL.iNet 读取。
> 如果你的默认分支不是 `main`(老仓库可能是 `master`),把链接里的 `main` 换成 `master`。

## 五、在 GL.iNet 路由器中配置(固件 v4.7+)

**VPN 策略**:管理后台 → VPN → 对应的 VPN 客户端 → **代理模式 / Proxy Mode** → 选择"基于目标域名或 IP 的 VPN 策略" → 选择"使用在线文件 / Use an online file" → 粘贴上面的 raw 链接 → 应用。

**家长控制**:管理后台 → 应用 → 家长控制 → 添加规则集 → 选择在线文件 → 粘贴 `gl-inet-proxy-domains.txt` 的 raw 链接。

---

## 想自己增减类别?

编辑 `build_filter.py` 顶部的 `SOURCES` 列表,加一行 `("名字", "上游 .list 的 raw 链接")` 或删掉不需要的行,提交后工作流会自动按新列表重建。
