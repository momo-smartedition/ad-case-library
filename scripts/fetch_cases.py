#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
仅供乐呵案例库 · 云端自动抓取+推送脚本
运行环境: GitHub Actions (Ubuntu) 或本地
主数据源: 数英网 RSS (稳定、含最新案例+图片)
流程: 抓 RSS -> 解析最新案例 -> 图片验证 -> 合并去重写 data/cases.json & cases.js -> PushPlus 推送
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
RSS_URL = "https://www.digitaling.com/rss"


def fetch(url, ref=None, timeout=25):
    cmd = ["curl", "-sL", "--compressed", "--max-time", str(timeout), "-A", UA]
    if ref:
        cmd += ["-e", ref]
    try:
        r = subprocess.run(cmd + [url], capture_output=True, timeout=timeout + 15)
        return r.stdout.decode("utf-8", "ignore")
    except Exception as e:
        print("  [FETCH_FAIL] %s -> %r" % (url, e))
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
    t = re.sub(r"\s*[-–—]\s*(数英网|SocialBeta|广告门).*$", "", t)
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


def collect(target=5, days=7):
    xml = fetch(RSS_URL)
    if not xml:
        print("[RSS] 抓取失败")
        return []
    items = parse_rss(xml)
    print("[RSS] 解析 %d 条" % len(items))
    cutoff = datetime.now() - timedelta(days=days)
    results = []
    for it in items:
        if "/articles/" in it["url"]:
            continue  # 只收案例项目，跳过观点文章
        if len(results) >= target:
            break
        if it["pub"] and it["pub"].replace(tzinfo=None) < cutoff:
            continue
        img = it["image"]
        if not img or not img_ok(img, ref=it["url"]):
            dh = fetch(it["url"], ref=RSS_URL)
            om = re.search(r'property=["\']og:image["\'][^>]*content=["\']([^"\']+)',
                           dh, re.I)
            img = om.group(1) if om else None
        if not img or not img_ok(img, ref=it["url"]):
            print("  跳过(无可用图):", it["title"])
            continue
        results.append({
            "id": "auto-" + datetime.now().strftime("%Y%m%d") + "-" + str(len(results) + 1),
            "title": it["title"],
            "advertiser": "",
            "agency": "",
            "campaignType": "最新案例",
            "summary": it["summary"] or "（详见原文）",
            "images": [img],
            "source": "数英网",
            "url": it["url"],
            "date": (it["pub"].strftime("%Y-%m-%d") if it["pub"]
                     else datetime.now().strftime("%Y-%m-%d")),
        })
    return results


def load_existing(path):
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def merge(existing, new):
    urls = {c.get("url") for c in existing}
    titles = {c.get("title") for c in existing}
    added = []
    for c in new:
        if c["url"] in urls or c["title"] in titles:
            continue
        existing.append(c)
        urls.add(c["url"])
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
    items = "".join(
        '<p>📌 <b>%s</b>（%s）</p><p>%s</p><p><a href="%s">看原文↗</a></p><hr/>'
        % (c["title"], c["source"], c["summary"], c["url"])
        for c in added
    )
    html = ("<h3>叮🔔 仅供乐呵案例库·今日新案例来喽～</h3>"
            "<p>最近数英网又整了不少好活，挑了几个有意思的给你：</p>"
            + items +
            "<p>完整案例库 & 检索在这儿 👉 <a href='%s'>%s</a></p>" % (SITE_URL, SITE_URL))
    body = json.dumps({"token": PUSHPLUS_TOKEN,
                       "title": "仅供乐呵案例库·新案例来喽",
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
    existing = load_existing(os.path.join(repo_root, "data", "cases.json"))
    print("[START] 现有案例 %d 条" % len(existing))
    new = collect(target=4)
    print("[COLLECT] 候选 %d 条" % len(new))
    existing, added = merge(existing, new)
    print("[MERGE] 新增 %d 条" % len(added))
    if DRY_RUN:
        print("[DRY_RUN] 不写文件、不推送。新增预览:")
        for c in added:
            print("  -", c["title"], c["url"], "图:", c["images"])
        return
    if added:
        total = write_files(existing, repo_root)
        print("[WRITE] 写入完成，共 %d 条" % total)
        pushplus(added)
    else:
        print("[NOOP] 无新增，无需提交")


if __name__ == "__main__":
    main()
