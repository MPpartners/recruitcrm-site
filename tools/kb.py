#!/usr/bin/env python3
"""
База знаний /baza-znaniy/ из руководства пользователя CRM (MPpartners/recruit-crm, docs/user-guide.md).

    python3 tools/kb.py ../recruit-crm/docs/user-guide.md

Берёт шапку, стили и подвал из index.html, переписывает baza-znaniy/index.html. Перед публикацией из текста
убирается то, чему не место на открытой странице (PUBLIC_EDITS ниже); если строка в руководстве поменялась и правка
не нашлась, скрипт остановится — поправьте PUBLIC_EDITS.
"""
import html, re, sys, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent

# (что в руководстве, чем заменить). Адрес сервисного аккаунта, пороги блокировки входа и служебное — не наружу.
PUBLIC_EDITS = [
    ("кому открыть таблицу (\n  `crm-sync@recruit-crm-510500.iam.gserviceaccount.com` как «Редактор»)",
     "кому открыть таблицу (адрес сервисного аккаунта CRM — там же, доступ «Редактор»)"),
    ("После 10 неверных паролей подряд для одного email вход по нему закрыт на 15 минут (с любого устройства); с одного\n"
     "адреса сети — после 30 неверных попыток по любым email. Неверный пароль администратора сервиса записывается в его\n"
     "журнал.",
     "После нескольких неверных паролей подряд вход временно закрывается — подождите или попросите администратора сменить пароль."),
]


def inline(t: str) -> str:
    t = html.escape(t, quote=False)
    t = re.sub(r"`([^`]+)`", r"<code>\1</code>", t)
    t = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", t)
    return t


def slug(title: str, used: set) -> str:
    tr = dict(zip("абвгдеёжзийклмнопрстуфхцчшщъыьэюя", ["a","b","v","g","d","e","e","zh","z","i","y","k","l","m","n","o","p","r","s","t","u","f","h","ts","ch","sh","sch","","y","","e","yu","ya"]))
    s = "".join(tr.get(c, c) for c in title.lower())
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-") or "razdel"
    base, n = s, 2
    while s in used:
        s, n = f"{base}-{n}", n + 1
    used.add(s)
    return s


def render(md: str):
    """The guide's subset of Markdown: ## / ### headings, paragraphs, «- » and «1. » lists nested by two spaces."""
    out, toc, used = [], [], set()
    lines = md.split("\n")
    i = 0
    stack = []  # open lists: (indent, tag)

    def close_lists(to_indent=-1):
        while stack and stack[-1][0] > to_indent:
            out.append(f"</li></{stack.pop()[1]}>")

    para = []

    def flush_para():
        if para:
            out.append(f"<p>{inline(' '.join(para))}</p>")
            para.clear()

    section_open = False
    while i < len(lines):
        line = lines[i].rstrip()
        m_h = re.match(r"^(#{1,3}) (.+)$", line)
        m_li = re.match(r"^( *)(- |\d+\. )(.*)$", line)
        if m_h:
            flush_para(); close_lists()
            level, title = len(m_h.group(1)), m_h.group(2).strip()
            if level == 1:
                i += 1; continue
            sid = slug(title, used)
            if level == 2:
                if section_open: out.append("</section>")
                out.append(f'<section class="kb-sec" id="{sid}"><h2>{inline(title)}</h2>')
                section_open = True
                toc.append((sid, title, []))
            else:
                out.append(f'<h3 id="{sid}">{inline(title)}</h3>')
                if toc: toc[-1][2].append((sid, title))
        elif m_li:
            flush_para()
            indent, marker, text = len(m_li.group(1)), m_li.group(2), m_li.group(3)
            tag = "ol" if marker[0].isdigit() else "ul"
            if stack and stack[-1][0] == indent:
                out.append("</li><li>")
            elif stack and stack[-1][0] > indent:
                close_lists(indent)
                out.append("</li><li>")
            else:
                out.append(f"<{tag}><li>")
                stack.append((indent, tag))
            # continuation lines: indented more than the marker, not a new item
            j = i + 1
            while j < len(lines) and lines[j].strip() and not re.match(r"^ *(- |\d+\. |#)", lines[j]) and lines[j].startswith(" " * (indent + 2)):
                text += " " + lines[j].strip(); j += 1
            out.append(inline(text))
            i = j; continue
        elif not line.strip():
            flush_para()
            # a blank line ends a list only if the next line is not part of it
            nxt = lines[i + 1] if i + 1 < len(lines) else ""
            if not re.match(r"^ *(- |\d+\. )", nxt): close_lists()
        else:
            if stack and line.startswith("  "):
                out.append(" " + inline(line.strip()))
            else:
                close_lists(); para.append(line.strip())
        i += 1
    flush_para(); close_lists()
    if section_open: out.append("</section>")
    return "\n".join(out), toc


BASES_INTRO = (
    "Работа в системе начинается с загрузки базы для обзвона. Сейчас доступны два способа загрузки: из таблицы и из "
    "изображений — скриншотов экрана, на которых есть номер телефона кандидата. По согласованию дополнительной разработки "
    "можно подключить и другие каналы загрузки базы: интеграции с Авито, hh.ru, VK и другими."
)

IMAGES_MD = """Скриншоты карточек кандидатов (например, из чатов VK Работы и похожих сервисов) CRM читает сама: находит имя,
телефон, город, возраст и вакансию. Загружать изображения может администратор и рекрутер с правом «Загружать базы».
Распознавание включается для колл-центра администратором сервиса.

### С компьютера

1. «Базы» → «Импорт базы», выберите дату и название базы.
2. Перетащите скриншоты в поле «Или скриншоты карточек кандидатов» — до 300 за раз. Браузер сам уменьшит их перед отправкой.
3. CRM распознает каждый скриншот и покажет таблицу: строку можно поправить. Неуверенно прочитанные и скриншоты без
   телефона отмечены «проверить», галочка у них снята — посмотрите и включите нужные.
4. Дальше — тот же предпросмотр, что у таблицы: новые люди, кто уже есть в проекте, ошибки. Нажмите «Импортировать».
   Пока не нажали, ничего не записывается.

### С телефона (iPhone)

Скриншоты можно отправлять прямо из «Фото» через «Поделиться», без компьютера.

1. Администратор открывает «Настройки» → «Фото с телефона» и получает ссылку проекта. Там же — пошаговая настройка
   команды «В CRM» в приложении «Команды»: её делают один раз и могут передать коллегам ссылкой iCloud.
2. В «Фото» выделите скриншоты → «Поделиться» → «В CRM». Придёт уведомление «Принято N фото, распознаю».
3. Через минуту-две карточки появятся в базе проекта «Фото ДД.ММ.ГГГГ» — одна база на день. Неуверенно прочитанные
   добавляются с пометкой «проверить» в комментарии, скриншоты без телефона — не добавляются. Люди, которые уже в
   работе, повторно не загружаются.
4. Фото, отправленные с перерывом больше 15 минут, становятся новой частью базы: на доске рядом с фильтром «База»
   можно выбрать «Часть 2 · 13:40 · 17» и увидеть только эту пачку.
5. Сколько добавлено, сколько не распознано и сколько ещё в очереди — видно в «Настройках» у ссылки проекта.
"""


def split_sections(md: str) -> dict:
    """«## Title» → its text (the heading line included), in order."""
    parts = re.split(r"(?m)^(?=## )", md)
    return {p.split("\n", 1)[0][3:].strip(): p for p in parts if p.startswith("## ")}


def bases_block(table_md: str, list_md: str, used_toc: list) -> str:
    table_html, _ = render("## x\n" + table_md)
    images_html, _ = render("## x\n" + IMAGES_MD)
    strip = lambda h: re.sub(r'^<section class="kb-sec" id="[^"]*"><h2>x</h2>\n?', "", h).removesuffix("</section>")
    list_html, _ = render("## x\n### Список баз\n" + list_md)
    used_toc.append(("bazy", "Базы", [("iz-tablitsy", "Загрузка из таблицы"), ("iz-izobrazheniy", "Загрузка из изображений"), ("spisok-baz", "Список баз")]))
    return (
        '<section class="kb-sec" id="bazy"><h2>Базы</h2>'
        f"<p>{html.escape(BASES_INTRO)}</p>"
        f'<details class="kb-more" id="iz-tablitsy"><summary>Как загрузить базу из таблицы</summary><div>{strip(table_html)}</div></details>'
        f'<details class="kb-more" id="iz-izobrazheniy"><summary>Как загрузить базу из изображений</summary><div>{strip(images_html)}</div></details>'
        + strip(list_html).replace('<h3 id="spisok-baz-2">', '<h3 id="spisok-baz">').replace('<h3 id="spisok-baz">', '<h3 id="spisok-baz">', 1)
        + "</section>"
    )


def main(guide_path: str) -> None:
    md = pathlib.Path(guide_path).read_text(encoding="utf-8")
    for old, new in PUBLIC_EDITS:
        if old not in md:
            sys.exit(f"Правка для открытой страницы не нашлась — руководство поменялось:\n{old[:120]}…")
        md = md.replace(old, new)
    if re.search(r"iam\.gserviceaccount\.com|@[a-z0-9-]+\.(local|ru|com)\b", md):
        sys.exit("В тексте остался адрес почты — не для открытой страницы")
    secs = split_sections(md)
    admin = secs.get("Для администратора", "")
    m_imp = re.search(r"(?ms)^### Импорт базы\n(.*?)(?=^### |\Z)", admin)
    if "Вход" not in secs or "Базы" not in secs or not m_imp:
        sys.exit("В руководстве нет раздела «Вход» или «Импорт базы» — поправьте порядок в tools/kb.py")
    secs["Для администратора"] = admin.replace(m_imp.group(0), "")
    first, rest_toc = render(secs.pop("Вход"))
    toc = list(rest_toc)
    bases_list = secs.pop("Базы").split("\n", 1)[1].strip() + "\n"
    block = bases_block(m_imp.group(1).strip() + "\n", bases_list, toc)
    body_rest, toc_rest = render("".join(secs.values()))
    body = first + block + body_rest
    toc += toc_rest

    index = (ROOT / "index.html").read_text(encoding="utf-8")
    head = index[: index.index("<main>")]
    foot = re.sub(r"<script>.*?</script>", "", index[index.index("</main>"):], flags=re.S)
    head = head.replace("<title>Recruit CRM — подбор под контролем</title>", "<title>База знаний — Recruit CRM</title>")
    head = re.sub(r'<link rel="canonical"[^>]*>', '<link rel="canonical" href="https://recruitcrm.pro/baza-znaniy/">', head)
    head = re.sub(r'<meta property="og:url"[^>]*>', '<meta property="og:url" content="https://recruitcrm.pro/baza-znaniy/">', head)
    head = re.sub(r'<meta property="og:title"[^>]*>', '<meta property="og:title" content="База знаний Recruit CRM">', head)
    head = re.sub(r'<meta (name|property)="(og:)?description"[^>]*>', "", head)
    # Only by the direct link: no site navigation in the header.
    head = re.sub(r'<div class="navlinks"[^>]*>.*?</div>', "", head, flags=re.S)
    head = re.sub(r'<button class="menu-btn".*?</button>', "", head, flags=re.S)
    head = head.replace('<a class="brand" href="#">', '<a class="brand" href="/">')
    foot = re.sub(r'<div class="footerlinks">.*?</div>', '<div class="footerlinks"><span>© 2026</span></div>', foot, flags=re.S)
    foot = foot.replace('<a class="brand" href="#">', '<a class="brand" href="/">')
    css = (".kb{display:grid;grid-template-columns:270px minmax(0,1fr);gap:56px;padding:48px 0 80px;align-items:start}"
           ".kb-side{position:sticky;top:104px;max-height:calc(100vh - 124px);overflow:auto;padding-right:6px}"
           ".kb-side input{width:100%;font:inherit;font-size:15px;padding:10px 12px;border:1px solid #c3cdd8;border-radius:8px;background:#fff;color:var(--ink);margin-bottom:14px}"
           ".kb-side input:focus{outline:2px solid #2a7de1;outline-offset:1px;border-color:#2a7de1}"
           "nav>.demo-btn{margin-left:auto}.kb-toc{display:grid;gap:1px;font-size:14px;height:auto;align-items:start}.kb-toc a{padding:6px 10px;border-radius:7px;color:var(--muted)}.kb-toc a:hover{background:#eef2f6;color:var(--ink)}"
           ".kb-toc a.sub{padding-left:24px;font-size:13px}.kb-head h1{font-size:clamp(34px,4vw,52px);letter-spacing:-2px;margin:18px 0 12px}"
           ".kb-head p{max-width:620px;font-size:16px}.kb-body{min-width:0;max-width:760px}"
           ".kb-sec{padding:34px 0 8px;border-top:1px solid var(--line);scroll-margin-top:96px}.kb-sec:first-of-type{border-top:0}"
           ".kb-sec h2{font-size:28px;letter-spacing:-.8px;margin:0 0 14px}.kb-sec h3{font-size:19px;margin:26px 0 8px;scroll-margin-top:96px}"
           ".kb-sec p,.kb-sec li{color:var(--ink);font-size:15px;line-height:1.65}.kb-sec ul,.kb-sec ol{padding-left:22px;display:grid;gap:8px;margin:10px 0 16px}"
           ".kb-sec li::marker{color:var(--brand)}.kb-sec ul ul{margin:8px 0 0}.kb-sec b{font-weight:600}"
           ".kb-sec code{font:13px/1.4 ui-monospace,SFMono-Regular,Menlo,monospace;background:#eef2f6;border-radius:5px;padding:1px 5px;overflow-wrap:anywhere}"
           ".kb-empty{display:none;color:var(--muted);padding:24px 0}.kb-sec mark{background:#d8e8fb;color:inherit;border-radius:3px}"
           "details.kb-more{border:1px solid var(--line);border-radius:12px;background:#fff;margin:14px 0;padding:0}details.kb-more:last-child{border-bottom:1px solid var(--line)}.kb-more summary{cursor:pointer;list-style:none;padding:16px 18px;font-weight:600;font-size:16px;display:flex;justify-content:space-between;gap:16px}.kb-more summary::after{content:'+';color:var(--brand);font-size:20px;line-height:1}.kb-more[open] summary::after{content:'−'}.kb-more summary::-webkit-details-marker{display:none}.kb-more>div{padding:0 18px 10px;border-top:1px solid var(--line)}.kb-more h3{font-size:17px}"
           "@media(max-width:900px){.kb{grid-template-columns:1fr;gap:20px;padding-top:28px}.kb-side{position:static;max-height:none}.kb-toc{display:none}}")
    head = head.replace("a:focus-visible,button:focus-visible", css + "a:focus-visible,button:focus-visible", 1)
    toc_html = "".join(
        f'<a href="#{sid}">{html.escape(t)}</a>' + "".join(f'<a class="sub" href="#{s2}">{html.escape(t2)}</a>' for s2, t2 in subs)
        for sid, t, subs in toc
    )
    script = """<script>
const openHash=()=>{const t=document.getElementById(location.hash.slice(1));const d=t&&(t.tagName==='DETAILS'?t:t.closest('details'));if(d)d.open=true};addEventListener('hashchange',openHash);openHash();
const q=document.getElementById('kb-q'),secs=[...document.querySelectorAll('.kb-sec')],empty=document.querySelector('.kb-empty');
q.addEventListener('input',()=>{const v=q.value.trim().toLowerCase();let n=0;
secs.forEach(s=>{const hit=!v||s.textContent.toLowerCase().includes(v);s.hidden=!hit;if(hit)n++;s.querySelectorAll('details').forEach(d=>{d.open=!!v&&d.textContent.toLowerCase().includes(v)})});
document.querySelectorAll('.kb-toc a').forEach(a=>{const t=document.getElementById(a.hash.slice(1));const s=t&&(t.closest('.kb-sec')||t);a.hidden=!!(s&&s.hidden)});
empty.style.display=n?'none':'block';});
</script>"""
    main_html = (f'<main><div class="wrap"><div class="kb"><aside class="kb-side"><input id="kb-q" type="search" placeholder="Поиск по базе знаний" aria-label="Поиск по базе знаний">'
                 f'<nav class="kb-toc" aria-label="Разделы">{toc_html}</nav></aside><div class="kb-body"><div class="kb-head"><div class="eyebrow"><span class="dot"></span>База знаний</div>'
                 f'<h1>Как работать в Recruit CRM</h1><p>Доска, карточка кандидата, звонки, базы, отчёты и настройки — для рекрутеров и администраторов.</p></div>'
                 f'{body}<p class="kb-empty">Ничего не нашлось — попробуйте другое слово.</p></div></div></div>')
    out = head + main_html + foot.replace("</body>", script + "</body>")
    (ROOT / "baza-znaniy").mkdir(exist_ok=True)
    (ROOT / "baza-znaniy" / "index.html").write_text(out, encoding="utf-8")
    print(f"baza-znaniy/index.html: {len(toc)} разделов, {len(out)//1024} КБ")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "../recruit-crm/docs/user-guide.md")
