# 讀 content.md，產生 index.html 和每間學校的專用網址（/代號/，對照表在 NOTES.md）
# 用法：python3 build.py（或執行 ./preview.sh，會產生網頁並開預覽）
# index.html 和學校資料夾都是產生出來的，不要直接改；內容改 content.md，版面改 assets/style.css
import datetime
import html
import os
import re
import shutil

SITE = 'https://liaowh0218.github.io/'

# 學校專用網址的代號（網址是 /代號/）。代號對應哪間學校只記在 NOTES.md（不上傳），這裡不要寫校名
SCHOOLS = [
    'mj33',
    '2cpe',
    'k32z',
    'nb48',
    'arfc',
    'tkf6',
    'nzwv',
    '5y6g',
    'k6vd',
    'bpqw',
    'udy2',
    '9qkz',
]

# 各區塊認得的欄位（其他的行當作一般文字）
FIELDS = {
    'Profile': {'Name', 'Chinese name', 'Tagline', 'Photo', 'CV', 'Email', 'GitHub', 'LinkedIn'},
    'About': {'Title', 'Tags'},
    'Interests': {'Title'},
    'Projects': {'When', 'Image', 'Tags', 'Code', 'Report', 'Link', 'Featured'},
    'Experience': {'When'},
    'Education': {'When', 'Note'},
    'Settings': {'GoatCounter', 'MapMyVisitors'},
}

# 頁尾的小圖示（簡單的 SVG，顏色跟著文字）
ICONS = {
    'Email': '<svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="1.8"><rect x="3" y="5" width="18" height="14" rx="2"/><path d="M3 7l9 6 9-6"/></svg>',
    'GitHub': '<svg viewBox="0 0 24 24" width="22" height="22" fill="currentColor"><path d="M12 2a10 10 0 0 0-3.16 19.49c.5.09.68-.22.68-.48v-1.7c-2.78.6-3.37-1.34-3.37-1.34-.45-1.16-1.11-1.47-1.11-1.47-.91-.62.07-.61.07-.61 1 .07 1.53 1.03 1.53 1.03.89 1.53 2.34 1.09 2.91.83.09-.65.35-1.09.63-1.34-2.22-.25-4.56-1.11-4.56-4.95 0-1.09.39-1.98 1.03-2.68-.1-.25-.45-1.27.1-2.65 0 0 .84-.27 2.75 1.02a9.56 9.56 0 0 1 5 0c1.91-1.29 2.75-1.02 2.75-1.02.55 1.38.2 2.4.1 2.65.64.7 1.03 1.59 1.03 2.68 0 3.85-2.34 4.7-4.57 4.94.36.31.68.92.68 1.85v2.74c0 .27.18.58.69.48A10 10 0 0 0 12 2z"/></svg>',
    'LinkedIn': '<svg viewBox="0 0 24 24" width="22" height="22" fill="currentColor"><path d="M4.98 3.5a2.5 2.5 0 1 1 0 5 2.5 2.5 0 0 1 0-5zM3 9h4v12H3zM9 9h3.8v1.7h.05c.53-1 1.83-2.05 3.77-2.05 4.03 0 4.78 2.65 4.78 6.1V21h-4v-5.5c0-1.31-.02-3-1.83-3-1.83 0-2.11 1.43-2.11 2.9V21H9z"/></svg>',
    'CV': '<svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M14 3H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"/><path d="M14 3v6h6M8 13h8M8 17h5"/></svg>',
}

HERE = os.path.dirname(os.path.abspath(__file__))
GEN = 'generated-by-build.py'


# ---------- 讀 content.md ----------
def parse(path):
    sections = {}
    sec = item = None
    for raw in open(path, encoding='utf-8'):
        line = raw.rstrip('\n')
        if line.strip().startswith('//'):
            continue
        if line.startswith('# '):
            sec = {'fields': {}, 'paras': [], 'bullets': [], 'items': [], 'order': []}
            sections[line[2:].strip()] = sec
            item = None
            continue
        if sec is None:
            continue
        if line.startswith('## '):
            item = {'title': line[3:].strip(), 'fields': {}, 'paras': [], 'bullets': []}
            sec['items'].append(item)
            continue
        target = item if item is not None else sec
        name = [k for k, v in sections.items() if v is sec][0]
        text = line.strip()
        if not text:
            target['paras'].append('')          # 空行 = 換段
            continue
        m = re.match(r'^([A-Za-z][A-Za-z ]{0,24}):\s?(.*)$', text)
        if m and (m.group(1) in FIELDS.get(name, set()) or name == 'Skills'):
            target['fields'][m.group(1)] = m.group(2).strip()
            if name == 'Skills':
                sec['order'].append(m.group(1))
            continue
        if text.startswith('- '):
            target['bullets'].append(text[2:].strip())
            continue
        target['paras'].append(text)
    return sections


def inline(text):
    # 跳脫 HTML，再處理 **粗體** 和 [文字](網址)
    t = html.escape(text, quote=False)
    t = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', t)
    t = re.sub(r'\[([^\]]+)\]\(([^)\s]+)\)', r'<a href="\2">\1</a>', t)
    return t


def paragraphs(paras, cls=''):
    out, cur = [], []
    for p in paras + ['']:
        if p:
            cur.append(p)
        elif cur:
            out.append(f'<p{cls}>' + inline(' '.join(cur)) + '</p>')
            cur = []
    return '\n'.join(out)


def attr(s):
    return html.escape(s, quote=True)


def split_title(t):
    a, _, b = t.partition(' | ')
    return inline(a), inline(b)


# ---------- 產生 HTML ----------
# 頁面：(網址資料夾, 導覽列名稱)；首頁的資料夾是 ''
# 左上角：學校（校徽＋校名）｜ 系所（系徽＋系名）；系徽圖檔不存在時只顯示文字；連結都用英文版網站
SCHOOL = ('assets/logos/nthu.png', 'National Tsing Hua University', 'NTHU', 'https://nthu-en.site.nthu.edu.tw/')
DEPTS = [
    ('assets/logos/econ.png', 'Economics', 'https://econ.site.nthu.edu.tw/?Lang=en'),
    ('assets/logos/qf.png', 'Quantitative Finance', 'https://qf.site.nthu.edu.tw/')   # 計財系官網沒有英文版，連中文官網,
]

UPDATED = datetime.date.today().strftime('%b %-d, %Y')   # 頁尾的 Last updated：產生網頁的那一天

PAGES = [('', 'About'), ('projects', 'Projects'), ('experience', 'Experience')]


def head(c, title, base, extra=''):
    pf = c.get('Profile', {}).get('fields', {})
    name = pf.get('Name', '')
    t = name if not title else f'{title} · {name}'
    return ('<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
            '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
            + (f'<base href="{base}">\n' if base else '') + extra +
            f'<!-- {GEN}: 這個檔案由 build.py 產生，不要直接改；內容請改 content.md -->\n'
            f'<title>{attr(t)}</title>\n'
            f'<meta name="description" content="{attr(name + " — " + pf.get("Tagline", ""))}">\n'
            '<link rel="stylesheet" href="assets/style.css">\n<link rel="icon" href="assets/favicon.svg" type="image/svg+xml">\n'
            '</head>\n<body>\n')


def topbar(c, active):
    name = c.get('Profile', {}).get('fields', {}).get('Name', '')
    links = []
    for folder, label in PAGES:
        cls = ' class="active"' if folder == active else ''
        href = f'{folder}/' if folder else './'
        links.append(f'<a href="{href}"{cls}>{label}</a>')
    def badge(img, alt):
        return f'<img src="{attr(img)}" alt="">' if img and os.path.exists(os.path.join(HERE, img)) else ''
    img, full, short, url = SCHOOL
    school = (f'<a class="aff-school" href="{attr(url)}">{badge(img, full)}'
              f'<span class="long">{inline(full)}</span><span class="short">{inline(short)}</span></a>')
    depts = ' <span class="dot">·</span> '.join(
        f'<a href="{attr(u)}">{badge(i, n)}{inline(n)}</a>' for i, n, u in DEPTS)
    logos = [school, f'<span class="aff-depts">{depts}</span>']
    return ('<header class="topbar">\n'
            '  <div class="brand-logos">' + ''.join(logos) + '</div>\n'
            '  <nav>' + ''.join(links) + '</nav>\n</header>\n\n<main>\n')


def footer(c):
    pf = c.get('Profile', {}).get('fields', {})
    icons = []
    if pf.get('Email'):
        icons.append(f'<a href="mailto:{attr(pf["Email"])}" aria-label="Email" title="Email">{ICONS["Email"]}</a>')
    for k in ['GitHub', 'LinkedIn']:
        if pf.get(k):
            icons.append(f'<a href="{attr(pf[k])}" aria-label="{k}" title="{k}">{ICONS[k]}</a>')
    if pf.get('CV'):
        icons.append(f'<a href="{attr(pf["CV"])}" aria-label="CV" title="CV (PDF)">{ICONS["CV"]}</a>')
    out = ['</main>\n',
           f'<footer><p>© <span id="year">2026</span> {inline(pf.get("Name", ""))} · Last updated {UPDATED}</p><div class="social">' + ''.join(icons) + '</div></footer>',
           "<script>document.getElementById('year').textContent = new Date().getFullYear();</script>",
           # 直接用瀏覽器開本機檔案（file://）時，資料夾連結補上 index.html，才不會只看到檔案清單
           "<script>if (location.protocol === 'file:') document.querySelectorAll('a[href]').forEach(a => {"
           " if (a.href.startsWith('file:') && a.href.endsWith('/')) a.href += 'index.html'; });</script>"]
    gc = c.get('Settings', {}).get('fields', {}).get('GoatCounter', '').strip()
    if gc:
        out.append(f'<script data-goatcounter="https://{attr(gc)}.goatcounter.com/count" async src="//gc.zgo.at/count.js"></script>')
    out.append('</body>\n</html>\n')
    return '\n'.join(out)


def hero(c):
    pf = c.get('Profile', {}).get('fields', {})
    name, zh = pf.get('Name', ''), pf.get('Chinese name', '')
    out = ['<section class="hero">']
    if pf.get('Photo'):
        out.append(f'  <img class="avatar" src="{attr(pf["Photo"])}" alt="{attr(name)}">')
    out.append('  <div>')
    out.append(f'    <h1>{inline(name)}' + (f' <span class="zh">{inline(zh)}</span>' if zh else '') + '</h1>')
    if pf.get('Tagline'):
        out.append(f'    <p class="tagline">{inline(pf["Tagline"])}</p>')
    btns = []
    if pf.get('CV'):
        btns.append(f'<a class="btn primary" href="{attr(pf["CV"])}">{ICONS["CV"]}CV (PDF)</a>')
    for k in ['GitHub', 'LinkedIn']:
        if pf.get(k):
            btns.append(f'<a class="btn" href="{attr(pf[k])}">{ICONS[k]}{k}</a>')
    if pf.get('Email'):
        btns.append(f'<a class="btn" href="mailto:{attr(pf["Email"])}">{ICONS["Email"]}Email</a>')
    out.append('    <div class="buttons">' + ''.join(btns) + '</div>')
    out.append('  </div>\n</section>\n')
    return '\n'.join(out)


def about(c):
    if 'About' not in c:
        return ''
    a = c['About']
    title = a['fields'].get('Title', '').strip()
    text = paragraphs(a['paras'])
    if not text:
        return ''
    head = f'<h2>{inline(title)}</h2>\n' if title else ''
    return f'<section class="about">\n{head}{text}\n</section>\n'


def visitors(c):
    # 訪客地圖（MapMyVisitors），依淺色／深色模式換配色；代碼空著就不顯示
    code = c.get('Settings', {}).get('fields', {}).get('MapMyVisitors', '').strip()
    if not code:
        return ''
    return ('<section>\n<h2>Visitors</h2>\n<div class="visitors" id="map-container"></div>\n</section>\n'
            '<script>(function () {\n'
            "  var dark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;\n"
            "  var c = dark ? {cl: '82aee0', co: '11161d', ct: 'e6eaf0', dot: 'ffcc4d'}\n"
            "               : {cl: '2a5788', co: 'ffffff', ct: '1b2430', dot: 'f0a020'};\n"
            "  if (location.protocol === 'file:' || /^(localhost|127\\.)/.test(location.hostname)) {\n"
            "    document.getElementById('map-container').innerHTML = '<p class=\"meta\">Visitor map appears on the live site (not loaded in local preview, so your own previews are not counted).</p>';\n"
            "    return;\n"
            "  }\n"
            "  var s = document.createElement('script');\n"
            "  s.id = 'mapmyvisitors'; s.type = 'text/javascript';\n"
            f"  s.src = 'https://mapmyvisitors.com/map.js?d={attr(code)}&cl=' + c.cl + '&w=a&co=' + c.co + '&ct=' + c.ct + '&t=tt&cmn=' + c.dot + '&cmo=' + c.dot;\n"
            "  document.getElementById('map-container').appendChild(s);\n"
            '})();</script>\n')


def skills(c):
    if 'Skills' not in c or not c['Skills']['order']:
        return ''
    sk = c['Skills']
    rows = ''.join(f'  <dt>{inline(k)}</dt><dd>{inline(sk["fields"][k])}</dd>\n' for k in sk['order'])
    return f'<section>\n<h2>Skills</h2>\n<dl class="skills">\n{rows}</dl>\n</section>\n'


def card(it, image=True):
    f = it['fields']
    out = []
    out.append('<article class="card">')
    if image and f.get('Image'):
        out.append(f'  <img src="{attr(f["Image"])}" alt="">')
    out.append('  <div class="card-body">')
    out.append(f'    <h3>{inline(it["title"])}</h3>')
    if f.get('When'):
        out.append(f'    <p class="meta">{inline(f["When"])}</p>')
    out.append('    ' + paragraphs(it['paras']))
    tags = [t.strip() for t in f.get('Tags', '').split(',') if t.strip()]
    if tags:
        out.append('    <div class="tags">' + ''.join(f'<span>{inline(t)}</span>' for t in tags) + '</div>')
    links = [(k, f[k]) for k in ['Code', 'Report', 'Link'] if f.get(k)]
    if links:
        out.append('    <div class="links">' + ''.join(f'<a href="{attr(u)}">{k}</a>' for k, u in links) + '</div>')
    out.append('  </div>\n</article>')
    return '\n'.join(out)


def projects(c):
    out = ['<section class="page">\n<h1 class="page-title">Projects</h1>\n<div class="cards">']
    out += [card(it) for it in c.get('Projects', {}).get('items', [])]
    out.append('</div>\n</section>\n')
    return '\n'.join(out)


def interests(c):
    if 'Interests' not in c or not c['Interests']['bullets']:
        return ''
    it = c['Interests']
    title = it['fields'].get('Title', 'Interest Areas').strip()
    chips = ''.join(f'<span>{inline(x)}</span>' for x in it['bullets'])
    return f'<section>\n<h2>{inline(title)}</h2>\n<div class="chips">{chips}</div>\n</section>\n'


def selected(c):
    items = [it for it in c.get('Projects', {}).get('items', [])
             if it['fields'].get('Featured', '').strip().lower() in ('yes', 'y', 'true')]
    if not items:
        return ''
    out = ['<section>\n<h2>Selected Projects</h2>\n<div class="cards">']
    out += [card(it) for it in items]
    out.append('</div>\n<p class="more"><a href="projects/">All projects →</a></p>\n</section>\n')
    return '\n'.join(out)


def experience(c):
    # Education 在上、Work & Research 在下
    out = ['<section class="page">\n<h1 class="page-title">Experience</h1>']
    for sec_name, sub in [('Education', 'Education'), ('Experience', 'Work & Research')]:
        if sec_name not in c:
            continue
        out.append(f'<h3 class="sub">{sub}</h3>\n<div class="timeline">')
        for it in c[sec_name]['items']:
            f = it['fields']
            a, b = split_title(it['title'])
            out.append('<div class="item">')
            out.append(f'  <div class="when">{inline(f.get("When", ""))}</div>')
            out.append('  <div>')
            out.append(f'    <h3>{a}' + (f' <span class="at">· {b}</span>' if b else '') + '</h3>')
            if it['paras']:
                out.append('    ' + paragraphs(it['paras']))
            if f.get('Note'):
                out.append(f'    <p class="meta">{inline(f["Note"])}</p>')
            if it['bullets']:
                out.append('    <ul>' + ''.join(f'<li>{inline(x)}</li>' for x in it['bullets']) + '</ul>')
            out.append('  </div>\n</div>')
        out.append('</div>')
    out.append('</section>\n')
    return '\n'.join(out)


def write(folder, text):
    d = os.path.join(HERE, folder) if folder else HERE
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, 'index.html'), 'w', encoding='utf-8') as f:
        f.write(text)


def main():
    c = parse(os.path.join(HERE, 'content.md'))
    body = {
        '': hero(c) + about(c) + interests(c) + selected(c) + skills(c) + visitors(c),
        'projects': projects(c),
        'experience': experience(c),
    }
    titles = {'': '', 'projects': 'Projects', 'experience': 'Experience'}
    for folder, _ in PAGES:
        base = '../' if folder else ''
        write(folder, head(c, titles[folder], base) + topbar(c, folder) + body[folder] + footer(c))
    # 學校專用網址：首頁的副本，另外加 noindex、canonical
    extra = f'<meta name="robots" content="noindex">\n<link rel="canonical" href="{SITE}">\n'
    for slug in SCHOOLS:
        write(slug, head(c, '', '../', extra) + topbar(c, '') + body[''] + footer(c))
    # 清掉不在清單上、由這支程式產生的舊資料夾
    keep = set(SCHOOLS) | {f for f, _ in PAGES if f}
    for name in os.listdir(HERE):
        p = os.path.join(HERE, name, 'index.html')
        if name not in keep and os.path.isfile(p) and GEN in open(p, encoding='utf-8').read():
            shutil.rmtree(os.path.join(HERE, name))
    todo = sum(1 for line in open(os.path.join(HERE, 'content.md'), encoding='utf-8')
               if 'TODO' in line and not line.strip().startswith('//'))
    print('已更新首頁、Projects、Experience 和', len(SCHOOLS), '個學校網址')
    print('content.md 還有', todo, '行含 TODO' if todo else '行含 TODO，全部填完了')
    if not c.get('Settings', {}).get('fields', {}).get('GoatCounter', '').strip():
        print('提醒：Settings 的 GoatCounter 還沒填，目前不會統計訪客')
    if not c.get('Settings', {}).get('fields', {}).get('MapMyVisitors', '').strip():
        print('提醒：Settings 的 MapMyVisitors 還沒填，首頁不會顯示訪客地圖')


if __name__ == '__main__':
    main()
