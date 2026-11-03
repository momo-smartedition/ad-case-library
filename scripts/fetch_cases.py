#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
仅供乐呵 · 云端自动抓取+推送脚本
运行环境: GitHub Actions (Ubuntu) 或本地
数据源（按优先级合并）:
  1) 奖项库 data/awards.json（策展真实获奖案例，priority 优先，带 award 字段）
  2) RSS 多源: 数英网 / 梅花网（带真实来源标签，跳过观点文，验图）
  3) TOPYS 列表页 HTML 抓取（创意/文案垂直，best-effort）
流程: 抓各源 -> 图片验证 -> 合并去重写 data/cases.json & cases.js -> PushPlus 推送（奖项案例置顶）
"""
import json
import os
import re
import sys
import subprocess
from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")
REPO = "momo-smartedition/ad-case-library"
DRY_RUN = os.environ.get("DRY_RUN", "") == "1"
PUSHPLUS_TOKEN = os.environ.get("PUSHPLUS_TOKEN", "")
SITE_URL = "https://6152ab6c7ba745fe8a11897d460d9b9f.app.workbuddy.host"

# RSS 多源（都是 git 可稳定抓取、带真实来源标签）
RSS_SOURCES = [
    {"name": "数英网", "url": "https://www.digitaling.com/rss"},
    {"name": "梅花网", "url": "https://www.meihua.info/feed"},
]
TOPYS_URL = "https://www.topys.cn"
SB_URL = "https://socialbeta.com/campaign"   # SocialBeta 每日品牌营销快讯（案例库）

# 奖项关键词（用于从 RSS/标题里识别是否获奖）
AWARD_KW = ["金投赏", "戛纳", "长城奖", "黄河奖", "艾菲", "One Show",
            "龙吟", "D&AD", "金瞳", "金鼠标", "Effie", "Cannes", "ROI"]

# 奖项等级权重（杰出 S / 知名 A / 入围 B）
TIER_W = {"S": 40, "A": 25, "B": 15}
# 来源权威度权重
SRC_W = {"金投赏": 10, "戛纳创意节": 10, "长城奖": 10, "TOPYS": 6,
         "数英网": 4, "梅花网": 3}
# 6 维评分默认中分（RSS/普通案例无人工分时给，每维 3）
DEFAULT_SCORE = 18

# ---------- 非案例内容黑名单（招聘/专访/活动预告/观点文，不是广告案例） ----------
JUNK_KW = [
    "招聘", "实习生", "校招", "社招", "招贤", "纳新", "招新", "求职", "简历", "岗位",
    "专访", "访谈", "对话", "独家对话", "面对面", "人物", "设计师介绍",
    "创意大会", "峰会", "论坛", "报名", "预告", "倒计时", "直播预约", "招募",
    "周报", "月报", "日报", "盘点", "榜单", "排行", "汇总", "精选集", "合辑",
    "投稿", "征稿", "课程", "训练营", "讲座", "沙龙", "工作坊",
    "MINDPARK", "Re:Think", "ReThink", "梦中情司", "开放日", "参观",
    "影像", "摄影集", "街头摄影", "平面设计遍布", "插画师", "字体设计",
    "观点", "观察", "深度解析", "行业观察", "编辑说", "专栏",
    # 站点头部/导航被误抓成案例（实测 TOPYS 首页标题混进来过）
    "创意内容平台", "OPEN YOUR MIND", "关于我们", "广告服务", "版权声明",
]

# ---------- 广告主（品牌）词库：用于自动补全 advertiser ----------
# 长词在前，避免「伊利」抢掉「金典(伊利)」这类短词误匹配
BRAND_LEXICON = [
    # 已有获奖案例品牌
    "名创优品 MINISO", "金典 SATINE", "金典(伊利)", "麦当劳（巴西）",
    "毛铺草本酒(劲牌)", "淘宝闪购 × 美的", "VIATRIS(晖致)", "乐高 LEGO",
    "品客 Pringles", "康恩贝肠炎宁", "Oura Ring", "Mikkeller",
    "太太乐", "恒源祥", "波司登", "百雀羚", "三顿半", "百事可乐",
    "国泰航空", "扬州旅游局", "深圳旅游局", "天猫超市", "天猫",
    "伊利", "京东", "美团", "乐事", "观夏", "金典", "OPPO",
    # 常见广告主（持续补充）
    "三星", "苹果", "华为", "小米", "vivo", "荣耀", "联想", "戴尔",
    "耐克", "阿迪达斯", "adidas", "NIKE", "安踏", "李宁", "斐乐", "新百伦", "NB",
    "优衣库", "无印良品", "ZARA", "H&M", "GAP", "UR", "海澜之家",
    "可口可乐", "雪碧", "芬达", "元气森林", "农夫山泉", "怡宝", "康师傅",
    "统一", "娃哈哈", "蒙牛", "光明", "君乐宝", "简爱", "认养一头牛",
    "麦当劳", "肯德基", "星巴克", "瑞幸", "喜茶", "奈雪", "蜜雪冰城",
    "霸王茶姬", "海底捞", "西贝", "老乡鸡", "白象", "汤达人",
    "沃尔沃", "宝马", "奔驰", "奥迪", "大众", "丰田", "本田", "日产",
    "比亚迪", "蔚来", "小鹏", "理想", "特斯拉", "五菱", "长安", "吉利",
    "奥利奥", "好丽友", "玛氏", "德芙", "士力架", "绿箭", "益达",
    "宝洁", "联合利华", "欧莱雅", "雅诗兰黛", "兰蔻", "SK-II", "资生堂",
    "珀莱雅", "薇诺娜", "花西子", "完美日记", "CeraVe", "Cetaphil", "理肤泉",
    "野兽派", "泡泡玛特", "名创优品", "晨光", "得力", "B站", "哔哩哔哩",
    "抖音", "快手", "小红书", "微博", "微信", "支付宝", "淘宝", "拼多多",
    "携程", "飞猪", "去哪儿", "同程", "马蜂窝", "滴滴", "高德", "百度地图",
    "腾讯", "阿里", "字节跳动", "网易", "京东健康", "平安", "招商银行",
    "中国银联", "工商银行", "建设银行", "支付宝", "云闪付",
    "Sour Patch Kids", "MINISO", "MINI", "MINI Cooper",
    "立白", "蓝月亮", "滴露", "舒肤佳", "海飞丝", "飘柔", "潘婷",
    "云南白药", "片仔癀", "同仁堂", "汤臣倍健", "Swisse", "善存",
    "中国移动", "中国电信", "中国联通", "中国邮政", "顺丰", "中通", "韵达",
    "宜家", "居然之家", "红星美凯龙", "林氏家居", "顾家家居", "慕思",
    # SocialBeta 高频（奢侈品/时尚/国际品牌）
    "CHANEL", "LV", "Louis Vuitton", "Balenciaga", "Dior", "Gucci", "Prada",
    "Hermès", "Hermes", "Cartier", "Tiffany", "Burberry", "Rolex", "Omega",
    "Miu Miu", "Loewe", "Fendi", "Versace", "Armani", "Coach", "Michael Kors",
    "Ray-Ban", "Swarovski", "Moncler", "Canada Goose", "The North Face",
    "Puma", "Under Armour", "New Balance", "ASICS", "Lululemon", "Arc'teryx",
    "Levi's", "Calvin Klein", "Tommy Hilfiger", "Ralph Lauren", "COS", "Massimo Dutti",
    # 中国家电/3C/新消费（SocialBeta 高频）
    "美的", "海尔", "格力", "TCL", "海信", "方太", "老板电器", "九阳", "苏泊尔",
    "追觅", "石头科技", "添可", "科沃斯", "大疆", "Insta360", "影石",
    "自然堂", "韩束", "谷雨", "夸迪", "可复美", "巨子生物", "润百颜",
    "泡泡玛特", "TOP TOY", "52TOYS", "卡游", "三只松鼠", "良品铺子", "周黑鸭",
    "蜜雪冰城", "古茗", "茶百道", "沪上阿姨", "霸王茶姬", "Manner", "Seesaw",
    "始祖鸟", "Salomon", "迪桑特", "KOLON SPORT", "骆驼", "探路者",
    "999感冒灵", "999皮炎平", "999", "三九", "华润三九", "江中",
]


def is_junk(title):
    """判断是否为非案例内容（招聘/专访/活动预告/观点文），True 则丢弃。"""
    t = (title or "")
    for kw in JUNK_KW:
        if kw.lower() in t.lower():
            return True
    return False


def guess_advertiser(title, summary=""):
    """从标题里猜广告主（品牌名），用于补全 advertiser 让品牌检索可用。
    ⚠️ 只用标题匹配词库：摘要里常有站点通用词（如「中国银联」「大众」出自页面描述），
    拿摘要匹配会张冠李戴。策略：① 词库匹配（长词优先，英文用词边界）
    ② 标题分隔符前提取（金典：xxx / 野兽派×xxx）。"""
    t = title or ""
    # ⓪ 联名格式「品牌A × B」：A 是主广告主（茉酸奶 × 自嘲熊 → 茉酸奶），
    #    必须先于词库，否则「…苹果狂欢夜」会被词库里的“苹果”抢走
    mx = re.match(r"^(.{2,15}?)\s*[×✕]\s*", t)
    if mx:
        cand = mx.group(1).strip()
        if (2 <= len(cand) <= 15 and not is_junk(cand)
                and re.fullmatch(r"[一-龥A-Za-z0-9&·\.\(\)（） ]{2,15}", cand)):
            return cand
    for b in sorted(BRAND_LEXICON, key=len, reverse=True):
        if re.fullmatch(r"[A-Za-z0-9&\.\+\- ]+", b):
            # 纯英文/数字品牌用词边界，避免 UR 命中 S-o-ur、MINI 命中 MINIMAL
            if re.search(r"(?<![A-Za-z0-9])" + re.escape(b) + r"(?![A-Za-z0-9])", t, re.I):
                return b
        elif b.lower() in t.lower():
            return b
    # ② 标题开头就是英文品牌（SocialBeta 常见格式：CHANEL 将冬日雪境… / LV 将经典…）
    m = re.match(r"^([A-Za-z][A-Za-z&\.'\s\-]{1,18}?)\s+[\u4e00-\u9fa5]", t)
    if m:
        cand = m.group(1).strip()
        if 2 <= len(cand) <= 20 and cand.lower() not in ("the", "a", "an"):
            return cand
    # ③ 分隔符前提取：「金典：邀请小孩姐…」→ 金典；「野兽派家居×瞿颖」→ 野兽派家居
    head = re.split(r"[：:｜|×✕\-—–]", t, maxsplit=1)[0].strip()
    if 2 <= len(head) <= 10 and not is_junk(head):
        # 纯中文/英文品牌片段才认，避免把整句当前缀
        if re.fullmatch(r"[一-龥A-Za-z0-9&·\.\(\)（） ]{2,10}", head):
            return head
    return ""



def fetch(url, ref=None, timeout=25, retries=3):
    cmd = ["curl", "-sL", "--compressed", "--max-time", str(timeout), "-A", UA]
    if ref:
        cmd += ["-e", ref]
    for i in range(retries):
        try:
            r = subprocess.run(cmd + [url], capture_output=True, timeout=timeout + 15)
            out = r.stdout.decode("utf-8", "ignore")
            if out.strip():
                return out
            print("  [FETCH_EMPTY] %s attempt %d" % (url, i + 1))
        except Exception as e:
            print("  [FETCH_FAIL] %s attempt %d -> %r" % (url, i + 1, e))
    return ""


def img_ok(url, ref=None, timeout=20):
    cmd = ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}",
           "--max-time", str(timeout), "-A", UA]
    if ref:
        cmd += ["-e", ref]
    try:
        r = subprocess.run(cmd + [url], capture_output=True, timeout=timeout + 10)
        return r.stdout.decode().strip() == "200"
    except Exception as e:
        print("  [IMG_FAIL] %s -> %r" % (url, e))
        return False


def clean_title(t):
    t = re.sub(r"^(项目频道|文章频道|案例频道)\s*[-–—]\s*", "", t.strip())
    t = re.sub(r"\s*[-–—]\s*(数英网|SocialBeta|广告门|梅花网).*$", "", t)
    return t.strip()


def text_of(html):
    h = re.sub(r"<[^>]+>", " ", html)
    h = re.sub(r"&[a-z]+;", " ", h)
    h = re.sub(r"\s+", " ", h).strip()
    return h


def parse_rss(xml):
    items = re.findall(r"<item>(.*?)</item>", xml, re.S)
    out = []
    for it in items:
        tm = re.search(r"<title>(?:<!\[CDATA\[)?\s*(.*?)\s*(?:\]\]>)?</title>", it, re.S)
        lm = re.search(r"<link>(?:<!\[CDATA\[)?\s*(.*?)\s*(?:\]\]>)?</link>", it, re.S)
        dm = re.search(r"<description>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</description>", it, re.S)
        pm = re.search(r"<pubDate>(.*?)</pubDate>", it, re.S)
        if not (tm and lm):
            continue
        title = clean_title(tm.group(1))
        link = lm.group(1).strip()
        desc = dm.group(1) if dm else ""
        summary = text_of(desc)[:200]
        img = None
        im = re.search(r'<img[^>]+src=["\']([^"\']+)', desc, re.S)
        if im:
            img = im.group(1)
        pub = None
        if pm:
            try:
                pub = parsedate_to_datetime(pm.group(1))
            except Exception:
                pub = None
        out.append({"title": title, "url": link, "summary": summary,
                    "image": img, "pub": pub})
    return out


def detect_award(text):
    t = (text or "").lower()
    for kw in AWARD_KW:
        if kw.lower() in t:
            return kw
    return ""


def collect_rss(target=5, days=7):
    """多源 RSS：遍历所有可用源，按真实来源打标，跳过观点文，验图。"""
    results = []
    cutoff = datetime.now() - timedelta(days=days)
    for src in RSS_SOURCES:
        xml = fetch(src["url"])
        if not xml or "<item>" not in xml:
            print("[RSS] 失败/无数据:", src["name"])
            continue
        items = parse_rss(xml)
        print("[RSS] %s 解析 %d 条" % (src["name"], len(items)))
        for it in items:
            if len(results) >= target:
                break
            if "/articles/" in it["url"]:
                continue  # 只收案例项目，跳过观点文章
            if is_junk(it["title"]):
                print("  跳过(非案例):", it["title"][:36])
                continue  # 招聘/专访/活动预告/观点文，不是广告案例
            if it["pub"] and it["pub"].replace(tzinfo=None) < cutoff:
                continue
            img = it["image"]
            if not img or not img_ok(img, ref=it["url"]):
                dh = fetch(it["url"], ref=src["url"])
                om = re.search(r'property=["\']og:image["\'][^>]*content=["\']([^"\']+)',
                               dh, re.I)
                img = om.group(1) if om else None
            if not img or not img_ok(img, ref=it["url"]):
                print("  跳过(无图):", it["title"])
                continue
            award = detect_award(it["title"] + " " + it["summary"])
            results.append({
                "id": "auto-" + datetime.now().strftime("%Y%m%d") + "-" + str(len(results) + 1),
                "title": it["title"],
                "advertiser": guess_advertiser(it["title"], it["summary"]),
                "agency": "",
                "campaignType": "最新案例",
                "summary": it["summary"] or "（详见原文）",
                "images": [img],
                "source": src["name"],
                "award": award,
                "priority": bool(award),
                "url": it["url"],
                "date": (it["pub"].strftime("%Y-%m-%d") if it["pub"]
                         else datetime.now().strftime("%Y-%m-%d")),
            })
    return results


def collect_topys(target=3):
    """TOPYS 列表页 HTML 抓取（创意/文案垂直，best-effort）。"""
    html = fetch(TOPYS_URL)
    if not html:
        print("[TOPYS] 列表页抓取失败")
        return []
    links = re.findall(r'href="(/article/\d+)"', html)
    seen, uniq = set(), []
    for l in links:
        if l not in seen:
            seen.add(l)
            uniq.append(l)
    out = []
    for l in uniq:
        if len(out) >= target:
            break
        url = "https://www.topys.cn" + l
        try:
            d = fetch(url, ref=TOPYS_URL)
            if not d:
                continue
            tm = re.search(r"<title>(?:<!\[CDATA\[)?\s*(.*?)\s*(?:\]\]>)?</title>", d, re.S)
            title = clean_title(tm.group(1)) if tm else ""
            if not title or len(title) < 4:
                continue
            # 标题末尾带「| TOPYS…」的是 TOPYS 自媒体栏目（观点/影像/专访），非广告案例
            if re.search(r"[|｜]\s*TOPYS", title):
                print("  [TOPYS] 跳过(自媒体栏目):", title[:36])
                continue
            if is_junk(title):
                print("  [TOPYS] 跳过(非案例):", title[:36])
                continue
            om = re.search(r'property=["\']og:image["\'][^>]*content=["\']([^"\']+)', d, re.I)
            img = om.group(1) if om else None
            if img and not img_ok(img, ref=url):
                img = None
            dm = re.search(r'name=["\']description["\'][^>]+content=["\']([^"\']+)', d, re.I)
            summary = text_of(dm.group(1))[:200] if dm else "（详见原文）"
            out.append({
                "id": "topys-" + datetime.now().strftime("%Y%m%d") + "-" + str(len(out) + 1),
                "title": title,
                "advertiser": guess_advertiser(title, summary),
                "agency": "",
                "campaignType": "创意精选",
                "summary": summary,
                "images": [img] if img else [],
                "source": "TOPYS",
                "award": "",
                "priority": False,
                "url": url,
                "date": datetime.now().strftime("%Y-%m-%d"),
            })
        except Exception as e:
            print("  [TOPYS_ITEM_FAIL] %s -> %r" % (url, e))
    print("[TOPYS] 采集 %d 条" % len(out))
    return out


def collect_socialbeta(target=4):
    """SocialBeta「每日品牌营销快讯」案例库（无可用 RSS，抓 /campaign 列表页）。
    卡片结构：<li><a class="pic" href="/campaign/ID"><img src="图"></a>
              <div class="tit"><a>标题</a></div><div class="meta">简介</div></li>
    ⚠️ 必须逐卡解析（按 <a class="pic" 切段），不能用跨卡 findall：
    旧正则的 .*? 会跨越卡片边界，把 A 卡的链接/图配上 B 卡的标题（实测错位事故）。
    最后再用详情页 <title> 校准一次，双保险。"""
    html = fetch(SB_URL)
    if not html or "hdtitle" not in html:
        print("[SB] 列表页抓取失败/结构变更")
        return []
    parts = re.split(r'<div class="hdtitle[^"]*">(.*?)</div>', html, flags=re.S)
    out, now = [], datetime.now()
    for i in range(1, len(parts) - 1, 2):
        header, body = parts[i], parts[i + 1]
        m = re.search(r'(\d{1,2})\s*月\s*(\d{1,2})\s*日', header)
        date = now.strftime("%Y-%m-%d")
        if m:
            try:
                date = datetime(now.year, int(m.group(1)), int(m.group(2))).strftime("%Y-%m-%d")
            except ValueError:
                pass
        # 逐卡切段：每段从本卡 <a class="pic" 开始，到下一卡为止 → 段内 tit/meta 一定属于本卡
        segs = re.split(r'<a class="pic"', body)
        for seg in segs[1:]:
            if len(out) >= target:
                break
            um = re.search(r'href="(https://socialbeta\.com/campaign/(\d+))"', seg)
            if not um:
                continue
            url, cid = um.group(1), um.group(2)
            im = re.search(r'<img src="([^"]+)"', seg)
            tm = re.search(r'<div class="tit"><a[^>]*>([^<]+)</a></div>', seg)
            mm = re.search(r'<div class="meta">\s*([^<]*)</div>', seg)
            title = clean_title(tm.group(1)) if tm else ""
            img = im.group(1) if im else ""
            if not title or len(title) < 4:
                continue
            if is_junk(title):
                print("  [SB] 跳过(非案例):", title[:30])
                continue
            # 详情页校准：真实标题/描述以详情页为准（防列表页结构变化）
            page = fetch(url, ref=SB_URL)
            pt = re.search(r"<title>(.*?)</title>", page, re.S)
            if pt:
                real = clean_title(pt.group(1)).replace("｜SocialBeta", "").strip()
                if real and len(real) >= 4 and not is_junk(real):
                    if real != title:
                        print("  [SB] 校准标题:", title[:20], "->", real[:30])
                    title = real
            pd = re.search(r'name=["\']description["\'][^>]+content=["\']([^"\']+)', page, re.I)
            summary = text_of(pd.group(1))[:200] if pd else (text_of(mm.group(1))[:200] if mm and mm.group(1) else "（详见原文）")
            if not img or not img_ok(img, ref=url):
                # 列表图失效则从详情页 og:image / 正文首图补
                img = find_image_for_url(url) or ""
            if not img:
                print("  [SB] 跳过(无图):", title[:26])
                continue
            out.append({
                "id": "sb-" + cid,
                "title": title,
                "advertiser": guess_advertiser(title, summary),
                "agency": "",
                "campaignType": "每日快讯",
                "summary": summary,
                "images": [img],
                "source": "SocialBeta",
                "award": detect_award(title + " " + summary),
                "priority": False,
                "url": url,
                "date": date,
            })
    print("[SB] 采集 %d 条" % len(out))
    return out


def load_json(path):
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def save_json(path, data):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False


def find_image_for_url(url):
    """尽力为某 URL 找到一张可加载的正文图（og:image → data-src → <img>）。
    用于奖项案例补图的安全网：策展库里某奖项案例忘了填图时，推送前自动补。"""
    if not url:
        return None
    h = fetch(url)
    if not h:
        return None
    m = re.search(r'property=["\']og:image["\'][^>]*content=["\']([^"\']+)', h, re.I)
    if m and img_ok(m.group(1)):
        return m.group(1)
    for m in re.finditer(r'data-(?:src|original)=["\']([^"\']+)', h, re.I):
        if img_ok(m.group(1)):
            return m.group(1)
    for m in re.finditer(r'<img[^>]+src=["\']([^"\']+)', h, re.I):
        s = m.group(1)
        if any(x in s.lower() for x in ("logo", "icon", "avatar", "qrcode", "1x1", "pixel", "nopic", "header_default")):
            continue
        if img_ok(s):
            return s
    return None


def merge(existing, new, dedup_by="all"):
    urls = {c.get("url") for c in existing}
    titles = {c.get("title") for c in existing}
    ids = {c.get("id") for c in existing}
    index = {c.get("id"): i for i, c in enumerate(existing) if c.get("id")}
    added = []
    for c in new:
        if c.get("id") and c["id"] in ids:
            if dedup_by == "id":
                # 奖项库：用最新策展数据刷新字段（tier/scores/award 等），不重复添加
                ex = existing[index[c["id"]]]
                for k in ("award_tier", "scores", "award", "title", "summary",
                          "advertiser", "agency", "campaignType", "url", "date"):
                    if c.get(k) is not None:
                        ex[k] = c[k]
                if c.get("images"):
                    ex["images"] = c["images"]
                continue
            else:
                continue
        else:
            if c.get("url") and c["url"] in urls:
                continue
            if c.get("title") and c["title"] in titles:
                continue
        existing.append(c)
        if c.get("id"):
            ids.add(c["id"])
        if c.get("url"):
            urls.add(c["url"])
        if c.get("title"):
            titles.add(c["title"])
        added.append(c)
    return existing, added


def compute_score(c):
    """优质分 = 奖项等级权重 + 6维评分和 + 有图 + 来源权威度。
    奖项案例天然高分置顶；无人工评分的 RSS/普通案例给默认中分。"""
    tier = c.get("award_tier")
    tier_w = TIER_W.get(tier, 25 if c.get("award") else 0)
    sc = c.get("scores")
    sum_sc = sum(sc.values()) if sc else DEFAULT_SCORE
    img_w = 5 if (c.get("images") and c["images"] and c["images"][0]) else 0
    src_w = SRC_W.get(c.get("source"), 2)
    return tier_w + sum_sc + img_w + src_w


def write_files(existing, repo_root):
    data_dir = os.path.join(repo_root, "data")
    os.makedirs(data_dir, exist_ok=True)
    with open(os.path.join(data_dir, "cases.json"), "w", encoding="utf-8") as f:
        json.dump(existing, f, ensure_ascii=False, indent=2)
    with open(os.path.join(data_dir, "cases.js"), "w", encoding="utf-8") as f:
        f.write("window.CASES = " + json.dumps(existing, ensure_ascii=False, indent=2) + ";\n")
    return len(existing)


def pushplus(items):
    if not PUSHPLUS_TOKEN:
        print("[PUSH] 未配置 PUSHPLUS_TOKEN，跳过推送")
        return
    if not items:
        print("[PUSH] 无推送内容，跳过")
        return
    award_items = [c for c in items if c.get("priority") or c.get("award")]
    other_items = [c for c in items if not (c.get("priority") or c.get("award"))]

    def block(c):
        tier = c.get("award_tier")
        tag = ("🏆%s " % tier) if tier else ""
        return ('<p>%s<b>%s</b>（%s · %s · 评分%s）</p><p>%s</p>'
                '<p><a href="%s">看原文↗</a></p><hr/>'
                % (tag, c["title"], c.get("source", ""), c.get("award", "") or "最新案例",
                   c.get("score", ""), c.get("summary", ""), c["url"]))

    html = ("<h3>叮🔔 仅供乐呵·精选案例来喽～</h3>"
            + (("<p>🏆 本期精选 <b>%d</b> 个奖项案例：</p>" % len(award_items)) if award_items else "")
            + "".join(block(c) for c in award_items)
            + (("<p>⭐ 本期 <b>%d</b> 个高评分最新案例：</p>" % len(other_items)) if other_items else "")
            + "".join(block(c) for c in other_items)
            + "<p>完整案例库 & 检索在这儿 👉 <a href='%s'>%s</a></p>" % (SITE_URL, SITE_URL))
    title = "仅供乐呵·精选（%d奖项+%d高分）" % (len(award_items), len(other_items))
    body = json.dumps({"token": PUSHPLUS_TOKEN, "title": title, "content": html}).encode("utf-8")
    req = subprocess.run(
        ["curl", "-s", "-X", "POST", "https://www.pushplus.plus/send",
         "-H", "Content-Type: application/json; charset=utf-8",
         "--data-binary", "@-"],
        input=body, capture_output=True, timeout=30)
    try:
        print("[PUSH] 推送结果:", req.stdout.decode("utf-8", "ignore"))
    except Exception as e:
        print("[PUSH] 推送失败:", repr(e))


def select_push_items(existing, added, repo_root):
    """每期必推：**2 个最新案例放前面** + **1 个奖项案例压轴**（轮转，避免期期重复）。
    最新案例优先取本期新增，不足 2 条时从全库按日期补齐。"""
    state_path = os.path.join(repo_root, "data", "push_state.json")
    state = load_json(state_path)
    if not isinstance(state, dict):
        state = {}

    def is_curated_award(c):
        # 只认策展奖项库（priority），SocialBeta/数英快讯里带「戛纳」字样不算
        return bool(c.get("priority"))

    # 1) 两个最新案例：优先本期新增，不足从全库按日期补
    fresh = [c for c in added if not is_curated_award(c)]
    fresh.sort(key=lambda c: (c.get("date", ""), c.get("score", 0)), reverse=True)
    latest = fresh[:2]
    if len(latest) < 2:
        picked = {c.get("id") for c in latest}
        pool = [c for c in existing
                if not is_curated_award(c) and c.get("id") not in picked]
        pool.sort(key=lambda c: (c.get("date", ""), c.get("score", 0)), reverse=True)
        latest += pool[:2 - len(latest)]

    # 2) 一个奖项案例（轮转）
    awards = [c for c in existing if is_curated_award(c)]
    awards.sort(key=lambda c: (c.get("score", 0), c.get("date", "")), reverse=True)
    award_case = None
    if awards:
        idx = int(state.get("award_idx", 0)) % len(awards)
        award_case = awards[idx]
        state["award_idx"] = (idx + 1) % len(awards)

    save_json(state_path, state)
    # 最新两条在前，奖项案例压轴
    return latest + ([award_case] if award_case else [])


def main():
    repo_root = (os.environ.get("GITHUB_WORKSPACE")
                 or os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    existing = load_json(os.path.join(repo_root, "data", "cases.json"))
    print("[START] 现有案例 %d 条" % len(existing))

    # 1) 奖项库（优先，按 id 去重，每条独立保留）
    curated = load_json(os.path.join(repo_root, "data", "awards.json"))
    existing, added_award = merge(existing, curated, dedup_by="id")
    print("[AWARD] 奖项库新增 %d 条" % len(added_award))

    # 2) RSS 多源
    new_rss = collect_rss(target=5)
    existing, added_rss = merge(existing, new_rss)
    print("[RSS] 新增 %d 条" % len(added_rss))

    # 3) TOPYS 创意垂直
    new_topys = collect_topys(target=3)
    existing, added_topys = merge(existing, new_topys)
    print("[TOPYS] 新增 %d 条" % len(added_topys))

    # 4) SocialBeta 每日品牌营销快讯（案例库）
    new_sb = collect_socialbeta(target=4)
    existing, added_sb = merge(existing, new_sb)
    print("[SB] 新增 %d 条" % len(added_sb))

    added = added_award + added_rss + added_topys + added_sb
    print("[MERGE] 本次新增共 %d 条" % len(added))

    # 入库时间 added_at：本期新增标今天，历史条目用发布日期兜底
    # → 保证「本次更新抓到的案例永远排最前面」，哪怕它发布日期较早
    today = datetime.now().strftime("%Y-%m-%d")
    for c in added:
        c["added_at"] = today
    for c in existing:
        if not c.get("added_at"):
            c["added_at"] = c.get("date", "") or today

    # 计算优质分（仍保留用于展示分数徽章）
    for c in existing:
        c["score"] = compute_score(c)
    # 排序：先按「更新时间」倒序（今天新更新的在最前），再按发布日期，最后比分数
    existing.sort(key=lambda c: (c.get("added_at", ""), c.get("date", ""), c.get("score", 0)),
                  reverse=True)
    added = sorted(added, key=lambda c: (c.get("added_at", ""), c.get("date", ""), c.get("score", 0)),
                   reverse=True)

    # 推送前强制补图：奖项案例务必带真图（策展库漏填时自动从来源页补）
    award_imgs_changed = False
    for c in existing:
        if (c.get("priority") or c.get("award")) and not (c.get("images") and c["images"]):
            img = find_image_for_url(c.get("url", ""))
            if img:
                c["images"] = [img]
                for k in curated:
                    if k.get("id") == c.get("id"):
                        k["images"] = [img]
                award_imgs_changed = True
                print("[IMG] 奖项案例补图:", c.get("id"), img[:60])
    if award_imgs_changed:
        save_json(os.path.join(repo_root, "data", "awards.json"), curated)
        print("[IMG] 已把补图写回 awards.json")

    if DRY_RUN:
        print("[DRY_RUN] 不写文件、不推送。新增预览:")
        for c in added:
            print("  -", ("🏆 " if c.get("priority") else ""), c["title"], c.get("source"), "score=", c.get("score"), c["url"])
        return
    # 始终写文件：固化评分/排序/奖项等级字段（无新增时仅落盘，不推送）
    total = write_files(existing, repo_root)
    print("[WRITE] 写入完成，共 %d 条" % total)
    # 每期必推：1 奖项案例 + 2 个近期最高分优秀案例
    # 无新增时也照发精选（奖项轮转 + 高分轮转），保证 momo 每 2 天都能收到推送，不再静默
    items = select_push_items(existing, added, repo_root)
    tag = ("本期新增 %d 条" % len(added)) if added else "无新增·精选回顾"
    print("[PUSH] 本期推送 %d 条（%s）" % (len(items), tag))
    pushplus(items)


if __name__ == "__main__":
    main()
