#!/usr/bin/env python3
"""Chinese OEM/OE web evidence miner.

This does not mark marketplace snippets as VIN-confirmed OE. It collects candidate
part numbers, URLs, titles and snippets so the catalogue can expand safely.
"""
import csv, json, os, re, time, urllib.parse, urllib.request, html
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'src' / 'data' / 'webEvidence.json'
CSVOUT = ROOT / 'src' / 'data' / 'webEvidence.csv'
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/122 Safari/537.36'

VIN = 'LGFP7AJJ7SA606343'
VEHICLE_ALIASES = [
    '东风御风', '东风御风 A100', '东风御风 V9', 'Dongfeng Yufeng', 'Dongfeng UVANE', 'DFAC Yufeng',
    '东风轻客 御风', '东风御风 P7AJJ'
]
PART_TERMS = {
    'Front bumper': ['前保险杠', '前杠', 'front bumper'],
    'Rear bumper': ['后保险杠', '后杠', 'rear bumper'],
    'Headlights': ['前大灯', '大灯总成', 'head lamp', 'headlight'],
    'Taillights': ['尾灯', '后尾灯', 'tail lamp'],
    'Side mirrors': ['后视镜', '倒车镜', 'side mirror'],
    'Doors': ['车门', '前门', '中门', '滑门', 'door assembly'],
    'Hood': ['发动机盖', '机盖', 'hood bonnet'],
    'Filters': ['机油滤清器', '空气滤清器', '柴油滤清器', '燃油滤清器', '空调滤清器', 'filter'],
    'Brake pads': ['刹车片', '制动块', 'brake pad'],
    'Brake discs': ['刹车盘', '制动盘', 'brake disc'],
    'Water pump': ['水泵', 'water pump'],
    'Radiator': ['散热器', '水箱', 'radiator'],
    'Thermostat': ['节温器', 'thermostat'],
    'Cylinder head': ['缸盖', '气缸盖', 'cylinder head'],
    'Pistons/rings': ['活塞环', '活塞', 'piston ring'],
    'Crankshaft/camshaft': ['曲轴', '凸轮轴', 'crankshaft', 'camshaft'],
    'EGR': ['EGR阀', '废气再循环阀', 'egr valve'],
    'DPF/DPR': ['颗粒捕集器', 'DPF', 'dpf filter'],
    'Clutch disc': ['离合器片', 'clutch disc'],
    'Pressure plate': ['离合器压盘', 'clutch pressure plate'],
    'Release bearing': ['分离轴承', 'release bearing'],
    'Clutch booster/master': ['离合器总泵', '离合器分泵', '离合器助力器', 'clutch booster'],
    'Hubs': ['轮毂轴承', '轮毂单元', 'hub bearing'],
    'Clutch rings': ['同步环', '离合器环', 'clutch ring'],
}
SOURCE_HINTS = ['site:1688.com', 'site:china.cn', 'site:made-in-china.com', 'site:alibaba.com', 'site:qipeiren.com', 'site:hc360.com', 'site:taobao.com', 'site:jd.com']
# Conservative patterns: common Chinese OE-like alnum strings with dash, and known family prefixes.
PN_PATTERNS = [
    re.compile(r'\b\d{5,7}-[A-Z0-9]{4,12}\b'),
    re.compile(r'\b[A-Z]{1,4}\d?[A-Z]?[-_]\d{5,8}[A-Z0-9-]*\b'),
    re.compile(r'\b[A-Z]{2}\d[A-Z]-\d{7,8}[A-Z]?\b'),
    re.compile(r'\b\d{5}[A-Z]\d{3,5}[A-Z]?\b'),
    re.compile(r'\b[A-Z]{2,5}\d{2,5}[A-Z0-9-]{2,}\b'),
]
BAD = {'HTTP','HTTPS','HTML','UTF','GBK','GB2312','DOCTYPE','BING','CACHE','JAVASCRIPT','CMAPI00048835'}
BAD_PREFIXES = ('INDEX-', 'ITEM-', 'MALL-', 'SHOP-', 'HTTP-', 'HTTPS-')

def fetch(q):
    # DuckDuckGo HTML currently exposes Chinese marketplace pages more reliably than Bing for these queries.
    url = 'https://html.duckduckgo.com/html/?q=' + urllib.parse.quote(q)
    req = urllib.request.Request(url, headers={'User-Agent': UA, 'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.6'})
    try:
        return urllib.request.urlopen(req, timeout=8).read().decode('utf-8', 'ignore')
    except Exception:
        return ''

def clean(s):
    s = re.sub(r'<script[\s\S]*?</script>|<style[\s\S]*?</style>', ' ', s, flags=re.I)
    s = re.sub(r'<[^>]+>', ' ', s)
    return html.unescape(re.sub(r'\s+', ' ', s)).strip()

def unwrap_ddg(url):
    url = html.unescape(url)
    if 'duckduckgo.com/l/' in url and 'uddg=' in url:
        return urllib.parse.unquote(urllib.parse.parse_qs(urllib.parse.urlparse(url).query).get('uddg', [''])[0]) or url
    if url.startswith('//duckduckgo.com/l/'):
        return unwrap_ddg('https:' + url)
    return url

def parse_results(page):
    results=[]
    blocks = re.findall(r'<div class="result[\s\S]*?</div>\s*</div>', page)
    if not blocks:
        blocks = page.split('result__a')
    for b in blocks[:12]:
        lm = re.search(r'class="result__a"[^>]*href="([^"]+)"[^>]*>([\s\S]*?)</a>', b)
        if not lm: continue
        url = unwrap_ddg(lm.group(1))
        title = clean(lm.group(2))
        sm = re.search(r'class="result__snippet"[^>]*>([\s\S]*?)</a>|class="result__snippet"[^>]*>([\s\S]*?)</div>', b)
        snippet = clean((sm.group(1) or sm.group(2)) if sm else clean(b)[:700])
        results.append((url,title,snippet))
    return results

def pns(text):
    found=set()
    for pat in PN_PATTERNS:
        for m in pat.findall(text.upper()):
            x=m.strip('.,;:()[]{}<>，。；：')
            if len(x) < 6 or x in BAD or x.startswith(BAD_PREFIXES): continue
            if re.search(r'\d',x) and not re.match(r'^[0-9]{4}$', x): found.add(x)
    return sorted(found)

def main():
    evidence=[]; seen=set(); qcount=0
    # VIN/family target searches first. Priority terms avoid the generic "OE query" pages that drown Chinese search results.
    queries=[]
    priority = [
        ('Front bumper','前保险杠 配件'), ('Rear bumper','后保险杠 配件'), ('Headlights','大灯总成 配件号'),
        ('Taillights','尾灯 总成 配件号'), ('Side mirrors','后视镜总成 配件号'), ('Doors','车门 总成 配件'),
        ('Hood','发动机盖 配件'), ('Brake pads','刹车片 3501013-K11001'), ('Brake discs','前刹车盘 K11001'),
        ('Water pump','水泵 配件号'), ('Radiator','散热器 水箱 配件号'), ('Thermostat','节温器 配件号'),
        ('Filters','机油 空气 柴油 滤清器 原厂号'), ('EGR','EGR阀 ZD25 ZD30'), ('DPF/DPR','DPF 颗粒捕集器'),
        ('Clutch disc','离合器片 1601130-K11001'), ('Pressure plate','离合器压盘 1601090-K11001'),
        ('Release bearing','分离轴承 配件号'), ('Clutch booster/master','离合器总泵 分泵 助力器'), ('Hubs','轮毂轴承 配件号')
    ]
    for alias in VEHICLE_ALIASES:
        for group, phrase in priority:
            queries.append((alias, group, f'{alias} {phrase}'))
            queries.append((alias, group, f'{alias} {phrase} 原厂'))
        # site-hinted high yield searches for core terms only
        for hint in SOURCE_HINTS[:5]:
            for group,term in [('Brake pads','刹车片'),('Clutch disc','离合器片'),('Headlights','大灯总成'),('Front bumper','前保险杠'),('Filters','滤清器')]:
                queries.append((alias, group, f'{hint} {alias} {term} 配件'))
    # Known brands from the current catalogue: broader enrichment seeds.
    brand_model_seeds = [
        ('BYD Seal U 宋PLUS', 'BYD SEAL U / SONG PLUS'), ('BYD Dolphin 海豚', 'BYD Dolphin'), ('BYD Atto3 元PLUS', 'BYD Atto3'),
        ('MG ZS 名爵ZS', 'MG ZS'), ('MG HS 名爵HS','MG HS'), ('吉利 Coolray 缤越','Geely Coolray'),
        ('奇瑞 Tiggo 7 瑞虎7','Chery Tiggo 7'), ('捷途 X70','Jetour X70'), ('长安 CS35','Changan CS35'),
        ('哈弗 H6', 'Haval H6'), ('江淮 T8', 'JAC T8'), ('福田 Auman 欧曼','Foton Auman'),
        ('中国重汽 HOWO', 'Sinotruk HOWO'), ('陕汽 Shacman X3000', 'Shacman X3000'), ('上汽大通 V80','Maxus V80')
    ]
    for zh, label in brand_model_seeds:
        for group,term in [('Front bumper','前保险杠'),('Headlights','大灯总成'),('Taillights','尾灯'),('Side mirrors','后视镜'),('Brake pads','刹车片'),('Brake discs','制动盘'),('Filters','滤清器'),('Clutch disc','离合器片'),('EGR','EGR阀'),('DPF/DPR','DPF')]:
            queries.append((label, group, f'{zh} {term} OE OEM 原厂 零件号'))
    # de-dup and cap for respectful run
    dedup=[]; qseen=set()
    for item in queries:
        if item[2] not in qseen:
            dedup.append(item); qseen.add(item[2])
    for vehicle, group, q in dedup[:70]:
        qcount += 1
        page=fetch(q)
        for url,title,snippet in parse_results(page):
            text=f'{title} {snippet}'
            nums=pns(text)
            key=(vehicle,group,url,title)
            if key in seen: continue
            seen.add(key)
            if nums or any(t in text for t in ['原厂','零件号','OE','OEM','适用','配件','总成']):
                evidence.append({
                    'vehicle': vehicle, 'partGroup': group, 'query': q, 'title': title, 'url': url,
                    'snippet': snippet[:900], 'candidateNumbers': nums,
                    'evidenceLevel': 'Candidate web evidence — requires EPC/VIN/supplier confirmation',
                    'collectedAt': datetime.now(timezone.utc).isoformat()
                })
        # polite throttle; DDG/Chinese result pages are slow, so keep this small for batch mining.
        time.sleep(0.03)
    # Preserve curated/manual evidence and merge fresh hits instead of overwriting better rows.
    existing=[]
    if OUT.exists():
        try:
            existing=json.loads(OUT.read_text(encoding='utf-8')).get('records', [])
        except Exception:
            existing=[]
    merged=[]; mseen=set()
    for r in existing + evidence:
        nums=[n for n in r.get('candidateNumbers', []) if not str(n).upper().startswith(BAD_PREFIXES)]
        r=dict(r); r['candidateNumbers']=nums
        key=(r.get('vehicle',''), r.get('partGroup',''), r.get('url',''), r.get('title',''))
        if key in mseen: continue
        mseen.add(key); merged.append(r)
    # Sort: candidates with numbers first, while keeping curated rows.
    merged.sort(key=lambda r: (len(r.get('candidateNumbers', [])) == 0, r.get('vehicle',''), r.get('partGroup','')))
    OUT.write_text(json.dumps({'generatedAt': datetime.now(timezone.utc).isoformat(), 'queryCount': qcount, 'records': merged}, ensure_ascii=False, indent=2), encoding='utf-8')
    fieldnames=['vehicle','partGroup','candidateNumbers','title','url','snippet','query','evidenceLevel','buyerNote','collectedAt']
    with CSVOUT.open('w', encoding='utf-8-sig', newline='') as f:
        w=csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
        w.writeheader()
        for r in merged:
            row=r.copy(); row['candidateNumbers']='; '.join(row.get('candidateNumbers', [])); w.writerow(row)
    print(json.dumps({'queries': qcount, 'evidence_records': len(merged), 'new_hits': len(evidence), 'records_with_candidate_numbers': sum(bool(r.get('candidateNumbers')) for r in merged), 'out': str(OUT)}, ensure_ascii=False, indent=2))

if __name__ == '__main__': main()
