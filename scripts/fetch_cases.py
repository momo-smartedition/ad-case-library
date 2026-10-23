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
SITE_URL = "https://34cc3ccbfb1f4c41a8bf6bf6425de755.app.workbuddy.host"

# RSS 多源（都是 git 可稳定抓取、带真实来源标签）
RSS_SOURCES = [
    {"name": "数英网", "url": "https://www.digitaling.com/rss"},
    {"name": "梅花网", "url": "https://www.meihua.info/feed"},
]
TOPYS_URL = "https://www.topys.cn"

# 奖项关键词（用于从 RSS/标题里识别是否获奖）
AWARD_KW = ["金投赏", "戛纳", "长城奖", "黄河奖", "艾菲", "One Show",
            "龙吟", "D&AD", "金瞳", "金鼠标", "Effie", "Cannes", "ROI"]


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
                "advertiser": "",
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
            om = re.search(r'property=["\']og:image["\'][^>]*content=["\']([^"\']+)', d, re.I)
            img = om.group(1) if om else None
            if img and not img_ok(img, ref=url):
                img = None
            dm = re.search(r'name=["\']description["\'][^>]+content=["\']([^"\']+)', d, re.I)
            summary = text_of(dm.group(1))[:200] if dm else "（详见原文）"
            out.append({
                "id": "topys-" + datetime.now().strftime("%Y%m%d") + "-" + str(len(out) + 1),
                "title": title,
                "advertiser": "",
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


def load_json(path):
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def merge(existing, new, dedup_by="all"):
    urls = {c.get("url") for c in existing}
    titles = {c.get("title") for c in existing}
    ids = {c.get("id") for c in existing}
    added = []
    for c in new:
        if dedup_by == "id":
            # 奖项库：每条独立保留（多条可能共用同一篇报道 URL）
            if c.get("id") and c["id"] in ids:
                continue
        else:
            if c.get("id") and c["id"] in ids:
                continue
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


def write_files(existing, repo_root):
    data_dir = os.path.join(repo_root, "data")
    os.makedirs(data_dir, exist_ok=True)
    with open(os.path.join(data_dir, "cases.json"), "w", encoding="utf-8") as f:
        json.dump(existing, f, ensure_ascii=False, indent=2)
    with open(os.path.join(data_dir, "cases.js"), "w", encoding="utf-8") as f:
        f.write("window.CASES = " + json.dumps(existing, ensure_ascii=False, indent=2) + ";\n")
    return len(existing)


def pushplus(added):
    if not PUSHPLUS_TOKEN:
        print("[PUSH] 未配置 PUSHPLUS_TOKEN，跳过推送")
        return
    if not added:
        print("[PUSH] 无新增案例，跳过推送")
        return
    award_added = [c for c in added if c.get("priority") or c.get("award")]
    others = [c for c in added if not (c.get("priority") or c.get("award"))]

    def block(c):
        return ('<p>🏆 <b>%s</b>（%s · %s）</p><p>%s</p>'
                '<p><a href="%s">看原文↗</a></p><hr/>'
                % (c["title"], c.get("source", ""), c.get("award", ""),
                   c.get("summary", ""), c["url"]))

    html = ("<h3>叮🔔 仅供乐呵·新案例来喽～</h3>"
            + (("<p>🏆 本期 <b>%d</b> 个奖项案例优先送达：</p>" % len(award_added)) if award_added else "")
            + "".join(block(c) for c in award_added)
            + (("".join(block(c) for c in others)) if others else "")
            + "<p>完整案例库 & 检索在这儿 👉 <a href='%s'>%s</a></p>" % (SITE_URL, SITE_URL))
    body = json.dumps({"token": PUSHPLUS_TOKEN,
                       "title": "仅供乐呵·新案例来喽（含%d个奖项案例）" % len(award_added),
                       "content": html}).encode("utf-8")
    req = subprocess.run(
        ["curl", "-s", "-X", "POST", "https://www.pushplus.plus/send",
         "-H", "Content-Type: application/json; charset=utf-8",
         "--data-binary", "@-"],
        input=body, capture_output=True, timeout=30)
    try:
        print("[PUSH] 推送结果:", req.stdout.decode("utf-8", "ignore"))
    except Exception as e:
        print("[PUSH] 推送失败:", repr(e))


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

    added = added_award + added_rss + added_topys
    print("[MERGE] 本次新增共 %d 条" % len(added))

    if DRY_RUN:
        print("[DRY_RUN] 不写文件、不推送。新增预览:")
        for c in added:
            print("  -", ("🏆 " if c.get("priority") else ""), c["title"], c.get("source"), c["url"])
        return
    if added:
        total = write_files(existing, repo_root)
        print("[WRITE] 写入完成，共 %d 条" % total)
        pushplus(added)
    else:
        print("[NOOP] 无新增，无需提交")


if __name__ == "__main__":
    main()
