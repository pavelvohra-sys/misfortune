# -*- coding: utf-8 -*-
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Tuple, Dict, List
import os

# 10 небесных стволов / 12 земных ветвей
STEMS      = ["甲","乙","丙","丁","戊","己","庚","辛","壬","癸"]
ELEMENTS   = ["Дерево","Огонь","Земля","Металл","Вода"]    # s//2
YIN_YANG   = ["ян","инь"]                                  # s%2

BRANCHES = [
    ("子","zi","цзы"),("丑","chou","чоу"),("寅","yin","инь"),("卯","mao","мао"),
    ("辰","chen","чэнь"),("巳","si","сы"),("午","wu","у"),("未","wei","вэй"),
    ("申","shen","шэнь"),("酉","you","ю"),("戌","xu","сю"),("亥","hai","хай"),
]
ANIMALS = {
    "zi":"🐀","chou":"🐂","yin":"🐅","mao":"🐇","chen":"🐉","si":"🐍",
    "wu":"🐎","wei":"🐐","shen":"🐒","you":"🐓","xu":"🐕","hai":"🐖"
}

# ——— Табу еды (много вариантов, выбираем детерминированно по дате/часу/чату)
TABOOS: List[str] = [
    "мёд + зелёный лук",
    "игуана + сметана",
    "краб + овсянка быстрого приготовления",
    "говяжий холодец + бананы",
    "чипсы «Лейс» + шампанское",
    "кактус + шоколадные батончики",
    "мидии + жевательная резинка",
    "селёдка + ванильное мороженое",
    "энергетик + суп из петрушки",
    "фалафель + клюквенный морс",
    "лягушачьи лапки + борщ",
    "дуриан + пельмени",
    "креветки + апельсиновый сок",
    "тунец + латте",
    "шпроты + капучино",
    "ролтон + кокосовое молоко",
    "хинкали + малиновый сироп",
    "суши + варенье из шишек",
    "колбаса «докторская» + айран",
    "стейк тартар + компот из сухофруктов",
    "сыр тофу + «Буратино»",
    "вяленая кета + какао",
    "буженина + «Тархун»",
    "яйцо пашот + кефир комнатной температуры",
    "руккола + сгущёнка",
    "манго + селёдка под шубой",
    "жареные пельмени + клубничный йогурт",
    "паста карбонара + клюквенное варенье",
    "килька в томате + латте без пенки",
]

# ——— Несчастья (как ты присылал, без правок)
MISFORTUNES: List[Dict[str, str]] = [
    {"emoji":"🔥","code":"fire","name":"Май асс из он фаер","desc":"Все сгорит, вали на дачу, там по крайней мере воздух чище"},
    {"emoji":"🌊","code":"flood","name":"Ной гоуз хард","desc":"Сегодня твоего соседа снизу постигнет небесная кара, сделай вид что ты давно в отьезде"},
    {"emoji":"🕳️","code":"hole","name":"Черная дыра","desc":"Экзистенциальный кризис, черная бездна безумия, тлен и безысходность - обычный день, ничего нового"},
    {"emoji":"🧲","code":"theft","name":"Липкие руки","desc":"Тебя облапает пенсионерка"},
    {"emoji":"💻","code":"tech_fail","name":"Синий экран судьбы","desc":"Техника выкинет фокус; VPN перестанет запускаться, ты не сможешь листать рилзы в инстаграм "},
    {"emoji":"🧳","code":"lost","name":"Потеряшка","desc":"Риск потерять ключи/документы/деньги/совесть. теряй последнее, там все равно ничего не осталось"},
    {"emoji":"🤒","code":"illness","name":"Внезапная хворь","desc":"Тебя поразят споры кордицепса, ты станешь грибом "},
    {"emoji":"🧿","code":"curse","name":"В интернетах кто-то неправ","desc":"Сглаз и хейт; ты будешь ввязываться в любой спор в интернете и везде проиграешь"},
    {"emoji":"⏰","code":"deadline","name":"Дедлайны горят","desc":"твоя пьяная бывшая/бывший позвонит тебе через пару минут и расскажет про свои беды"},
    {"emoji":"🗯️","code":"arguments","name":"Скандал на пустом месте","desc":"Ты поссоришься с любимыми сектантами из-зи нюансов жертвоприношения, они перестанут с тобой общаться"},
    {"emoji":"🙈","code":"embarr","name":"Публичный конфуз","desc":"Тебя пригласят провести мастер класс для пенсионеров, ты его сольешь и будешь освистан"},
    {"emoji":"🗃️","code":"bureau","name":"Бюрократический квест","desc":"Собирай вещи, ты уезжаешь в Германию"},
    {"emoji":"🚧","code":"transport","name":"Дороги гнева","desc":"Ты отправляешься в путешествие через всю Россию на Ладе Калина"},
    {"emoji":"🩹","code":"bruise","name":"Лёгкие травмы","desc":"Ты осознаешь, что ничего не добился в этой жизни и продолжишь листать мемасы"},
    {"emoji":"🧯","code":"appliance","name":"Бытовой бунт","desc":"Тараканы организуют профсоюз, захватят холодильник и станут требовать коммунистической утопии "},
    {"emoji":"🧒🐶","code":"kids_pets","name":"Домашние проделки","desc":"Все стены в твоем доме будут исписаны, иногда даже ребенком"},
    {"emoji":"👻","code":"ghost","name":"Ночные гости","desc":"Твой покойный прадед всю ночь будет поносить тебя за недостаочную сыновью почтительность"},
    {"emoji":"🪦","code":"grim","name":"Мрачный знак","desc":"Доллар по сотке"},
]

# ——— Алгоритм циклов
EPOCH = datetime(1970,1,1,0,0,0)
def _idx60(dt: datetime) -> int:      return ((dt - EPOCH).days) % 60
def _stem(dt: datetime) -> int:        return _idx60(dt) % 10
def _branch(dt: datetime) -> int:      return _idx60(dt) % 12
def _hour_branch(dt: datetime) -> int: return ((dt.hour + 1) // 2) % 12  # двухчасовые ветви

# ——— Пиктограммы ветвей (ASCII, чтобы не было «квадратов»)
ICON_DIR = "icons"
def icon_filename(py: str) -> str: return os.path.join(ICON_DIR, f"{py}.png")

def ensure_icons():
    try:
        from PIL import Image, ImageDraw, ImageFont
    except Exception:
        return
    os.makedirs(ICON_DIR, exist_ok=True)
    def load_font(size):
        for path in [
            "arial.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        ]:
            try: return ImageFont.truetype(path, size)
            except Exception: pass
        return ImageFont.load_default()
    font_code = load_font(140); font_ru = load_font(40)
    for han, py, ru in BRANCHES:
        p = icon_filename(py)
        if os.path.exists(p): continue
        img = Image.new("RGB", (512, 512), (20, 20, 24))
        d = ImageDraw.Draw(img)
        d.rounded_rectangle((40, 40, 472, 472), radius=48, fill=(48, 48, 56))
        d.text((256, 230), py.upper(), anchor="mm", font=font_code, fill=(240, 240, 240))
        d.text((256, 360), ru, anchor="mm", font=font_ru, fill=(200, 200, 200))
        img.save(p, "PNG")

@dataclass
class HowlReading:
    dt: datetime
    stem: int
    branch: int
    hour_branch: int
    element: str
    yin_yang: str
    branch_tuple: Tuple[str,str,str]
    hour_branch_tuple: Tuple[str,str,str]
    doom_index: int
    doom_level: int
    doom: Dict[str,str]
    taboo: str

def read_howl(dt: datetime, salt: int = 0) -> HowlReading:
    s  = _stem(dt)
    b  = _branch(dt)
    hb = _hour_branch(dt)
    element = ELEMENTS[s // 2]
    yin_yang = YIN_YANG[s % 2]
    branch_tuple      = BRANCHES[b]
    hour_branch_tuple = BRANCHES[hb]

    # несчастье и степень
    doom_index = (s*12 + b*3 + hb + salt) % len(MISFORTUNES)
    doom_level = ((s + hb + b) % 5) + 1  # 1..5

    # ВАЖНО: табу еды — детерминированно по дате/часу/чату (не застрянет на «мёд+лук»)
    taboo_idx = (s*13 + b*7 + hb*3 + salt) % len(TABOOS)
    taboo = TABOOS[taboo_idx]

    doom = MISFORTUNES[doom_index]
    return HowlReading(dt, s, b, hb, element, yin_yang, branch_tuple, hour_branch_tuple,
                       doom_index, doom_level, doom, taboo)

def render_reading(r: HowlReading) -> str:
    import html as _html
    han, py, ru    = r.branch_tuple
    hhan, hpy, hru = r.hour_branch_tuple
    stars = "☠️" * r.doom_level

    # мягкие, норм советы (китайская медицина/дао-практики) — можно править под себя
    tips = [
        "Дыхание животом 5 минут: выдох длиннее вдоха.",
        "Шесть звуков: xu/печень, he/сердце, hu/селезёнка, si/лёгкие, chui/почки, xi/тройной обогреватель.",
        "Растирание ладоней до тепла и прикладывание к глазам 30–60 сек.",
        "Постукивание грудной клетки 36 раз ладонями.",
        "Прокатка стопы мячом 1–2 минуты.",
        "Согреть нижний даньтянь тёплой грелкой 10 минут.",
        "Имбирный чай с красным фиником и ягодами годжи.",
        "Тёплая ножная ванна 10–15 минут перед сном.",
        "HeGu (LI4) и ZuSanLi (ST36) — самомассаж по 1–2 мин.",
        "NeiGuan (PC6) 1–2 мин; мягкие круги.",
        "FengChi (GB20) у основания черепа — мягкие круги.",
        "Круги плечами и шеи по 6 раз в каждую сторону.",
        "Лёгкая встряска тела 1–2 минуты.",
        "5–10 минут растяжки/бадуаньцзин — выбери 3–4 движения.",
        "Проветривание 3 минуты; по желанию лёгкое благовоние.",
        "Меньше холодного в холодный день; выбирай тёплую пищу.",
        "Тёплая вода маленькими глотками в течение дня.",
        "Растирание поясницы (почки) 1–2 минуты до тепла.",
        "Пауза без экрана 5 минут: взгляд вдаль, плечи вниз.",
        "Массаж живота по часовой 1–2 минуты.",
    ]
    tip = tips[(r.stem + r.branch + r.hour_branch) % len(tips)]

    name = _html.escape(r.doom["name"]); desc = _html.escape(r.doom["desc"])
    tip = _html.escape(tip); taboo = _html.escape(r.taboo)

    lines = [
        f"{r.doom['emoji']} {stars}  <b>{name}</b>",
        f"🕒 <b>Время:</b> {r.dt.isoformat(sep=' ', timespec='minutes')}",
        f"🐉 <b>Знак:</b> {ANIMALS.get(py,'?')} {han} {py} / {ru}; <i>час</i> {ANIMALS.get(hpy,'?')} {hhan} {hpy}",
        f"📜 <b>Описание:</b> {desc}",
        f"⚖️ <b>Элемент дня:</b> {ELEMENTS[r.stem // 2]} ({YIN_YANG[r.stem % 2]})",
        f"🚫 <b>Табу еды:</b> {taboo}",
        f"👻 <b>Совет духов:</b> {tip}",
    ]
    return "\n".join(lines)

# ——— (опционально) iCalendar на год
def ics_for_year(year: int) -> str:
    lines = ["BEGIN:VCALENDAR","VERSION:2.0","PRODID:-//HOWL//ru"]
    cur = datetime(year, 1, 1)
    while cur.year == year:
        r = read_howl(cur)
        uid  = f"{cur.strftime('%Y%m%d')}-{r.doom['code']}@howl"
        title = r.doom["name"]
        desc  = f"{r.doom['emoji']} {r.doom['name']} — {r.doom['desc']} / Табу: {r.taboo}"
        desc  = desc.replace(",", r"\,").replace(";", r"\;").replace("\n", r"\n")
        lines += [
            "BEGIN:VEVENT",
            f"UID:{uid}",
            f"DTSTAMP:{cur.strftime('%Y%m%d')}T000000Z",
            f"DTSTART;VALUE=DATE:{cur.strftime('%Y%m%d')}",
            f"SUMMARY:{title}",
            f"DESCRIPTION:{desc}",
            "END:VEVENT",
        ]
        cur += timedelta(days=1)
    lines.append("END:VCALENDAR")
    return "\n".join(lines)
