# -*- coding: utf-8 -*-
"""
misfortune.py — двигатель HOWL:
- псевдо-«бацзы» (ствол/ветвь/час) от времени «воя»
- категории несчастий (редактируй под себя)
- пиктограммы 12 ветвей (эмодзи-животные)
- 12 «табу на еду» вместо направлений
- советы (TCM/даосские практики, без абсурда)
"""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Tuple, Dict, List
import os

# 10 небесных стволов
STEMS      = ["甲","乙","丙","丁","戊","己","庚","辛","壬","癸"]
ELEMENTS   = ["Дерево","Огонь","Земля","Металл","Вода"]  # s//2
YIN_YANG   = ["ян","инь"]                                # s%2

# 12 земных ветвей (漢字, pinyin, рус. передача)
BRANCHES = [
    ("子","zi","цзы"),("丑","chou","чоу"),("寅","yin","инь"),("卯","mao","мао"),
    ("辰","chen","чэнь"),("巳","si","сы"),("午","wu","у"),("未","wei","вэй"),
    ("申","shen","шэнь"),("酉","you","ю"),("戌","xu","сю"),("亥","hai","хай"),
]

# Животные-эмодзи для ветвей
ANIMALS = {
    "zi":"🐀","chou":"🐂","yin":"🐅","mao":"🐇","chen":"🐉","si":"🐍",
    "wu":"🐎","wei":"🐐","shen":"🐒","you":"🐓","xu":"🐕","hai":"🐖"
}

# 12 «табу на еду» (食物相克, фольклор) — по порядку ветвей 子…亥
BRANCH_TABOOS = [
    "краб + хурма (螃蟹+柿子)",                 # 子
    "молоко + апельсин (牛奶+橙/橘)",            # 丑
    "креветки/краб + большие дозы витамина C",   # 寅
    "тофу + шпинат (豆腐+菠菜)",                 # 卯
    "крепкий чай после краба (浓茶+蟹)",          # 辰
    "личи + алкоголь (荔枝+酒)",                 # 巳
    "арбуз + баранина (西瓜+羊肉)",              # 午
    "мёд + зелёный лук (蜂蜜+葱)",               # 未
    "полевые улитки + кукуруза (田螺+玉米)",     # 申
    "яйцо + соевое молоко (鸡蛋+豆浆)",          # 酉
    "красный финик + огурец (红枣+黄瓜)",        # 戌
    "креветки + тыква (虾+南瓜)",               # 亥
]

# КАТЕГОРИИ НЕСЧАСТИЙ — редактируй под себя (emoji/name/desc)
MISFORTUNES: List[Dict[str, str]] = [
  {"emoji":"🔥","code":"fire","name":"Май асс из он фаер","desc":"Все сгорит, вали на дачу, там по крайней мере воздух чище"},
    {"emoji":"🌊","code":"flood","name":"Ной гоуз хард","desc":"Сегодня твоего соседа снизу постигнет небесная кара, сделай вид что ты давно в отьезде"},
    {"emoji":"🕳️","code":"hole","name":"Черная дыра","desc":"Экзистенциальный кризис, черная бездна безумия, тлен и безысходность - обычный день, ничего нового"},
    {"emoji":"🧲","code":"theft","name":"Липкие руки","desc":"Тебя облапает пенсионерка"},
    {"emoji":"💻","code":"tech_fail","name":"Синий экран судьбы","desc":"Техника выкинет фокус; VPN перестанет запускаться, ты не сможешь листать рилзы в инстаграм "},
    {"emoji":"🧳","code":"lost","name":"Потеряшка","desc":"Риск потерять ключи/документы/деньги/совесть. теряй последнее, там все равно ничего не осталось"},
    {"emoji":"🤒","code":"illness","name":"Внезапная хворь","desc":"Тебя поразят споры кордицепса, ты станешь грибом "},
    {"emoji":"🧿","code":"curse","name":"В интернетах кто-то неправ","desc":"Сглаз и хейт; ты будешь ввязываться в любой спор в интернете и везде проиграешь"},
    {"emoji":"⏰","code":"deadline","name":"Дедлайны горят","desc":"твоя бывшая/бывший позвонит тебе через пару минут"},
    {"emoji":"🗯️","code":"arguments","name":"Скандал на пустом месте","desc":"Ты поссоришься с любимыми сектантами из-зи нюансов жертвоприношения, они перестанут с тобой общаться"},
    {"emoji":"🙈","code":"embarr","name":"Публичный конфуз","desc":"Тебя пригласят провести мастер класс для пенсионеров, ты его сольешь и будешь освистан"},
    {"emoji":"🗃️","code":"bureau","name":"Бюрократический квест","desc":"Собирай вещи, ты уезжаешь в Германию"},
    {"emoji":"🚧","code":"transport","name":"Дороги гнева","desc":"Ты отправляешься в путешествие через всю Россию на Ладе Калина"},
    {"emoji":"🩹","code":"bruise","name":"Лёгкие травмы","desc":"Ты осознаешь, что ничего не добился в этой жизни и продолжишь листать мемасы"},
    {"emoji":"🧯","code":"appliance","name":"Бытовой бунт","desc":"Тараканы организуют профсоюз, захватят холодильник и станут требовать коммунистической утопии "},
    {"emoji":"🧒🐶","code":"kids_pets","name":"Домашние проделки","desc":"Все стены будут исписаны, иногда даже ребенком"},
    {"emoji":"👻","code":"ghost","name":"Ночные гости","desc":"Твой покойный прадед всю ночь будет поносить тебя за недостаочную сыновью почтительность"},
    {"emoji":"🪦","code":"grim","name":"Мрачный знак","desc":"Доллар по сотке"},
]

# Псевдо-«бацзы»
EPOCH = datetime(1970,1,1,0,0,0)

def _idx60(dt: datetime) -> int:      return ((dt - EPOCH).days) % 60
def _stem(dt: datetime) -> int:        return _idx60(dt) % 10
def _branch(dt: datetime) -> int:      return _idx60(dt) % 12
def _hour_branch(dt: datetime) -> int: return ((dt.hour + 1) // 2) % 12  # 23–00 -> 子

# Иконки ветвей
ICON_DIR = "icons"
def icon_filename(py: str) -> str: return os.path.join(ICON_DIR, f"{py}.png")

def ensure_icons():
    """Создаёт 12 PNG (512×512) с эмодзи-животным и подписью PY/рус. Требует Pillow."""
    try:
        from PIL import Image, ImageDraw, ImageFont
    except Exception:
        return
    os.makedirs(ICON_DIR, exist_ok=True)
    try:
        font_big = ImageFont.truetype("arial.ttf", 180)
        font_small = ImageFont.truetype("arial.ttf", 48)
    except Exception:
        from PIL import ImageFont as F
        font_big = F.load_default()
        font_small = F.load_default()
    for han, py, ru in BRANCHES:
        p = icon_filename(py)
        if os.path.exists(p): continue
        img = Image.new("RGB", (512, 512), (24, 24, 24))
        d = ImageDraw.Draw(img)
        animal = ANIMALS.get(py, "❓")
        d.text((256, 150), animal, anchor="mm", font=font_big, fill=(240,240,240))
        d.text((256, 380), f"{py.upper()} / {ru}", anchor="mm", font=font_small, fill=(200,200,200))
        img.save(p, "PNG")

# Модель
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
    taboo: str  # << вместо «направления»

def read_howl(dt: datetime, salt: int = 0) -> HowlReading:
    s  = _stem(dt)
    b  = _branch(dt)
    hb = _hour_branch(dt)
    element = ELEMENTS[s // 2]
    yin_yang = YIN_YANG[s % 2]
    branch_tuple      = BRANCHES[b]
    hour_branch_tuple = BRANCHES[hb]
    doom_index = (s*12 + b*3 + hb + salt) % len(MISFORTUNES)
    doom_level = ((s + hb + b) % 5) + 1  # 1..5
    taboo = BRANCH_TABOOS[b]
    doom = MISFORTUNES[doom_index]
    return HowlReading(dt, s, b, hb, element, yin_yang, branch_tuple, hour_branch_tuple,
                       doom_index, doom_level, doom, taboo)

def render_reading(r: HowlReading) -> str:
    han, py, ru     = r.branch_tuple
    hhan, hpy, hru  = r.hour_branch_tuple
    stars = "☠️" * r.doom_level
    base = (
        f"{r.doom['emoji']} {stars}\n"
        f"{r.dt.isoformat(sep=' ', timespec='minutes')}  [{han} {py} / {ru}; час {hhan} {hpy}]\n"
        f"{r.doom['name']} — {r.doom['desc']}\n"
        f"Элемент дня: {r.element} ({r.yin_yang}); табу еды: {r.taboo}."
    )
    # Советы (TCM/даосские практики) — редактируй при желании
    tips = [
        "Дыхание животом (нижний даньтянь) 5 минут: выдох длиннее вдоха.",
        "Шесть целительных звуков: xu/печень, he/сердце, hu/селезёнка, si/лёгкие, chui/почки, xi/тройной обогреватель.",
        "Растирание ладоней до тепла и прикладывание к глазам 30–60 сек.",
        "Мягкое постукивание грудной клетки 36 раз ладонями.",
        "Прокатка стопы мячом 1–2 минуты на каждую.",
        "Согрев нижнего даньтянь тёплой грелкой 10 минут (не горячо).",
        "Имбирный чай с красным фиником и ягодами годжи по вкусу.",
        "Тёплая ножная ванна с щепоткой соли 10–15 минут перед сном.",
        "HeGu (LI4) и ZuSanLi (ST36) — самомассаж по 1–2 мин на сторону.",
        "NeiGuan (PC6) 1–2 мин при тревоге/тошноте; мягкие круги.",
        "Разогрев FengChi (GB20) у основания черепа мягкими кругами.",
        "Плавные круги плечами и шеи по 6 раз в каждую сторону.",
        "Лёгкая встряска тела 1–2 минуты для снятия застоя.",
        "5–10 минут Baduanjin/растяжки — выбери 3–4 движения.",
        "Проветривание 3 минуты; по желанию лёгкое благовоние.",
        "Меньше холодного в холодный день; выбирай тёплую пищу.",
        "Тёплая вода небольшими глотками в течение дня.",
        "Растирание поясницы (область почек) 1–2 минуты до тепла.",
        "Пауза без экрана 5 минут: взгляд вдаль, расслабь плечи.",
        "Самомассаж живота по часовой стрелке 1–2 минуты.",
    ]
    tip = tips[(r.stem + r.branch + r.hour_branch) % len(tips)]
    return base + "\n" + "Совет духов: " + tip

# .ics календарь на год (один «приговор» в день)
def ics_for_year(year: int) -> str:
    lines = ["BEGIN:VCALENDAR","VERSION:2.0","PRODID:-//Ghost Cry Oracle//ru"]
    cur = datetime(year, 1, 1)
    while cur.year == year:
        r = read_howl(cur)
        uid  = f"{cur.strftime('%Y%m%d')}-{r.doom['code']}@ghost-cry"
        title = r.doom["name"]
        desc  = f"{r.doom['emoji']} {r.doom['name']} — {r.doom['desc']} / Табу: {BRANCH_TABOOS[r.branch]}"
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
