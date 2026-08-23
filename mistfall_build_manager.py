from __future__ import annotations

import json
import math
import re
import os
import sys
import urllib.request
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    from PySide6.QtCore import Qt, QThread, Signal, QSize, QPoint, QTimer
    from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QPen, QPixmap, QCursor, QPolygon, QPainterPath
    from PySide6.QtWidgets import (
        QApplication,
        QDialog,
        QDialogButtonBox,
        QComboBox,
        QCheckBox,
        QFrame,
        QGridLayout,
        QHBoxLayout,
        QLabel,
        QLineEdit,
        QMainWindow,
        QMessageBox,
        QPushButton,
        QScrollArea,
        QSizePolicy,
        QSpacerItem,
        QSpinBox,
        QStackedWidget,
        QTabBar,
        QTabWidget,
        QTableWidget,
        QTableWidgetItem,
        QVBoxLayout,
        QWidget,
        QHeaderView,
        QGraphicsDropShadowEffect,
    )
except ImportError:
    print("PySide6 не установлен. Установи его командой:  python -m pip install PySide6")
    raise


APP_NAME = "Менеджер сборок Mistfall 4.2"
DATA_URLS = (
    "https://raw.githubusercontent.com/Mistfall-Builder/mistfall-builder.github.io/refs/heads/main/donnees.json",
    "https://mistfall-builder.github.io/donnees.json",
)
B62 = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"

CLASS_RU = {
    "Mercenary": "Наёмник",
    "Sorcerer": "Чародей",
    "Blackarrow": "Чёрная стрела",
    "Shadowstrix": "Тенестрикс",
    "Seer": "Провидец",
    "Withered Knight": "Иссохший рыцарь",
}

AFFIX_RU = {
    # Полный список основных атрибутов, сверенный по русской локализации игры.
    "Valor": "Доблесть",
    "Aegis": "Эгида",
    "Eloquence": "Красноречие",
    "Creation": "Создание",
    "Wrath": "Гнев",
    "Tenacious": "Живучесть",
    "Seamless": "Непрерывность",
    "Sky Piercer": "Небесный пронзатель",
    "Bulwark": "Защита",
    "Vitality": "Энергичность",
    "Fervid": "Пыл",
    "Iron Helmet": "Железный шлем",
    "Swift": "Быстрота",
    "Seeker": "Ловец",
    "Stoic": "Стоик",
    "Elusive": "Неуловимость",
    "Ranged": "Дальний бой",
    "Ethereal": "Бесплотность",
    "Sleight of Hand": "Ловкость",
    "Fervor": "Рвение",
    "Brotherhood": "Братство",
    "Blessing": "Благословение",
    "Smiting": "Угнетение",
    "Spirit Shield": "Щит духа",
    "Curse": "Проклятие",
    "Burst": "Взрыв",
    "Unyielding": "Непреклонность",
    "Focused": "Концентрация",
    "Strife": "Раздор",
    "Distant Ward": "Защита на расстоянии",
    "Wealth": "Богатство",

    # Поля, которые присутствуют в базе Mistfall Builder, но не входят
    # в основной экран списка атрибутов или используются как внутренние эффекты.
    "Spirit Spring": "Источник духа",
    "Physical Damage Reduction": "Физическое сопротивление",
    "Magic Damage Reduction": "Магическое сопротивление",
    "Resilience": "Выносливость",
    "Powerful": "Физическая мощь",
    "Wise": "Магическая мощь",
    "Critical Damage": "Критический урон",
    "Defense Penetration": "Пробивание защиты",
    "Lifebane": "Губитель жизни",
    "Skill Energy Cost Reduction": "Снижение расхода энергии умений",
    "Block Energy Cost Reduction": "Снижение расхода энергии блока",
    "Energy Recovery Speed Increase": "Скорость восстановления энергии",
    "Siphon": "Поглощение",
}

# Порядок как на полном экране атрибутов в игре.
GAME_AFFIX_ORDER = [
    # Атака
    "Valor", "Wrath", "Sky Piercer", "Fervid", "Seeker",
    "Ranged", "Fervor", "Smiting", "Burst", "Strife",
    # Защита
    "Aegis", "Tenacious", "Bulwark", "Iron Helmet", "Ethereal",
    "Stoic", "Brotherhood", "Spirit Shield", "Unyielding", "Distant Ward",
    "Resilience",
    # Поддержка
    "Eloquence", "Seamless", "Vitality", "Swift", "Elusive",
    "Sleight of Hand", "Blessing", "Curse", "Wealth", "Focused", "Creation",
]

AFFIX_CATEGORY = {
    # offense
    "Valor": "offense", "Wrath": "offense", "Sky Piercer": "offense",
    "Fervid": "offense", "Ranged": "offense", "Fervor": "offense",
    "Smiting": "offense", "Burst": "offense", "Strife": "offense", "Seeker": "offense",
    # defense
    "Aegis": "defense", "Tenacious": "defense", "Bulwark": "defense",
    "Iron Helmet": "defense", "Stoic": "defense", "Brotherhood": "defense",
    "Spirit Shield": "defense", "Unyielding": "defense",
    "Distant Ward": "defense", "Ethereal": "defense", "Resilience": "defense",
    # utility
    "Eloquence": "utility", "Creation": "utility", "Seamless": "utility",
    "Vitality": "utility", "Swift": "utility",
    "Elusive": "utility", "Sleight of Hand": "utility", "Blessing": "utility",
    "Curse": "utility", "Focused": "utility", "Wealth": "utility",
}


AFFIX_DESC_RU = {
    "Valor": "Повышает атаку. По достижении определённого уровня также повышает пробивание защиты.",
    "Aegis": "Повышает защиту. По достижении определённого уровня повышает физическое сопротивление.",
    "Eloquence": "Повышает скорость произнесения. По достижении определённого уровня произнесение нельзя прервать незначительной отдачей.",
    "Creation": "Повышает длительность конструкций. По достижении определённого уровня успешный призыв конструкции временно повышает физический и магический урон.",
    "Wrath": "При низком здоровье повышает физический и магический урон. На высоком уровне дополнительно повышает атаку.",
    "Tenacious": "Повышает максимальное здоровье. По достижении определённого уровня повышает лечение.",
    "Seamless": "Повышает скорость перезарядки умений. По достижении определённого уровня добивание противника дополнительно сокращает текущие перезарядки.",
    "Sky Piercer": "Применение умений в воздухе повышает физический и магический урон. На высоком уровне также снижает расход энергии на умения в воздухе.",
    "Bulwark": "Повышает снижение урона при блоке. По достижении требуемого уровня снижает расход энергии на блок.",
    "Vitality": "Повышает максимальную энергию. По достижении определённого уровня один раз защищает от состояния нехватки энергии, затем уходит на перезарядку.",
    "Fervid": "При высоком здоровье повышает физический и магический урон. На высоком уровне также снижает расход энергии умений.",
    "Iron Helmet": "Повышает сопротивление критическому урону. На высоком уровне уменьшает отдачу и оглушение от полученных критических ударов.",
    "Swift": "Повышает скорость передвижения во время приседания, бесшумной ходьбы, прицеливания и произнесения.",
    "Seeker": "Попадание по врагу временно повышает скорость передвижения. На высоком уровне эффект может суммироваться.",
    "Stoic": "При низком здоровье повышает физическое и магическое сопротивление. На высоком уровне также восстанавливает здоровье.",
    "Elusive": "Снижает расход энергии на уклонение.",
    "Ranged": "Попадание с большой дистанции временно повышает физический и магический урон. На высоком уровне повышает эффективную дальность.",
    "Ethereal": "Повышает сопротивление урону от падения. На высоком уровне падение перестаёт вызывать ошеломление.",
    "Sleight of Hand": "Повышает скорость взаимодействия. Взаимодействие нельзя прервать незначительной отдачей; эффект имеет перезарядку.",
    "Fervor": "Попадания временно накапливают бонус к физическому и магическому урону. На высоком уровне при достаточном числе зарядов также растёт пробивание защиты.",
    "Brotherhood": "Пока вы живы, повышает защиту вам и союзникам. В группе действует только самый высокий уровень. На высоком уровне также повышает атаку.",
    "Blessing": "Повышает длительность положительных эффектов, наложенных вами.",
    "Smiting": "Критические удары восстанавливают энергию. На высоком уровне критические удары также сокращают перезарядку умений.",
    "Spirit Shield": "Повышает прочность щита. На высоком уровне накладываемые вами щиты дополнительно дают магическое сопротивление.",
    "Curse": "Повышает длительность отрицательных эффектов, наложенных вами.",
    "Burst": "Повышает урон особого добивающего приёма Иссохшего рыцаря.",
    "Unyielding": "Когда новый враг наносит вам урон, временно повышаются физическое и магическое сопротивление. Эффект может складываться.",
    "Focused": "Повышает скорость заряда. На высоком уровне также повышает скорость передвижения во время заряда.",
    "Strife": "Повышает урон оружия ближнего боя. На высоком уровне урон дополнительно растёт за каждого находящегося рядом врага.",
    "Distant Ward": "Если атакующий находится далеко, попадание временно повышает физическое и магическое сопротивление. На высоком уровне усиливается защита от дальних атак.",
    "Wealth": "Повышает количество золотой крови, получаемой в PvE и подземельях.",
    "Spirit Spring": "Усиливает лечение источником духа и связанные с ним эффекты.",
    "Resilience": "Сокращает длительность получаемых отрицательных эффектов и контроля.",
    "Lifebane": "Удары по противникам с высоким запасом здоровья временно повышают наносимый урон.",
    "Siphon": "Убийство противника восстанавливает здоровье; на высоком уровне может временно повысить атаку.",
}


# Проверенные по русской локализации игры названия из пользовательских скриншотов.
# Ключи здесь — английские имена из donnees.json. Если перевода ещё нет,
# интерфейс безопасно показывает оригинальное английское имя.
ITEM_NAME_RU = {
    "True Intent Catalyst": "Катализатор «Подлинное намерение»",
    "Rusty Spiked Mace": "Ржавая булава с шипами",
    "True Prayer Miter": "Митра искренней молитвы",
    "True Prayer Vestment": "Риза искренней молитвы",
    "True Prayer Bracers": "Наручи искренней молитвы",
    "True Prayer Pants": "Штаны искренней молитвы",
    "True Prayer Greaves": "Наголенники искренней молитвы",
    "Ragon's Pendant": "Подвеска Рагона",
    "Ragon's Ring": "Кольцо Рагона",
    "Beast Spirit Catalyst": "Катализатор «Дух зверя»",
    "Arcane Elixir Catalyst": "Катализатор «Мистический эликсир»",
    "Martyr's Hood": "Капюшон мученика",
    "Martyr's Vestment": "Риза мученика",
    "Martyr's Bracers": "Наручи мученика",
    "Martyr's Pants": "Штаны мученика",
    "Martyr's Greaves": "Наголенники мученика",
    "Sorcery Collar": "Обруч колдуна",
    "Mithril Ring": "Мифриловое кольцо",
    "Byrnes's Ash Urn": "Урна с прахом Бирнса",
    "Holy Saint's Miter": "Митра святого",
    "Holy Saint's Vestment": "Риза святого",
    "Holy Saint's Bracers": "Наручи святого",
    "Holy Saint's Pants": "Штаны святого",
    "Holy Saint's Greaves": "Наголенники святого",
    "Raven War Pendant": "Подвеска вороньей войны",
    "Eye of the Sea Giant": "Око морского гиганта",
}

# Дополнительный перевод всех базовых названий из текущей базы.
# Сначала используются точные названия выше, затем эти шаблоны.
ITEM_SPECIAL_RU = {
    "Absolution": "Отпущение",
    "Ancestral Blessing Ring": "Кольцо благословения предков",
    "Antique Mace": "Старинная булава",
    "Beak Necklace": "Ожерелье «Клюв»",
    "Benediction Amulet": "Амулет благословения",
    "Blade of Destined Death": "Клинок предначертанной смерти",
    "Blind Eye Staff": "Посох слепого ока",
    "Bloodborn Amulet": "Амулет кроворождённого",
    "Bond of Friendship": "Узы дружбы",
    "Brass Necklace": "Латунное ожерелье",
    "Carved Amulet": "Резной амулет",
    "Carved Dagger": "Резной кинжал",
    "Commander Seal Ring": "Кольцо с печатью командира",
    "Commander Sword and Shield": "Меч и щит командира",
    "Convergence Staff": "Посох схождения",
    "Crude Hammer": "Грубый молот",
    "Deathclaw Hunter": "Охотник Смертекогтя",
    "Decorative Ring": "Декоративное кольцо",
    "Demonbane Ring": "Кольцо погибели демонов",
    "Discipline Pendant": "Подвеска дисциплины",
    "Dominance Amulet": "Амулет господства",
    "Dragon Slumber Necklace": "Ожерелье драконьего сна",
    "Dragonbreath Ring": "Кольцо дыхания дракона",
    "Dreamweaver Necklace": "Ожерелье ткача снов",
    "Einherjar's Blessing Necklace": "Ожерелье благословения эйнхерия",
    "Empyrean Rain Staff": "Посох небесного дождя",
    "Engraved Ring": "Гравированное кольцо",
    "Executioner Greatsword": "Двуручный меч палача",
    "Exile Greatsword": "Двуручный меч изгнанника",
    "Faded Apprentice Staff": "Выцветший посох ученика",
    "Fang-Piercer Dagger": "Кинжал «Пронзатель клыков»",
    "Fine Iron Sword and Shield": "Меч и щит из качественного железа",
    "Focus Staff": "Посох сосредоточения",
    "Frostspeaker Pendant": "Подвеска глашатая мороза",
    "Gem Lizard Dagger": "Кинжал самоцветной ящерицы",
    "Guard Polearm and Shield": "Древковое оружие и щит стража",
    "Handcrafted Longbow": "Самодельный длинный лук",
    "Hunter's Ring": "Кольцо охотника",
    "Jungle Emissary Necklace": "Ожерелье посланника джунглей",
    "Lover's Ring": "Кольцо влюблённых",
    "Magica Hammer": "Магический молот",
    "Magical Knot Catalyst": "Катализатор «Магический узел»",
    "Mercy": "Милосердие",
    "Military Hammer": "Военный молот",
    "Morningstar Mace": "Булава-моргенштерн",
    "Night Vigil Polearm and Shield": "Древковое оружие и щит ночного дозора",
    "Obsidian Sledgehammer": "Обсидиановая кувалда",
    "Oil-soaked Wooden Bow": "Промасленный деревянный лук",
    "Recruit Sword and Shield": "Меч и щит рекрута",
    "Retribution Ring": "Кольцо возмездия",
    "Rose Proclamation": "Провозглашение розы",
    "Rough Handcrafted Longbow": "Грубый самодельный длинный лук",
    "Rusty Crude Hammer": "Ржавый грубый молот",
    "Rusty Recruit Sword and Shield": "Ржавый меч и щит рекрута",
    "Rusty Squire Greatsword": "Ржавый двуручный меч оруженосца",
    "Rusty Wooden-Handled Dual Blades": "Ржавые парные клинки с деревянными рукоятями",
    "Sacred Heart Greatsword": "Двуручный меч Священного сердца",
    "Serpent's Whisper": "Шёпот змея",
    "Shadow Amberflux Ring": "Кольцо теневого янтаря",
    "Sirius Ring": "Кольцо Сириуса",
    "Skullcrusher": "Череполом",
    "Soulbane Necklace": "Ожерелье погибели душ",
    "Spiked Mace": "Булава с шипами",
    "Spirit Feline Dual Blades": "Парные клинки духа кошки",
    "Spiritwood Drumstick": "Барабанная палочка из духовного дерева",
    "Squire Greatsword": "Двуручный меч оруженосца",
    "Stargazing Ring": "Кольцо звездочёта",
    "Studded Sword and Shield": "Шипованный меч и щит",
    "Thorn Polearm and Shield": "Шипастое древковое оружие и щит",
    "Traveler's Ring": "Кольцо путника",
    "Tri-phase Knot Pendant": "Подвеска трёхфазного узла",
    "Twilight Knot Catalyst": "Катализатор «Сумеречный узел»",
    "Veil Dual Blades": "Парные клинки покрова",
    "Venomfang": "Ядовитый клык",
    "Venomfang Dagger": "Кинжал «Ядовитый клык»",
    "Warrior Pendant": "Подвеска воина",
    "Wooden-Handled Dual Blades": "Парные клинки с деревянными рукоятями",
    "Woodling Guardian Ring": "Кольцо хранителя древесника",
    "Worn Carved Dagger": "Изношенный резной кинжал",
    "Yew Longbow": "Тисовый длинный лук",
    "Moon Deity - Soul Devourer Catalyst": "Лунное божество — катализатор пожирателя душ",
    "Moon Deity - Summoning Catalyst": "Лунное божество — катализатор призыва",
}

ITEM_SET_PREFIX_RU = {
    "Ace Assassin": "мастера-убийцы",
    "Apprentice": "ученика",
    "Artisan's": "ремесленника",
    "Black Iris": "Чёрного ириса",
    "Bloodwrath General": "генерала Кровавой ярости",
    "Champion's": "чемпиона",
    "Crude Recruit": "неопытного рекрута",
    "Crusade": "крестового похода",
    "Crusader": "крестоносца",
    "Eagle God": "Бога-орла",
    "Emissary": "посланника",
    "Enlightenment": "просветления",
    "Fearless": "бесстрашия",
    "Guard": "стража",
    "Holy Saint's": "святого",
    "Martyr's": "мученика",
    "Moon Priestess": "лунной жрицы",
    "Mysteria Elder": "старейшины Мистерии",
    "Practitioner": "послушника",
    "Raven Priest": "вороньего жреца",
    "Rosen Oath": "клятвы Розен",
    "Rover": "странника",
    "Scaleclaw": "Чешуйчатого когтя",
    "Shadow Skull": "теневого черепа",
    "Shadowstrix": "Тенестрикса",
    "Veteran": "ветерана",
    "True Prayer": "искренней молитвы",
}

ITEM_SLOT_WORD_RU = {
    "Leather Boots": "Кожаные ботинки",
    "Leather Armor": "Кожаный доспех",
    "Long Boots": "Высокие ботинки",
    "Winged Helm": "Крылатый шлем",
    "Breastplate": "Нагрудник",
    "Vestment": "Риза",
    "Gauntlets": "Перчатки",
    "Bracers": "Наручи",
    "Breeches": "Бриджи",
    "Sabatons": "Сабатоны",
    "Greaves": "Наголенники",
    "Helmet": "Шлем",
    "Crown": "Корона",
    "Miter": "Митра",
    "Hood": "Капюшон",
    "Mask": "Маска",
    "Eyepatch": "Повязка на глаз",
    "Armor": "Доспех",
    "Garb": "Одеяние",
    "Robe": "Роба",
    "Vest": "Жилет",
    "Top": "Куртка",
    "Pants": "Штаны",
    "Tights": "Штаны",
    "Boots": "Ботинки",
    "Shoes": "Обувь",
    "Strongbow": "Мощный лук",
    "Staff": "Посох",
    "Vigor": "Живость",
}

ITEM_LORE_RU = {
    "Byrnes's Ash Urn": (
        "В этой урне хранится прах набожного Бирнса. Исполняя его последнюю волю, "
        "двенадцать учеников взяли по урне, чтобы развеять его останки по миру. "
        "По неизвестной причине эта урна была небрежно брошена."
    ),
    "Holy Saint's Miter": (
        "Головной убор двенадцати учеников мудреца Бирнса. Его украшают узлы из "
        "высушенных цветов — знак скорби и памяти об ушедшем наставнике."
    ),
    "Holy Saint's Vestment": (
        "Изысканная риза, сшитая мастерицами Священной палаты. На внутренней стороне "
        "ворота мелкими стежками вышиты слова о преданности и послушании; конец надписи "
        "истёрся и больше не читается."
    ),
    "Holy Saint's Bracers": (
        "После наступления апокалипсиса обряды аскезы становились всё суровее. "
        "Почитатели закрывали глаза и уши, оставаясь безучастными даже к бедам близких."
    ),
    "Holy Saint's Pants": (
        "«Создание и направление жизненной сущности — сила; её разрушение и изгнание — тоже сила. "
        "Боги нам никогда не были нужны — нас обманывали слишком долго!»"
    ),
    "Holy Saint's Greaves": (
        "Годы бесцельных странствий не позволяли этим сапогам повернуть домой. "
        "Каждая новая весть о погибших близких делала шаги всё тяжелее."
    ),
    "Raven War Pendant": (
        "Перед походом воины нередко оставляют воронам сырое мясо, надеясь, что сытые "
        "вестники Хермейла не поведут их в царство мёртвых."
    ),
    "Ancestral Blessing Ring": (
        "Северяне верят, что после смерти часть души возвращается из мира мёртвых, "
        "чтобы возродиться в той же семье. Считается, что новорождённый, названный "
        "в честь усопшего предка, может унаследовать его волю и добродетель."
    ),
    "Eye of the Sea Giant": (
        "У морских гигантов были кристально-голубые глаза, похожие на лёд северного моря. "
        "После гибели их предводителя Хастайна оставшиеся гиганты рассеялись и исчезли."
    ),
}



# В публичной таблице кодека встречаются cfgId, которых нет в массиве objets.
# Эти две записи подтверждены текущей базой/скриншотами и нужны для корректного
# чтения легендарных аксессуаров.
ITEM_ID_OVERRIDES = {
    1660402: {
        "id": "1660402",
        "n": "Raven War Pendant",
        "g": 6,
        "s": [[4, 2], [1, 1], [3, 1]],
        "i": None,
        "aff": 1,
        "ic": "T_UI_Icon_Equip_1221011.webp",
        "at": {"attack": 8, "combatValue": 500, "magicalIncrease": 0.018},
        "d": "",
    },
    1660403: {
        "id": "1660403",
        "n": "Raven War Pendant",
        "g": 6,
        # Confirmed by the decoded gems in the supplied build:
        # rank-2 Peridot + rank-1 Onyx + rank-1 Peridot.
        "s": [[4, 2], [1, 1], [4, 1]],
        "i": None,
        "aff": 1,
        "ic": "T_UI_Icon_Equip_1221011.webp",
        "at": {"attack": 8, "combatValue": 500, "magicalIncrease": 0.018},
        "d": (
            "Warriors often offer raw meat to crows before marching into battle, "
            "hoping that once Hermeil's heralds are satiated, they won't come to "
            "guide them to the Realm of the Dead."
        ),
    },
    1760103: {
        "id": "1760103",
        "n": "Ancestral Blessing Ring",
        "g": 6,
        # Confirmed by the supplied build:
        # rank-2 Peridot + rank-1 Onyx + rank-1 Amethyst.
        "s": [[4, 2], [1, 1], [2, 1]],
        "i": None,
        "aff": 0,
        "ic": "T_UI_Icon_Equip_1220018.webp",
        "at": {
            "maxHealth": 34,
            "combatValue": 500,
            "physicalReduction": 0.018,
        },
        "d": (
            "The Northerners believe that after death, a part of the soul returns "
            "from the Realm of the Dead to be reborn within the same family. "
            "Naming newborns after deceased relatives is thought to help children "
            "inherit their ancestors' will and virtuous qualities."
        ),
    },
    1760401: {
        "id": "1760401",
        "n": "Eye of the Sea Giant",
        "g": 6,
        "s": [[3, 2], [2, 1], [4, 1]],
        "i": None,
        "aff": 1,
        "ic": "",
        "at": {"attack": 8, "combatValue": 500, "magicalIncrease": 0.018},
        "d": "",
    },
    # Мифический/священный катализатор Провидца, подтверждённый кодом
    # 2nLRaAUNMc9eyBpzOmw4i73E8 и скриншотом пользователя.
    3070904: {
        "id": "3070904",
        "n": "Moon Deity - Soul Devourer Catalyst",
        "g": 7,
        "s": [[4, 2], [1, 1]],
        "i": "Seeker",
        "aff": 1,
        "ic": "3070904.webp",
        "at": {"attack": 40, "combatValue": 600, "magicalIncrease": 0.072},
        "d": "",
    },
    # Второй мифический катализатор из кода
    # 2nLRaAUNMc9eyBpzO3yfTFt5s. Точный арт пока не подменяем
    # легендарной заглушкой: если 3071001.webp отсутствует, UI оставит
    # иконку пустой вместо показа неверной урны.
    3071001: {
        "id": "3071001",
        "n": "Moon Deity - Summoning Catalyst",
        "g": 7,
        "s": [[4, 2], [1, 1]],
        "i": None,
        "aff": 1,
        "ic": "3071001.webp",
        "at": {"attack": 40, "combatValue": 600, "magicalIncrease": 0.072},
        "d": "",
    },
}

GEM_NAME_RU = {
    "Unity Aegis Moonstone": "Лунный камень братства и Щита духа",
    "Persuasive Peridot": "Перидот красноречия",
    "Fortitude-Brotherhood Agate": "Агат живучести и братства",
    "Ranged Power Amethyst": "Аметист дальнего боя",
    "Aegis: Tenacious Agate": "Агат эгиды и живучести",
    "Guardian Moonstone": "Лунный камень эгиды",
    "Tenacious - Wily Peridot": "Живучесть — перидот красноречия",
    "Warding-Brotherhood Agate": "Агат эгиды и братства",
    "Warding Agate": "Агат эгиды",
    "Spellshield Moonstone": "Лунный камень Щита духа",
}

SOCKET_RU = {
    -1: "Универсальный",
    1: "Агат",
    2: "Аметист",
    3: "Лунный камень",
    4: "Перидот",
}

STAT_RU = {
    "attack": "Атака",
    "defence": "Защита",
    "maxHealth": "Максимальное здоровье",
    "combatValue": "Боевая ценность",
    "criticalReduction": "Сопротивление критическому урону",
    "physicalReduction": "Физическое сопротивление",
    "magicalReduction": "Магическое сопротивление",
    "magicalIncrease": "Магический урон",
    "physicalIncrease": "Физический урон",
    "blockRate": "Шанс блока",
}

PERCENT_STATS = {
    "criticalReduction", "physicalReduction", "magicalReduction",
    "magicalIncrease", "physicalIncrease", "blockRate",
}

# Подтверждённые русские описания/уровни атрибутов. Остальные атрибуты
# продолжают использовать данные из базы на английском, пока не появятся
# скриншоты русской локализации.
AFFIX_DETAILS_RU = {
    "Aegis": {
        "desc": "Повышает защиту. По достижении определённого уровня повышает физическое сопротивление.",
        "eff": [
            "Защита +15.", "Защита +30.", "Защита +45.", "Защита +60.",
            "Защита +75. Физическое сопротивление +2,5%.",
            "Защита +90. Физическое сопротивление +2,5%.",
            "Защита +105. Физическое сопротивление +2,5%.",
        ],
    },
    "Tenacious": {
        "desc": "Повышает максимальное здоровье. По достижении определённого уровня повышает лечение.",
        "eff": [
            "Максимальное здоровье +1,8%.", "Максимальное здоровье +3,6%.",
            "Максимальное здоровье +5,4%.", "Максимальное здоровье +7,2%.",
            "Максимальное здоровье +9%. Лечение +7,5%.",
            "Максимальное здоровье +10,8%. Лечение +7,5%.",
            "Максимальное здоровье +12,6%. Лечение +7,5%.",
        ],
    },
    "Brotherhood": {
        "desc": "Пока вы живы, повышает защиту вам и союзникам. Если этот атрибут есть у нескольких членов отряда, срабатывает только атрибут самого высокого уровня. По достижении определённого уровня повышает атаку вам и союзникам.",
        "eff": [
            "Защита +6.", "Защита +12.", "Защита +18.", "Защита +24.",
            "Защита +30. Атака +1,8%.", "Защита +36. Атака +1,8%.",
            "Защита +42. Атака +1,8%.",
        ],
    },
    "Spirit Shield": {
        "desc": "Повышает прочность щита. По достижении определённого уровня накладываемые вами щиты дают защищённым магическое сопротивление во время действия.",
        "eff": [
            "Прочность щита +2,4%.", "Прочность щита +4,8%.",
            "Прочность щита +7,2%.", "Прочность щита +9,6%.",
            "Прочность щита +12%. Магическое сопротивление +5%.",
            "Прочность щита +14,4%. Магическое сопротивление +5%.",
            "Прочность щита +16,8%. Магическое сопротивление +5%.",
        ],
    },
    "Eloquence": {
        "desc": "Повышает скорость произнесения. По достижении определённого уровня произнесение нельзя прервать незначительной отдачей. Перезарядка: 10–15 с. (формулировка зависит от версии локализации).",
        "eff": [
            "Скорость произнесения +3%.", "Скорость произнесения +6%.",
            "Скорость произнесения +9%.", "Скорость произнесения +12%.",
            "Скорость произнесения +15%; защита от незначительного прерывания.",
            "Скорость произнесения +18%; защита от незначительного прерывания.",
            "Скорость произнесения +21%; защита от незначительного прерывания.",
        ],
    },
    "Ranged": {
        "desc": "Попадание временно повышает физический и магический урон, если расстояние до цели достаточно велико. На высоком уровне увеличивает эффективную дальность дальних атак.",
        "eff": [
            "Физический и магический урон +1,6%.", "Физический и магический урон +3,2%.",
            "Физический и магический урон +4,8%.", "Физический и магический урон +6,4%.",
            "Физический и магический урон +8%. Эффективная дальность +12%.",
            "Физический и магический урон +9,6%. Эффективная дальность +12%.",
            "Физический и магический урон +11,2%. Эффективная дальность +12%.",
        ],
    },
}

RARITY_RU = {
    1: "Повреждённый",
    2: "Обычный",
    3: "Редкий",
    4: "Отличный",
    5: "Эпический",
    6: "Легендарный",
    7: "Священный",
    8: "Призматический",
}

RARITY_COLORS = {
    1: "#5b5149",
    2: "#7b7b78",
    3: "#2d9a45",
    4: "#267aa5",
    5: "#81459e",
    6: "#c28a32",
    7: "#d9b957",
    8: "#b66bd6",
}

SLOT_RU = {
    0: "Голова",
    1: "Нагрудник",
    2: "Наручи",
    3: "Штаны",
    4: "Наголенники",
    5: "Ожерелье",
    6: "Кольцо",
    10: "Оружие I",
    11: "Оружие II",
}

DISPLAY_SLOT_ORDER = [10, 11, 0, 1, 2, 3, 4, 5, 6]

# Вертикальная раскладка как в игровом окне сборки.
# value: row, column, row_span, column_span, alignment
EQUIPMENT_GRID_LAYOUT = {
    10: (0, 0, 1, 1, Qt.AlignCenter),  # оружие I
    11: (0, 1, 1, 1, Qt.AlignCenter),  # оружие II
    0:  (1, 0, 1, 1, Qt.AlignCenter),  # шлем
    1:  (1, 1, 1, 1, Qt.AlignCenter),  # нагрудник
    2:  (2, 0, 1, 1, Qt.AlignCenter),  # руки
    3:  (2, 1, 1, 1, Qt.AlignCenter),  # ноги
    4:  (3, 0, 1, 2, Qt.AlignCenter),  # ботинки
    5:  (4, 0, 1, 1, Qt.AlignCenter),  # ожерелье
    6:  (4, 1, 1, 1, Qt.AlignCenter),  # кольцо
}

BUILD_CARD_WIDTH_PHYSICAL = 506
BUILD_CARD_GAP_PHYSICAL = 8

WEAPON_SLOTS = (10, 11)
DEFAULT_ACTIVE_WEAPON_SLOT = 10

SLOT_SHORT = {
    0: "ГЛ",
    1: "ТЛ",
    2: "НР",
    3: "ШТ",
    4: "НГ",
    5: "ОЖ",
    6: "КЛ",
    10: "I",
    11: "II",
}


def get_app_dir() -> Path:
    if os.name == "nt":
        base = Path(os.getenv("APPDATA", str(Path.home())))
    else:
        base = Path.home() / ".config"
    folder = base / "MistfallBuildManager"
    folder.mkdir(parents=True, exist_ok=True)
    return folder


APP_DIR = get_app_dir()
BUILDS_FILE = APP_DIR / "builds.json"
CACHE_DATA_FILE = APP_DIR / "mistfall_data.json"
BUNDLED_DATA_FILE = Path(__file__).resolve().with_name("mistfall_data.json")

# Реальные игровые иконки лежат рядом с программой.
BUNDLED_ICONS_DIR = Path(__file__).resolve().with_name("icons")
ICON_MAP_FILE = Path(__file__).resolve().with_name("icon_map.txt")

CLASS_ICON_FOLDERS = {
    "Mercenary": "mercenary",
    "Sorcerer": "sorcerer",
    "Blackarrow": "blackarrow",
    "Shadowstrix": "shadowstrix",
    "Seer": "seer",
    "Withered Knight": "withered-knight",
}
APP_ICONS_DIR = APP_DIR / "icons"
APP_ICONS_DIR.mkdir(parents=True, exist_ok=True)
ICONS_DIR = BUNDLED_ICONS_DIR

AFFIX_ICON_FILES = {
    "Ethereal": "Бесплотность.png",
    "Blessing": "Благословение.png",
    "Wealth": "Богатство.png",
    "Brotherhood": "Братство.png",
    "Swift": "Быстрота.png",
    "Burst": "Взрыв.png",
    "Wrath": "Гнев.png",
    "Ranged": "Дальний бой.png",
    "Valor": "Доблесть.png",
    "Iron Helmet": "Железный шлем.png",
    "Tenacious": "Живучесть.png",
    "Distant Ward": "Защита на расстоянии.png",
    "Bulwark": "Защита.png",
    "Focused": "Концентрация.png",
    "Eloquence": "Красноречие.png",
    "Seeker": "Ловец.png",
    "Sleight of Hand": "Ловкость.png",
    "Sky Piercer": "Небесный пронзатель.png",
    "Unyielding": "Непреклонность.png",
    "Seamless": "Непрерывность.png",
    "Elusive": "Неуловимость.png",
    "Curse": "Проклятие.png",
    "Fervid": "Пыл.png",
    "Strife": "Раздор.png",
    "Fervor": "Рвение.png",
    "Creation": "Создание.png",
    "Stoic": "Стоик.png",
    "Smiting": "Угнетение.png",
    "Spirit Shield": "Щит духа.png",
    "Aegis": "Эгида.png",
    "Vitality": "Энергичность.png",
}


_ICON_MAP_ITEM_FILES: dict[tuple[str, str], str] | None = None


def _normalize_icon_map_folder(raw: str) -> str:
    return raw.strip().strip("/\\")


def load_item_icon_map() -> dict[tuple[str, str], str]:
    """
    Читает icon_map.txt пользователя.

    Ключ: (папка класса, английское имя предмета)
    Значение: точное имя файла WEBP.

    Это важнее item["ic"], потому что одинаковые имена файлов могут встречаться
    в разных папках классов, а у части записей базы поле ic отсутствует.
    """
    global _ICON_MAP_ITEM_FILES
    if _ICON_MAP_ITEM_FILES is not None:
        return _ICON_MAP_ITEM_FILES

    mapping: dict[tuple[str, str], str] = {}
    if not ICON_MAP_FILE.exists():
        _ICON_MAP_ITEM_FILES = mapping
        return mapping

    try:
        lines = ICON_MAP_FILE.read_text(encoding="utf-8-sig").splitlines()
    except Exception:
        _ICON_MAP_ITEM_FILES = mapping
        return mapping

    current_folder = ""
    current_file = ""

    section_folder_patterns = {
        "НАЁМНИК": "mercenary",
        "ЧАРОДЕЙ": "sorcerer",
        "ЧЁРНАЯ СТРЕЛА": "blackarrow",
        "ТЕНЕСТРИКС": "shadowstrix",
        "ПРОВИДЕЦ": "seer",
        "ИССОХШИЙ РЫЦАРЬ": "withered-knight",
    }

    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            continue

        upper = line.upper()
        for section_name, folder in section_folder_patterns.items():
            if section_name in upper and "ПАПКА" in upper:
                current_folder = folder
                current_file = ""
                break

        if current_folder not in set(CLASS_ICON_FOLDERS.values()):
            continue

        # Строка с именем картинки.
        file_match = re.match(r"([^\s].*?\.(?:webp|png))\s*$", line, re.IGNORECASE)
        if file_match and not line.startswith("->"):
            current_file = Path(file_match.group(1).strip()).name
            continue

        if line.startswith("->") and current_file:
            description = line[2:].strip()
            # Формат:
            #   -> Провидец (Seer) · Шлем · Martyr's Hood (тир 3)
            parts = [part.strip() for part in description.split("·")]
            if len(parts) < 3:
                continue

            item_name = re.sub(r"\s*\(тир\s*\d+\)\s*$", "", parts[-1], flags=re.IGNORECASE).strip()
            if item_name:
                mapping[(current_folder, item_name.casefold())] = current_file

    _ICON_MAP_ITEM_FILES = mapping
    return mapping


def mapped_item_icon_filename(class_name: str, item_name: str) -> str | None:
    folder = CLASS_ICON_FOLDERS.get(class_name)
    if not folder or not item_name:
        return None
    return load_item_icon_map().get((folder, item_name.casefold()))


def is_legacy_myth_placeholder(path: Path, class_name: str, cfg: int) -> bool:
    """Reject old duplicated legendary images that were copied as mythic placeholders."""
    cfg = int(cfg or 0)
    placeholder_name = None
    placeholder_folder = CLASS_ICON_FOLDERS.get(class_name)

    if class_name == "Seer" and (3070901 <= cfg <= 3071009):
        placeholder_name = "T_UI_Icon_Equip_1216006.webp"

    if not placeholder_name or not placeholder_folder:
        return False

    reference = find_icon_path(placeholder_name, placeholder_folder)
    if reference is None:
        return False

    try:
        if path.resolve() == reference.resolve():
            return True
        return path.read_bytes() == reference.read_bytes()
    except OSError:
        return False


_ICON_PATH_INDEX: dict[str, list[Path]] | None = None
_ICON_PIXMAP_CACHE: dict[tuple[str, int], QPixmap] = {}


def _icon_roots() -> list[Path]:
    roots: list[Path] = []
    for root in (BUNDLED_ICONS_DIR, APP_ICONS_DIR):
        if root.exists() and root not in roots:
            roots.append(root)
    return roots


def rebuild_icon_index() -> None:
    """Индексирует PNG/WebP из icons/** и перечитывает icon_map.txt."""
    global _ICON_PATH_INDEX, _ICON_MAP_ITEM_FILES
    _ICON_MAP_ITEM_FILES = None
    index: dict[str, list[Path]] = {}
    for root in _icon_roots():
        for path in root.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in {".png", ".webp"}:
                continue
            index.setdefault(path.name.lower(), []).append(path)
    _ICON_PATH_INDEX = index
    _ICON_PIXMAP_CACHE.clear()


def find_icon_path(filename: str | None, preferred_folder: str | None = None) -> Path | None:
    if not filename:
        return None
    name = Path(str(filename)).name

    if preferred_folder:
        for root in _icon_roots():
            candidate = root / preferred_folder / name
            if candidate.exists():
                return candidate

    for root in _icon_roots():
        candidate = root / name
        if candidate.exists():
            return candidate

    global _ICON_PATH_INDEX
    if _ICON_PATH_INDEX is None:
        rebuild_icon_index()

    matches = (_ICON_PATH_INDEX or {}).get(name.lower(), [])
    return matches[0] if matches else None


def load_icon_pixmap(
    filename: str | None,
    physical_size: int,
    preferred_folder: str | None = None,
) -> QPixmap | None:
    path = find_icon_path(filename, preferred_folder)
    if path is None:
        return None

    logical_size = ui_px(physical_size)
    cache_key = (str(path), logical_size)
    cached = _ICON_PIXMAP_CACHE.get(cache_key)
    if cached is not None:
        return cached

    pixmap = QPixmap(str(path))
    if pixmap.isNull():
        return None

    pixmap = pixmap.scaled(
        logical_size,
        logical_size,
        Qt.KeepAspectRatio,
        Qt.SmoothTransformation,
    )
    _ICON_PIXMAP_CACHE[cache_key] = pixmap
    return pixmap


def ru_affix(name: str | None) -> str:
    if not name:
        return "—"
    return AFFIX_RU.get(name, name)


def clean_code(value: str) -> str:
    return "".join(value.strip().split())


def item_name_ru(item: dict[str, Any] | None, fallback: str = "—") -> str:
    if not item:
        return f"Предмет {fallback}" if fallback and fallback != "—" else "—"

    name = str(item.get("n", "") or "")
    if item.get("_missing_from_database"):
        try:
            cfg_text = str(item.get("id", fallback))
        except Exception:
            cfg_text = fallback
        return f"Неизвестный предмет из кодека · ID {cfg_text}"
    if name in ITEM_NAME_RU:
        return ITEM_NAME_RU[name]
    if name in ITEM_SPECIAL_RU:
        return ITEM_SPECIAL_RU[name]

    if name.startswith("Ceremonial "):
        ceremonial = {
            "Bracers": "Церемониальные наручи",
            "Breastplate": "Церемониальный нагрудник",
            "Breeches": "Церемониальные бриджи",
            "Helmet": "Церемониальный шлем",
            "Sabatons": "Церемониальные сабатоны",
        }
        suffix = name[len("Ceremonial "):]
        if suffix in ceremonial:
            return ceremonial[suffix]

    if name.startswith("Simple Leather "):
        simple = {
            "Boots": "Простые кожаные ботинки",
            "Bracers": "Простые кожаные наручи",
            "Eyepatch": "Простая кожаная повязка на глаз",
            "Pants": "Простые кожаные штаны",
            "Vest": "Простой кожаный жилет",
        }
        suffix = name[len("Simple Leather "):]
        if suffix in simple:
            return simple[suffix]

    if name.startswith("Training Apprentice "):
        suffix = name[len("Training Apprentice "):]
        noun = ITEM_SLOT_WORD_RU.get(suffix)
        if noun:
            return f"Учебные {noun.lower()} ученика"

    for prefix in sorted(ITEM_SET_PREFIX_RU, key=len, reverse=True):
        if not name.startswith(prefix + " "):
            continue
        suffix = name[len(prefix) + 1:]
        noun = ITEM_SLOT_WORD_RU.get(suffix)
        if noun:
            return f"{noun} {ITEM_SET_PREFIX_RU[prefix]}"

    # Не протаскиваем английское имя в русскую версию интерфейса.
    return f"Предмет {fallback}" if fallback and fallback != "—" else "Неизвестный предмет"


def item_lore_ru(item: dict[str, Any] | None) -> str:
    if not item:
        return ""
    return ITEM_LORE_RU.get(str(item.get("n", "") or ""), "")


def gem_name_ru(gem: dict[str, Any] | None, fallback: str = "—") -> str:
    if not gem:
        return f"Самоцвет {fallback}" if fallback and fallback != "—" else "—"

    name = str(gem.get("n", "") or "")
    if name in GEM_NAME_RU:
        return GEM_NAME_RU[name]

    gem_type = SOCKET_RU.get(int(gem.get("t", 0) or 0), "Самоцвет")
    affixes = [ru_affix(str(a)) for a in (gem.get("a") or [])]
    if affixes:
        return f"{gem_type}: " + " + ".join(affixes)
    return f"{gem_type} ранг {int(gem.get('l', 0) or 0)}"


def format_stat(key: str, value: Any) -> str:
    label = STAT_RU.get(key, key)
    if key in PERCENT_STATS and isinstance(value, (int, float)):
        number = float(value) * 100.0
        rendered = f"{number:.2f}".replace(".", ",").rstrip("0").rstrip(",")
        return f"{label}: {rendered}%"
    return f"{label}: {value}"




def ui_px(physical_pixels: int) -> int:
    """Keep important UI geometry close to the requested physical pixel size at 100–200% DPI."""
    screen = QApplication.primaryScreen()
    ratio = float(screen.devicePixelRatio()) if screen is not None else 1.0
    ratio = max(1.0, ratio)
    return max(1, int(round(float(physical_pixels) / ratio)))


def affix_icon_pixmap(name: str, physical_size: int = 42) -> QPixmap | None:
    return load_icon_pixmap(AFFIX_ICON_FILES.get(name), physical_size, "affixes")


def setup_affix_icon_label(label: QLabel, name: str, physical_size: int = 42) -> None:
    size = ui_px(physical_size)
    label.setFixedSize(size, size)
    label.setAlignment(Qt.AlignCenter)
    label.setStyleSheet(
        f"background: {affix_color(name)}; border: 1px solid #38424a; "
        "color: #eeeeea; font-weight: 700;"
    )
    pixmap = affix_icon_pixmap(name, physical_size)
    if pixmap is not None:
        label.setPixmap(pixmap)
        label.setText("")
    else:
        label.setPixmap(QPixmap())
        label.setText(affix_icon_text(name))


def gem_icon_pixmap(gem: dict[str, Any] | None, physical_size: int = 48) -> QPixmap | None:
    if not gem:
        return None
    return load_icon_pixmap(str(gem.get("ic", "") or ""), physical_size, "gem")


def make_gem_icon_label(gem: dict[str, Any], physical_size: int = 48) -> QLabel:
    label = QLabel()
    size = ui_px(physical_size)
    label.setFixedSize(size, size)
    label.setAlignment(Qt.AlignCenter)
    label.setStyleSheet("background: transparent; border: none;")
    pixmap = gem_icon_pixmap(gem, physical_size)
    if pixmap is not None:
        label.setPixmap(pixmap)
    return label


def make_gem_affix_icons(
    gem: dict[str, Any] | None,
    icon_size: int = 26,
    spacing: int = 4,
) -> QWidget:
    """
    Compact in-game-like attribute display for a gem.

    Rank-1 gems show one attribute icon.
    Mixed/rank-2 gems show both attribute icons next to each other instead
    of a long "Attribute A + Attribute B" text string.
    """
    host = QWidget()
    host.setObjectName("gemAffixIcons")

    row = QHBoxLayout(host)
    row.setContentsMargins(0, 0, 0, 0)
    row.setSpacing(ui_px(spacing))
    row.setAlignment(Qt.AlignCenter)

    attrs = [str(a) for a in ((gem or {}).get("a") or [])]
    if not attrs:
        host.setFixedHeight(ui_px(icon_size))
        return host

    for name in attrs:
        icon = QLabel()
        setup_affix_icon_label(icon, name, icon_size)
        icon.setToolTip(ru_affix(name))
        row.addWidget(icon)

    host.setFixedHeight(ui_px(icon_size))
    host.setMinimumWidth(
        ui_px(len(attrs) * icon_size + max(0, len(attrs) - 1) * spacing)
    )
    return host


def gem_short_type_text(gem: dict[str, Any] | None) -> str:
    if not gem:
        return "Самоцвет"
    gem_type = SOCKET_RU.get(
        int(gem.get("t", 0) or 0),
        "Самоцвет",
    )
    rank = int(gem.get("l", 0) or 0)
    return f"{gem_type} · ранг {rank}"


def translate_effect_text(value: str) -> str:
    """Compact RU translation for the numeric effect strings from the public data file."""
    if not value:
        return ""
    result = str(value)
    replacements = [
        ("Block Damage Reduction Rate", "Снижение урона при блоке"),
        ("Critical Damage Resistance", "Сопротивление критическому урону"),
        ("Defense Penetration", "Пробивание защиты"),
        ("Physical Damage", "Физический урон"),
        ("Magic Damage", "Магический урон"),
        ("Physical Resistance", "Физическое сопротивление"),
        ("Magic Resistance", "Магическое сопротивление"),
        ("Maximum Health", "Максимальное здоровье"),
        ("Maximum Energy", "Максимальная энергия"),
        ("Movement Speed", "Скорость передвижения"),
        ("Chanting Speed", "Скорость произнесения"),
        ("Skill Cooldown Speed", "Скорость перезарядки умений"),
        ("Charging Speed", "Скорость заряда"),
        ("Interaction Speed", "Скорость взаимодействия"),
        ("Dodge Energy Cost Reduction", "Снижение расхода энергии на уклонение"),
        ("Skill Energy Cost Reduction", "Снижение расхода энергии умений"),
        ("Block Energy Cost Reduction", "Снижение расхода энергии блока"),
        ("Fall Damage Resistance", "Сопротивление урону от падения"),
        ("Shield Strength", "Прочность щита"),
        ("Buff Duration", "Длительность положительных эффектов"),
        ("Debuff Duration", "Длительность отрицательных эффектов"),
        ("Execution Damage", "Урон казни"),
        ("Amount of Gyldenblod dropped", "Добыча золотой крови"),
        ("Recover Energy by", "Восстановление энергии"),
        ("Recover Health equal to", "Восстановление здоровья"),
        ("Attack", "Атака"),
        ("Defense", "Защита"),
        ("Healing", "Лечение"),
    ]
    for old, new in replacements:
        result = result.replace(old, new)
    result = result.replace(".", ",") if any(ch.isdigit() for ch in result) else result
    # Restore sentence separators that became commas only when they followed percent/numbers.
    result = re.sub(r"(%|\d),\s+", r"\1. ", result)
    return result


def affix_icon_text(name: str) -> str:
    symbols = {
        "Valor": "⚔", "Aegis": "◉", "Eloquence": "✦", "Creation": "✋",
        "Wrath": "✝", "Tenacious": "✚", "Seamless": "⌛", "Sky Piercer": "♨",
        "Bulwark": "◎", "Vitality": "♥", "Fervid": "✣", "Iron Helmet": "♜",
        "Swift": "➤", "Seeker": "➤", "Stoic": "◌", "Elusive": "↝",
        "Ranged": "➶", "Ethereal": "↯", "Sleight of Hand": "♙", "Fervor": "✹",
        "Brotherhood": "◒", "Blessing": "♙", "Smiting": "☼", "Spirit Shield": "⬡",
        "Curse": "♟", "Burst": "✺", "Unyielding": "✧", "Focused": "❯",
        "Strife": "⚒", "Distant Ward": "⬢", "Wealth": "★",
    }
    return symbols.get(name, "◆")


def affix_color(name: str) -> str:
    category = AFFIX_CATEGORY.get(name, "utility")
    return {
        "offense": "#5b292a",
        "defense": "#23364c",
        "utility": "#493523",
    }.get(category, "#493523")


def item_stats_text(item: dict[str, Any] | None, include_combat: bool = False) -> list[str]:
    if not item:
        return []
    stats = dict(item.get("at") or {})
    if not include_combat:
        stats.pop("combatValue", None)
    order = [
        "attack", "defence", "maxHealth", "physicalReduction", "magicalReduction",
        "criticalReduction", "physicalIncrease", "magicalIncrease", "blockRate", "combatValue",
    ]
    result = []
    for key in order:
        if key in stats:
            result.append(format_stat(key, stats.pop(key)))
    for key, value in stats.items():
        result.append(format_stat(key, value))
    return result


def affix_current_effect(database: "MistfallDatabase", name: str, level: int) -> str:
    details = AFFIX_DETAILS_RU.get(name)
    if details:
        effects = details.get("eff", [])
        if 1 <= level <= len(effects):
            return str(effects[level - 1])
    raw = database.data.get("affixes", {}).get(name, {})
    effects = raw.get("eff", []) if isinstance(raw, dict) else []
    if 1 <= level <= len(effects):
        return translate_effect_text(str(effects[level - 1]))
    return ""


def affix_description(database: "MistfallDatabase", name: str) -> str:
    details = AFFIX_DETAILS_RU.get(name)
    if details and details.get("desc"):
        return str(details["desc"])
    if name in AFFIX_DESC_RU:
        return AFFIX_DESC_RU[name]
    raw = database.data.get("affixes", {}).get(name, {})
    return str(raw.get("desc", "")) if isinstance(raw, dict) else ""


def load_json_file(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))



class BitWriter:
    """Пишет поля в том же LSB-first формате, который читает BitReader."""

    def __init__(self):
        self.octets: list[int] = []
        self.pos = 0

    def write(self, value: int, width: int) -> None:
        value = int(value)
        for bit in range(width):
            byte_index = self.pos >> 3
            if byte_index >= len(self.octets):
                self.octets.append(0)
            if (value >> bit) & 1:
                self.octets[byte_index] |= 1 << (self.pos & 7)
            self.pos += 1


def bytes_to_base62(octets: list[int]) -> str:
    if not octets:
        return "0"

    number = int.from_bytes(bytes(octets), byteorder="big", signed=False)
    if number == 0:
        return "0"

    chars: list[str] = []
    while number:
        number, remainder = divmod(number, 62)
        chars.append(B62[remainder])
    return "".join(reversed(chars))


class BitReader:
    def __init__(self, octets: list[int]):
        self.octets = octets
        self.pos = 0

    def read(self, width: int) -> int:
        value = 0
        for bit in range(width):
            byte_index = self.pos >> 3
            if byte_index >= len(self.octets):
                raise ValueError("Код обрезан: закончились данные")
            value |= ((self.octets[byte_index] >> (self.pos & 7)) & 1) << bit
            self.pos += 1
        return value


def base62_to_bytes(code: str) -> list[int]:
    code = clean_code(code)
    if not code:
        raise ValueError("Пустой код")

    number = 0
    for char in code:
        index = B62.find(char)
        if index < 0:
            raise ValueError(f"Недопустимый символ в Base62: {char!r}")
        number = number * 62 + index

    octets: list[int] = []
    while number > 0:
        octets.insert(0, number & 0xFF)
        number >>= 8
    return octets


@dataclass
class DecodedItem:
    slot: int
    cfg: int
    item: dict[str, Any] | None
    gem_ids: list[int]
    gems: list[dict[str, Any]]


def item_attribute_contribution(decoded_item: DecodedItem) -> Counter:
    """All affix stacks physically present on one item, including socketed gems."""
    result: Counter = Counter()
    item = decoded_item.item
    if item and item.get("i"):
        result[str(item["i"])] += 1
    for gem in decoded_item.gems:
        for affix in gem.get("a", []) or []:
            result[str(affix)] += 1
    return result


def calculate_build_attributes(
    items: list[DecodedItem],
    active_weapon_slot: int = DEFAULT_ACTIVE_WEAPON_SLOT,
) -> Counter:
    """
    Mistfall Hunter applies attributes from only ONE of the two weapon slots.
    Armor/accessories always count; weapon I or II counts according to active_weapon_slot.
    """
    result: Counter = Counter()
    for decoded_item in items:
        if decoded_item.slot in WEAPON_SLOTS and decoded_item.slot != active_weapon_slot:
            continue
        result.update(item_attribute_contribution(decoded_item))
    return result


@dataclass
class DecodedBuild:
    code: str
    class_id: int
    class_name: str
    items: list[DecodedItem]
    attributes: Counter
    active_weapon_slot: int = DEFAULT_ACTIVE_WEAPON_SLOT

    def attributes_for_weapon(self, weapon_slot: int) -> Counter:
        if weapon_slot not in WEAPON_SLOTS:
            weapon_slot = self.active_weapon_slot
        return calculate_build_attributes(self.items, weapon_slot)


class MistfallDatabase:
    def __init__(self, data: dict[str, Any]):
        self.data = data
        self.codec = data.get("codec", {})
        self.classes = data.get("classes", {})
        self.rarities = data.get("raretes", {})

        self.item_by_id: dict[int, dict[str, Any]] = {}
        for item_list in data.get("objets", {}).values():
            for item in item_list:
                try:
                    self.item_by_id[int(item["id"])] = item
                except (KeyError, TypeError, ValueError):
                    pass

        for cfg_id, override in ITEM_ID_OVERRIDES.items():
            self.item_by_id.setdefault(int(cfg_id), dict(override))

        self.gem_by_id: dict[int, dict[str, Any]] = {}
        for gem in data.get("gemmes", []):
            try:
                self.gem_by_id[int(gem["id"])] = gem
            except (KeyError, TypeError, ValueError):
                pass

    def decode(
        self,
        code: str,
        active_weapon_slot: int = DEFAULT_ACTIVE_WEAPON_SLOT,
    ) -> DecodedBuild:
        code = clean_code(code)
        reader = BitReader(base62_to_bytes(code))

        head = reader.read(24)
        expected_head = int(self.codec.get("head", -1))
        if head != expected_head:
            raise ValueError("Это не похоже на код сборки Mistfall Hunter: неверный заголовок")

        version = reader.read(10)
        expected_version = int(self.codec.get("version", -1))
        if version != expected_version:
            raise ValueError(f"Неизвестная версия кода: {version}; база ожидает {expected_version}")

        class_id = reader.read(4)
        per_class = self.codec.get("equipParClasseEtSlot", {}).get(str(class_id))
        if not per_class:
            raise ValueError(f"Неизвестный класс в коде: {class_id}")

        class_name = str(self.classes.get(str(class_id), f"Класс {class_id}"))

        gem_ids_table = self.codec.get("gemIds", [])
        holes_table = self.codec.get("trous", {})
        decoded_items: list[DecodedItem] = []

        for raw_slot in self.codec.get("slots", []):
            slot = int(raw_slot)
            options = per_class.get(str(slot), [0])
            item_index = reader.read(10)
            if item_index >= len(options):
                raise ValueError(
                    f"Индекс предмета {item_index} вне таблицы для слота {slot}. "
                    "Вероятно, база предметов устарела."
                )

            cfg = int(options[item_index] or 0)
            source_item = self.item_by_id.get(cfg) if cfg else None
            item = dict(source_item) if source_item else None
            if cfg and item is None:
                item = {
                    "id": str(cfg),
                    "n": f"Unknown codec item {cfg}",
                    "g": 0,
                    "s": [],
                    "i": None,
                    "aff": 0,
                    "ic": "",
                    "at": {},
                    "d": "",
                    "_missing_from_database": True,
                }
            if item is not None:
                item["_class_name"] = class_name
            current_gem_ids: list[int] = []
            current_gems: list[dict[str, Any]] = []

            if cfg:
                hole_count = int(holes_table.get(str(cfg), 0) or 0)
                for _ in range(hole_count):
                    gem_index = reader.read(10)
                    if gem_index >= len(gem_ids_table):
                        raise ValueError(f"Индекс камня {gem_index} вне таблицы")
                    gem_id = int(gem_ids_table[gem_index] or 0)
                    current_gem_ids.append(gem_id)
                    gem = self.gem_by_id.get(gem_id)
                    if gem:
                        current_gems.append(gem)

            decoded_items.append(
                DecodedItem(
                    slot=slot,
                    cfg=cfg,
                    item=item,
                    gem_ids=current_gem_ids,
                    gems=current_gems,
                )
            )

        # Код хранит ОБА альтернативных оружия, но не хранит, какое из них
        # сейчас выбрано в интерфейсе игры. Поэтому активный слот выбирается
        # пользователем в менеджере и хранится отдельно от Gear Code.
        if active_weapon_slot not in WEAPON_SLOTS:
            active_weapon_slot = DEFAULT_ACTIVE_WEAPON_SLOT
        attributes = calculate_build_attributes(decoded_items, active_weapon_slot)

        return DecodedBuild(
            code=code,
            class_id=class_id,
            class_name=class_name,
            items=decoded_items,
            attributes=attributes,
            active_weapon_slot=active_weapon_slot,
        )

    def class_id_for_name(self, class_name: str) -> int:
        for raw_id, raw_name in self.classes.items():
            if str(raw_name) == class_name:
                return int(raw_id)
        raise ValueError(f"Неизвестный класс: {class_name}")

    def class_slot_items(self, class_name: str, slot: int) -> list[dict[str, Any]]:
        """Реальные варианты предметов, которые кодек допускает в этом слоте."""
        class_id = self.class_id_for_name(class_name)
        per_class = self.codec.get("equipParClasseEtSlot", {}).get(str(class_id), {})
        options = per_class.get(str(slot), [])

        result: list[dict[str, Any]] = []
        seen: set[int] = set()
        for raw_cfg in options:
            cfg = int(raw_cfg or 0)
            if not cfg or cfg in seen:
                continue
            seen.add(cfg)
            source = self.item_by_id.get(cfg)
            if not source:
                continue
            item = dict(source)
            item["_class_name"] = class_name
            result.append(item)
        return result

    def compatible_gems(self, socket_type: int, socket_level: int) -> list[dict[str, Any]]:
        allowed_ids = {
            int(raw or 0)
            for raw in self.codec.get("gemIds", [])
            if int(raw or 0)
        }
        result: list[dict[str, Any]] = []
        for gem_id, gem in self.gem_by_id.items():
            if gem_id not in allowed_ids:
                continue
            gem_type = int(gem.get("t", 0) or 0)
            gem_level = int(gem.get("l", 0) or 0)
            if socket_type != -1 and gem_type != socket_type:
                continue
            if gem_level > socket_level:
                continue
            result.append(gem)

        result.sort(
            key=lambda gem: (
                -int(gem.get("l", 0) or 0),
                " + ".join(ru_affix(str(a)) for a in (gem.get("a") or [])),
                str(gem.get("n", "")),
            )
        )
        return result

    def _auto_slot_candidates(
        self,
        class_name: str,
        slot: int,
        targets: dict[str, int],
        rarity_grade: int | None = None,
    ) -> list[dict[str, Any]]:
        """
        Candidate loadouts for one slot.

        Each candidate contains a real item + real compatible gems.
        Target vectors are clamped to requested levels so the state space
        stays small enough for instant-ish automatic selection.
        """
        names = list(targets)
        caps = tuple(max(0, min(int(targets[name]), 7)) for name in names)
        name_index = {name: index for index, name in enumerate(names)}

        best_by_vector: dict[tuple[int, ...], dict[str, Any]] = {}

        for item in self.class_slot_items(class_name, slot):
            cfg = int(item.get("id", 0) or 0)
            if not cfg:
                continue

            grade = int(item.get("g", 0) or 0)
            if rarity_grade is not None and grade != int(rarity_grade):
                continue

            base = [0] * len(names)
            off_target = 0
            innate = str(item.get("i", "") or "")
            if innate:
                if innate in name_index:
                    base[name_index[innate]] += 1
                else:
                    off_target += 1

            start_vector = tuple(
                min(caps[index], base[index])
                for index in range(len(names))
            )
            states: dict[tuple[int, ...], tuple[list[int], int]] = {
                start_vector: ([], off_target)
            }

            for socket in list(item.get("s") or []):
                try:
                    socket_type = int(socket[0])
                    socket_level = int(socket[1])
                except Exception:
                    socket_type = 0
                    socket_level = 0

                # For a target-vector-equivalent gem, keep the cleanest one.
                gem_options: dict[
                    tuple[int, ...],
                    tuple[int, int, int],
                ] = {
                    tuple([0] * len(names)): (0, 0, 0)
                }

                for gem in self.compatible_gems(socket_type, socket_level):
                    vector = [0] * len(names)
                    gem_off_target = 0
                    for affix in gem.get("a", []) or []:
                        affix_name = str(affix)
                        if affix_name in name_index:
                            vector[name_index[affix_name]] += 1
                        else:
                            gem_off_target += 1

                    vector_tuple = tuple(vector)
                    gem_id = int(gem.get("id", 0) or 0)
                    gem_rank = int(gem.get("l", 0) or 0)

                    previous = gem_options.get(vector_tuple)
                    current_score = (gem_off_target, -gem_rank, gem_id)
                    if (
                        previous is None
                        or current_score
                        < (previous[1], -previous[2], previous[0])
                    ):
                        gem_options[vector_tuple] = (
                            gem_id,
                            gem_off_target,
                            gem_rank,
                        )

                next_states: dict[
                    tuple[int, ...],
                    tuple[list[int], int],
                ] = {}

                for state_vector, (gem_ids, state_off) in states.items():
                    for gem_vector, (
                        gem_id,
                        gem_off,
                        _gem_rank,
                    ) in gem_options.items():
                        next_vector = tuple(
                            min(
                                caps[index],
                                state_vector[index] + gem_vector[index],
                            )
                            for index in range(len(names))
                        )
                        next_value = (
                            gem_ids + [gem_id],
                            state_off + gem_off,
                        )

                        previous = next_states.get(next_vector)
                        if (
                            previous is None
                            or next_value[1] < previous[1]
                        ):
                            next_states[next_vector] = next_value

                states = next_states

            for vector, (gem_ids, candidate_off) in states.items():
                candidate = {
                    "cfg": cfg,
                    "gems": gem_ids,
                    "vector": vector,
                    "off_target": candidate_off,
                    "grade": grade,
                }

                previous = best_by_vector.get(vector)
                if previous is None:
                    best_by_vector[vector] = candidate
                    continue

                # Prefer fewer unrelated affixes, then higher rarity.
                current_score = (
                    candidate_off,
                    -grade,
                    cfg,
                )
                previous_score = (
                    int(previous["off_target"]),
                    -int(previous["grade"]),
                    int(previous["cfg"]),
                )
                if current_score < previous_score:
                    best_by_vector[vector] = candidate

        return list(best_by_vector.values())

    def auto_build_for_attributes(
        self,
        class_name: str,
        targets: dict[str, int],
        active_weapon_slot: int = DEFAULT_ACTIVE_WEAPON_SLOT,
        include_second_weapon: bool = False,
        rarity_grade: int | None = 6,
    ) -> dict[str, Any]:
        """
        Build a complete equipment set that reaches requested affix levels.

        All seven armor/accessory slots and the active weapon are filled.
        The inactive weapon stays EMPTY by default, matching the requested
        creator behavior. It is filled only when include_second_weapon=True.
        """
        cleaned_targets = {
            str(name): max(1, min(int(level), 7))
            for name, level in targets.items()
            if str(name) and int(level) > 0
        }
        if not cleaned_targets:
            raise ValueError("Добавь хотя бы один желаемый атрибут")

        if active_weapon_slot not in WEAPON_SLOTS:
            active_weapon_slot = DEFAULT_ACTIVE_WEAPON_SLOT

        if rarity_grade is not None:
            rarity_grade = int(rarity_grade)
            if rarity_grade not in (3, 4, 5, 6):
                raise ValueError(
                    "Для автоподбора выбери редкость от Редкой до Легендарной"
                )

        names = list(cleaned_targets)
        target_vector = tuple(cleaned_targets[name] for name in names)
        zero_vector = tuple(0 for _ in names)

        active_slots = [
            0, 1, 2, 3, 4, 5, 6,
            active_weapon_slot,
        ]

        # state -> (off_target, grade_sum, slot_cfg, slot_gems)
        states: dict[
            tuple[int, ...],
            tuple[int, int, dict[int, int], dict[int, list[int]]],
        ] = {
            zero_vector: (0, 0, {}, {})
        }

        beam_limit = 4500

        for slot in active_slots:
            candidates = self._auto_slot_candidates(
                class_name,
                slot,
                cleaned_targets,
                rarity_grade,
            )
            if not candidates:
                rarity_text = (
                    self.rarity_name(rarity_grade)
                    if rarity_grade is not None
                    else "выбранной редкости"
                )
                raise ValueError(
                    f"Нет предметов редкости «{rarity_text}» "
                    f"для слота «{SLOT_RU.get(slot, slot)}»"
                )

            next_states: dict[
                tuple[int, ...],
                tuple[int, int, dict[int, int], dict[int, list[int]]],
            ] = {}

            for state_vector, (
                state_off,
                state_grade,
                state_cfg,
                state_gems,
            ) in states.items():
                for candidate in candidates:
                    vector = candidate["vector"]
                    next_vector = tuple(
                        min(
                            target_vector[index],
                            state_vector[index] + vector[index],
                        )
                        for index in range(len(names))
                    )

                    next_value = (
                        state_off + int(candidate["off_target"]),
                        state_grade + int(candidate["grade"]),
                        {
                            **state_cfg,
                            slot: int(candidate["cfg"]),
                        },
                        {
                            **state_gems,
                            slot: list(candidate["gems"]),
                        },
                    )

                    previous = next_states.get(next_vector)
                    if previous is None:
                        next_states[next_vector] = next_value
                        continue

                    # Same achieved target vector:
                    # cleaner build first, then higher total rarity.
                    if (
                        next_value[0],
                        -next_value[1],
                    ) < (
                        previous[0],
                        -previous[1],
                    ):
                        next_states[next_vector] = next_value

            # Keep the solver responsive even for many simultaneous targets.
            if len(next_states) > beam_limit:
                ranked = sorted(
                    next_states.items(),
                    key=lambda pair: (
                        sum(
                            target_vector[index] - pair[0][index]
                            for index in range(len(names))
                        ),
                        pair[1][0],
                        -pair[1][1],
                    ),
                )
                next_states = dict(ranked[:beam_limit])

            states = next_states

        if target_vector in states:
            best_vector = target_vector
            exact = True
        else:
            best_vector = min(
                states,
                key=lambda vector: (
                    sum(
                        target_vector[index] - vector[index]
                        for index in range(len(names))
                    ),
                    states[vector][0],
                    -states[vector][1],
                ),
            )
            exact = False

        off_target, grade_sum, slot_cfg, slot_gems = states[best_vector]

        # Inactive weapon is optional. By default it remains completely empty.
        inactive_weapon = 11 if active_weapon_slot == 10 else 10
        slot_cfg[inactive_weapon] = 0
        slot_gems[inactive_weapon] = []

        if include_second_weapon:
            inactive_items = self.class_slot_items(
                class_name,
                inactive_weapon,
            )
            if rarity_grade is not None:
                inactive_items = [
                    item for item in inactive_items
                    if int(item.get("g", 0) or 0) == int(rarity_grade)
                ]
            if inactive_items:
                filler = max(
                    inactive_items,
                    key=lambda item: (
                        int(item.get("g", 0) or 0),
                        len(item.get("s") or []),
                    ),
                )
                slot_cfg[inactive_weapon] = int(filler.get("id", 0) or 0)

        return {
            "slot_cfg": slot_cfg,
            "slot_gems": slot_gems,
            "requested": dict(cleaned_targets),
            "achieved_vector": best_vector,
            "target_names": names,
            "exact": exact,
            "off_target": off_target,
            "grade_sum": grade_sum,
            "rarity_grade": rarity_grade,
        }

    def encode(
        self,
        class_name: str,
        slot_cfg: dict[int, int],
        slot_gems: dict[int, list[int]] | None = None,
    ) -> str:
        """
        Создаёт настоящий Gear Code Mistfall Hunter.

        В код попадают только cfgId предметов и индексы самоцветов из
        codec-таблиц. Поэтому генератор не создаёт невозможные комбинации:
        UI предлагает только реальные варианты из базы игры.
        """
        slot_gems = slot_gems or {}
        class_id = self.class_id_for_name(class_name)

        per_class = self.codec.get("equipParClasseEtSlot", {}).get(str(class_id))
        if not per_class:
            raise ValueError(f"Для класса {class_name} нет таблицы кодека")

        gem_ids_table = [int(raw or 0) for raw in self.codec.get("gemIds", [])]
        gem_index: dict[int, int] = {}
        for index, gem_id in enumerate(gem_ids_table):
            gem_index.setdefault(gem_id, index)

        if 0 not in gem_index:
            raise ValueError("В codec.gemIds отсутствует пустой самоцвет (0)")

        writer = BitWriter()
        writer.write(int(self.codec.get("head", 0)), 24)
        writer.write(int(self.codec.get("version", 0)), 10)
        writer.write(class_id, 4)

        holes_table = self.codec.get("trous", {})

        for raw_slot in self.codec.get("slots", []):
            slot = int(raw_slot)
            options = [int(raw or 0) for raw in per_class.get(str(slot), [0])]
            cfg = int(slot_cfg.get(slot, 0) or 0)

            try:
                item_index = options.index(cfg)
            except ValueError as exc:
                raise ValueError(
                    f"Предмет ID {cfg} нельзя установить в слот "
                    f"«{SLOT_RU.get(slot, slot)}» класса "
                    f"«{CLASS_RU.get(class_name, class_name)}»"
                ) from exc

            writer.write(item_index, 10)

            if not cfg:
                continue

            hole_count = int(holes_table.get(str(cfg), 0) or 0)
            selected_gems = list(slot_gems.get(slot, []))

            for hole_index in range(hole_count):
                gem_id = int(
                    selected_gems[hole_index]
                    if hole_index < len(selected_gems)
                    else 0
                )
                if gem_id not in gem_index:
                    raise ValueError(f"Самоцвет ID {gem_id} отсутствует в кодеке")
                writer.write(gem_index[gem_id], 10)

        return bytes_to_base62(writer.octets)

    def rarity_name(self, grade: int) -> str:
        return RARITY_RU.get(grade, str(self.rarities.get(str(grade), grade)))


class DatabaseDownloadThread(QThread):
    loaded = Signal(dict, str)
    failed = Signal(str)

    def run(self) -> None:
        errors: list[str] = []
        for url in DATA_URLS:
            try:
                request = urllib.request.Request(
                    url,
                    headers={
                        "User-Agent": "MistfallBuildManager/4.1 (+PySide6)",
                        "Accept": "application/json,text/plain,*/*",
                    },
                )
                with urllib.request.urlopen(request, timeout=20) as response:
                    raw = response.read()
                data = json.loads(raw.decode("utf-8-sig"))
                if not isinstance(data, dict) or "codec" not in data:
                    raise ValueError("сервер вернул файл без codec")
                self.loaded.emit(data, url)
                return
            except Exception as exc:
                errors.append(f"{url}: {exc}")
        self.failed.emit("\n".join(errors))


class BuildRepository:
    def __init__(self, path: Path):
        self.path = path
        self.builds: list[dict[str, Any]] = []
        self.load()

    def load(self) -> None:
        if not self.path.exists():
            self.builds = []
            return
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            if not isinstance(raw, list):
                raise ValueError("корень builds.json должен быть списком")
            result: list[dict[str, Any]] = []
            for row in raw:
                if not isinstance(row, dict):
                    continue
                code = clean_code(str(row.get("code", "")))
                if not code:
                    continue
                try:
                    weapon_slot = int(row.get("weapon_slot", DEFAULT_ACTIVE_WEAPON_SLOT) or DEFAULT_ACTIVE_WEAPON_SLOT)
                except (TypeError, ValueError):
                    weapon_slot = DEFAULT_ACTIVE_WEAPON_SLOT
                if weapon_slot not in WEAPON_SLOTS:
                    weapon_slot = DEFAULT_ACTIVE_WEAPON_SLOT
                result.append({
                    "name": str(row.get("name", "Без названия")).strip() or "Без названия",
                    "code": code,
                    "weapon_slot": weapon_slot,
                    "class_name": str(row.get("class_name", "") or "").strip(),
                })
            self.builds = result
        except Exception:
            self.builds = []

    def save(self) -> None:
        self.path.write_text(
            json.dumps(self.builds, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def add(
        self,
        name: str,
        code: str,
        weapon_slot: int = DEFAULT_ACTIVE_WEAPON_SLOT,
        class_name: str = "",
    ) -> None:
        if weapon_slot not in WEAPON_SLOTS:
            weapon_slot = DEFAULT_ACTIVE_WEAPON_SLOT
        self.builds.append({
            "name": name.strip() or "Без названия",
            "code": clean_code(code),
            "weapon_slot": weapon_slot,
            "class_name": str(class_name or "").strip(),
        })
        self.save()

    def update(
        self,
        index: int,
        name: str,
        code: str,
        class_name: str | None = None,
        weapon_slot: int | None = None,
    ) -> None:
        old_weapon_slot = int(
            self.builds[index].get(
                "weapon_slot",
                DEFAULT_ACTIVE_WEAPON_SLOT,
            )
        )
        if weapon_slot is None:
            weapon_slot = old_weapon_slot
        if weapon_slot not in WEAPON_SLOTS:
            weapon_slot = DEFAULT_ACTIVE_WEAPON_SLOT

        old_class = str(
            self.builds[index].get("class_name", "") or ""
        )
        self.builds[index] = {
            "name": name.strip() or "Без названия",
            "code": clean_code(code),
            "weapon_slot": weapon_slot,
            "class_name": (
                old_class
                if class_name is None
                else str(class_name or "").strip()
            ),
        }
        self.save()

    def set_class_name(self, index: int, class_name: str) -> None:
        if not 0 <= index < len(self.builds):
            return
        self.builds[index]["class_name"] = str(class_name or "").strip()
        self.save()

    def set_weapon_slot(self, index: int, weapon_slot: int) -> None:
        if weapon_slot not in WEAPON_SLOTS:
            return
        self.builds[index]["weapon_slot"] = weapon_slot
        self.save()

    def delete(self, index: int) -> None:
        del self.builds[index]
        self.save()



class ClassSelectPage(QWidget):
    """Встроенная страница выбора класса — без отдельного окна."""

    class_selected = Signal(str)

    CLASS_ORDER = [
        "Mercenary",
        "Sorcerer",
        "Blackarrow",
        "Shadowstrix",
        "Seer",
        "Withered Knight",
    ]

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.repo: BuildRepository | None = None
        self.current_class: str | None = None
        self.buttons: dict[str, QPushButton] = {}

        outer = QVBoxLayout(self)
        outer.setContentsMargins(
            ui_px(120), ui_px(34), ui_px(120), ui_px(28)
        )
        outer.setSpacing(ui_px(12))
        outer.addStretch(1)

        panel = QFrame()
        panel.setObjectName("classSelectPanel")
        panel.setMaximumWidth(ui_px(820))

        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(
            ui_px(30), ui_px(26), ui_px(30), ui_px(24)
        )
        panel_layout.setSpacing(ui_px(12))

        title = QLabel("Выберите класс")
        title.setObjectName("classSelectTitle")
        title.setAlignment(Qt.AlignCenter)
        panel_layout.addWidget(title)

        subtitle = QLabel(
            "Сохранённые сборки разделены по классам. "
            "Выберите персонажа, чтобы открыть его сборки."
        )
        subtitle.setObjectName("classSelectSubtitle")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setWordWrap(True)
        panel_layout.addWidget(subtitle)

        grid = QGridLayout()
        grid.setContentsMargins(0, ui_px(14), 0, 0)
        grid.setHorizontalSpacing(ui_px(10))
        grid.setVerticalSpacing(ui_px(10))

        for index, class_name in enumerate(self.CLASS_ORDER):
            button = QPushButton()
            button.setObjectName("classSelectButton")
            button.setMinimumHeight(ui_px(88))
            button.setCursor(Qt.PointingHandCursor)
            button.clicked.connect(
                lambda _checked=False, c=class_name: self.class_selected.emit(c)
            )
            self.buttons[class_name] = button
            grid.addWidget(button, index // 2, index % 2)

        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        panel_layout.addLayout(grid)

        hint = QLabel("Класс можно сменить в любой момент.")
        hint.setObjectName("muted")
        hint.setAlignment(Qt.AlignCenter)
        panel_layout.addWidget(hint)

        center_row = QHBoxLayout()
        center_row.addStretch(1)
        center_row.addWidget(panel, 1)
        center_row.addStretch(1)
        outer.addLayout(center_row)
        outer.addStretch(2)

    def set_state(
        self,
        repo: BuildRepository,
        current_class: str | None = None,
    ) -> None:
        self.repo = repo
        self.current_class = current_class

        counts = Counter(
            str(build.get("class_name", "") or "")
            for build in repo.builds
            if build.get("class_name")
        )

        for class_name, button in self.buttons.items():
            ru_name = CLASS_RU.get(class_name, class_name)
            count = counts.get(class_name, 0)
            if count == 1:
                suffix = "сборка"
            elif 2 <= count <= 4:
                suffix = "сборки"
            else:
                suffix = "сборок"
            button.setText(f"{ru_name}\n{count} {suffix}")
            button.setProperty("selected", current_class == class_name)
            button.style().unpolish(button)
            button.style().polish(button)
            button.update()


class AccentLine(QWidget):
    """
    Smooth animated Mistfall-style title ornament.

    The animation is intentionally restrained: several symmetrical gold
    threads weave around a stable centre line.  The shape slowly opens,
    crosses and closes, matching the title decoration seen in Mistfall.
    """

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)

        self._phase = 0.0

        self.setFixedHeight(ui_px(52))
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)

        self._timer = QTimer(self)
        self._timer.setInterval(33)
        self._timer.timeout.connect(self._advance_animation)
        self._timer.start()

    def _advance_animation(self) -> None:
        self._phase = (self._phase + 0.017) % math.tau
        self.update()

    @staticmethod
    def _glow_path(
        painter: QPainter,
        path: QPainterPath,
        core: QColor,
        glow: QColor,
        core_width: float = 1.25,
    ) -> None:
        for width, alpha in (
            (7.0, 18),
            (4.5, 34),
            (2.7, 58),
        ):
            c = QColor(glow)
            c.setAlpha(alpha)
            painter.setPen(
                QPen(
                    c,
                    max(1.0, ui_px(width)),
                    Qt.SolidLine,
                    Qt.RoundCap,
                    Qt.RoundJoin,
                )
            )
            painter.setBrush(Qt.NoBrush)
            painter.drawPath(path)

        painter.setPen(
            QPen(
                core,
                max(1.0, ui_px(core_width)),
                Qt.SolidLine,
                Qt.RoundCap,
                Qt.RoundJoin,
            )
        )
        painter.setBrush(Qt.NoBrush)
        painter.drawPath(path)

    @staticmethod
    def _thread_path(
        cx: float,
        cy: float,
        half_span: float,
        amp: float,
        phase: float,
        invert: bool = False,
        short: bool = False,
    ) -> QPainterPath:
        sign = -1.0 if invert else 1.0
        span = half_span * (0.73 if short else 1.0)
        x0 = cx - span
        x1 = cx + span
        xm = cx

        # Smooth phase-driven deformation.  The endpoints always stay on
        # the central line while the middle opens into a woven knot.
        a = amp * (0.72 + 0.28 * math.sin(phase + 0.55))
        b = amp * (0.68 + 0.32 * math.cos(phase * 1.15 - 0.2))
        drift = amp * 0.20 * math.sin(phase * 0.7)

        path = QPainterPath()
        path.moveTo(x0, cy)

        path.cubicTo(
            cx - span * 0.80,
            cy - sign * a * 0.30,
            cx - span * 0.53,
            cy - sign * a,
            cx - span * 0.28,
            cy - sign * b * 0.62 + drift,
        )
        path.cubicTo(
            cx - span * 0.12,
            cy + sign * b * 0.92,
            cx - span * 0.05,
            cy + sign * a * 0.48,
            xm,
            cy,
        )
        path.cubicTo(
            cx + span * 0.05,
            cy - sign * a * 0.48,
            cx + span * 0.12,
            cy - sign * b * 0.92,
            cx + span * 0.28,
            cy + sign * b * 0.62 - drift,
        )
        path.cubicTo(
            cx + span * 0.53,
            cy + sign * a,
            cx + span * 0.80,
            cy + sign * a * 0.30,
            x1,
            cy,
        )
        return path

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)

        w = self.width()
        h = self.height()

        cx = w * 0.5
        cy = h * 0.48

        # The screenshots show a stable long divider with a brighter,
        # animated central knot.
        baseline = QColor("#7a4d0e")
        baseline.setAlpha(120)
        painter.setPen(
            QPen(
                baseline,
                max(1.0, ui_px(1.0)),
                Qt.SolidLine,
                Qt.RoundCap,
            )
        )
        painter.drawLine(0, round(cy), w, round(cy))

        breathe = 0.5 + 0.5 * math.sin(self._phase)
        half_span = ui_px(248 + 34 * breathe)
        amp = ui_px(12.5 + 3.4 * (1.0 - breathe))

        # Subtle warm glow beneath the whole knot.
        glow_line = QColor("#d88b13")
        glow_line.setAlpha(54)
        painter.setPen(
            QPen(
                glow_line,
                max(1.0, ui_px(3.0)),
                Qt.SolidLine,
                Qt.RoundCap,
            )
        )
        painter.drawLine(
            round(cx - half_span * 0.96),
            round(cy),
            round(cx + half_span * 0.96),
            round(cy),
        )

        p1 = self._thread_path(
            cx, cy, half_span, amp, self._phase, False, False
        )
        p2 = self._thread_path(
            cx, cy, half_span, amp, self._phase + 1.18, True, False
        )
        p3 = self._thread_path(
            cx, cy, half_span, amp * 0.72, -self._phase * 0.82 + 0.7, False, True
        )
        p4 = self._thread_path(
            cx, cy, half_span, amp * 0.58, self._phase * 0.63 + 2.05, True, True
        )

        self._glow_path(
            painter,
            p1,
            QColor("#f2ad28"),
            QColor("#dd8510"),
            1.30,
        )
        self._glow_path(
            painter,
            p2,
            QColor("#ffc243"),
            QColor("#e08a0f"),
            1.12,
        )

        c3 = QColor("#ffd36a")
        c3.setAlpha(175)
        self._glow_path(
            painter,
            p3,
            c3,
            QColor("#d77f0c"),
            0.88,
        )
        c4 = QColor("#e9a42d")
        c4.setAlpha(150)
        self._glow_path(
            painter,
            p4,
            c4,
            QColor("#c36f08"),
            0.72,
        )

        # Tiny, sparse dust — deliberately not noisy.
        for i in range(14):
            seed = 0.73 + i * 1.47
            pulse = 0.5 + 0.5 * math.sin(
                self._phase * 1.8 + seed
            )
            if pulse < 0.50:
                continue

            x = cx + math.sin(seed * 2.1 + self._phase * 0.45) * half_span * 0.48
            y = cy + math.cos(seed * 1.7 - self._phase * 0.58) * ui_px(10)

            sparkle = QColor("#ffc24a")
            sparkle.setAlpha(int(28 + pulse * 90))
            painter.setPen(Qt.NoPen)
            painter.setBrush(sparkle)
            r = max(1, round(ui_px(0.7 + pulse * 0.45)))
            painter.drawEllipse(QPoint(round(x), round(y)), r, r)

        # Central diamond.
        pulse = 0.5 + 0.5 * math.sin(self._phase * 1.6)
        r = ui_px(2.2 + pulse * 0.7)
        diamond = QPolygon(
            [
                QPoint(round(cx), round(cy - r)),
                QPoint(round(cx + r), round(cy)),
                QPoint(round(cx), round(cy + r)),
                QPoint(round(cx - r), round(cy)),
            ]
        )
        painter.setPen(
            QPen(
                QColor("#ffd66b"),
                max(1.0, ui_px(0.8)),
            )
        )
        fill = QColor("#eaa22d")
        fill.setAlpha(170)
        painter.setBrush(fill)
        painter.drawPolygon(diamond)

        painter.end()



class SegmentedAttributeBar(QWidget):
    def __init__(
        self,
        level: int,
        parent: QWidget | None = None,
        compact: bool = False,
    ):
        super().__init__(parent)
        self.level = max(0, min(int(level), 7))

        self.segment_count = 7
        self.segment_width = ui_px(14 if compact else 16)
        self.segment_gap = ui_px(2)
        self.segment_height = ui_px(8 if compact else 10)

        total_width = (
            self.segment_count * self.segment_width
            + (self.segment_count - 1) * self.segment_gap
        )
        self.setFixedSize(total_width, self.segment_height)

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, False)
        painter.setPen(Qt.NoPen)

        active = QColor("#a87835")
        inactive = QColor("#343735")

        for index in range(self.segment_count):
            x = index * (self.segment_width + self.segment_gap)
            painter.fillRect(
                x,
                0,
                self.segment_width,
                self.segment_height,
                active if index < self.level else inactive,
            )

        painter.end()


class AttributeHoverPopup(QFrame):
    """Большая карточка атрибута, показываемая при наведении."""

    def __init__(
        self,
        name: str,
        level: int,
        database: MistfallDatabase,
    ):
        super().__init__(None, Qt.ToolTip)
        self.name = name
        self.level = max(1, min(int(level), 7))
        self.database = database

        self.setObjectName("attributeHoverPopup")
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self.setFixedWidth(ui_px(500))

        root = QVBoxLayout(self)
        root.setContentsMargins(
            ui_px(18), ui_px(16), ui_px(18), ui_px(18)
        )
        root.setSpacing(ui_px(8))

        # Header
        header = QHBoxLayout()
        header.setSpacing(ui_px(12))

        icon = QLabel()
        setup_affix_icon_label(icon, name, 72)
        header.addWidget(icon, 0, Qt.AlignTop)

        title_box = QVBoxLayout()
        title_box.setSpacing(ui_px(2))

        title = QLabel(ru_affix(name))
        title.setObjectName("attributePopupTitle")
        title.setWordWrap(True)
        title_box.addWidget(title)

        current = QLabel(f"Текущий уровень: Lv.{self.level}")
        current.setObjectName("attributePopupCurrent")
        title_box.addWidget(current)

        header.addLayout(title_box, 1)
        root.addLayout(header)

        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setObjectName("attributePopupSeparator")
        root.addWidget(separator)

        effect_title = QLabel("Эффект")
        effect_title.setObjectName("attributePopupSection")
        root.addWidget(effect_title)

        description = QLabel(affix_description(database, name))
        description.setObjectName("attributePopupDescription")
        description.setWordWrap(True)
        root.addWidget(description)

        separator2 = QFrame()
        separator2.setFrameShape(QFrame.HLine)
        separator2.setObjectName("attributePopupSeparator")
        root.addWidget(separator2)

        levels_title = QLabel("Уровень атрибута")
        levels_title.setObjectName("attributePopupSection")
        root.addWidget(levels_title)

        raw = database.data.get("affixes", {}).get(name, {})
        cap = 7
        if isinstance(raw, dict):
            try:
                cap = max(1, min(int(raw.get("cap", 7) or 7), 7))
            except Exception:
                cap = 7

        for current_level in range(1, cap + 1):
            row = QFrame()
            row.setObjectName(
                "attributePopupLevelActive"
                if current_level == self.level
                else "attributePopupLevel"
            )

            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(
                ui_px(5), ui_px(4), ui_px(5), ui_px(4)
            )
            row_layout.setSpacing(ui_px(10))

            level_label = QLabel(f"Ур. {current_level}")
            level_label.setObjectName(
                "attributePopupLevelNumberActive"
                if current_level == self.level
                else "attributePopupLevelNumber"
            )
            level_label.setFixedWidth(ui_px(52))
            level_label.setAlignment(Qt.AlignTop | Qt.AlignLeft)
            row_layout.addWidget(level_label)

            effect = affix_current_effect(database, name, current_level)
            if not effect:
                effect = "Описание уровня отсутствует."

            effect_label = QLabel(effect)
            effect_label.setObjectName(
                "attributePopupEffectActive"
                if current_level == self.level
                else "attributePopupEffect"
            )
            effect_label.setWordWrap(True)
            row_layout.addWidget(effect_label, 1)

            root.addWidget(row)

        self.adjustSize()




class AttributeRow(QFrame):
    def __init__(
        self,
        name: str,
        level: int,
        database: MistfallDatabase | None = None,
        compact: bool = False,
    ):
        super().__init__()
        self.name = name
        self.level = level
        self.database = database
        self.compact = compact
        self._hover_popup: AttributeHoverPopup | None = None

        self.setObjectName("attributeRow")
        self.setFixedHeight(ui_px(56 if compact else 62))
        self.setCursor(
            Qt.PointingHandCursor if database is not None else Qt.ArrowCursor
        )

        layout = QHBoxLayout(self)
        layout.setContentsMargins(
            0,
            0 if compact else ui_px(2),
            0,
            0 if compact else ui_px(2),
        )
        layout.setSpacing(ui_px(8))

        icon = QLabel()
        icon.setObjectName("affixIcon")
        setup_affix_icon_label(icon, name, 52 if compact else 56)
        layout.addWidget(icon)

        middle = QVBoxLayout()
        middle.setContentsMargins(0, 0, 0, 0)
        middle.setSpacing(ui_px(3))

        title = QLabel(ru_affix(name))
        title.setObjectName("attributeName")
        title.setWordWrap(False)
        middle.addWidget(title)

        middle.addWidget(SegmentedAttributeBar(level, compact=compact))
        layout.addLayout(middle, 1)

        value = QLabel(f"Lv.{level}")
        value.setObjectName("attributeLevel")
        value.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        value.setFixedWidth(ui_px(44))
        layout.addWidget(value)

    def enterEvent(self, event) -> None:  # noqa: N802
        if self.database is not None:
            self._show_hover_popup()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:  # noqa: N802
        self._hide_hover_popup()
        super().leaveEvent(event)

    def _show_hover_popup(self) -> None:
        self._hide_hover_popup()
        if self.database is None:
            return

        popup = AttributeHoverPopup(
            self.name,
            self.level,
            self.database,
        )
        popup.adjustSize()

        center = self.mapToGlobal(self.rect().center())
        screen = QApplication.screenAt(center)
        if screen is None:
            screen = QApplication.primaryScreen()
        if screen is None:
            return

        geometry = screen.availableGeometry()

        right_pos = self.mapToGlobal(
            QPoint(self.width() + ui_px(10), -ui_px(6))
        )
        left_pos = self.mapToGlobal(
            QPoint(-popup.width() - ui_px(10), -ui_px(6))
        )

        x = right_pos.x()
        if x + popup.width() > geometry.right():
            x = left_pos.x()

        x = max(
            geometry.left() + ui_px(4),
            min(
                x,
                geometry.right() - popup.width() - ui_px(4),
            ),
        )

        # Vertically center the popup relative to the hovered row where possible.
        y = center.y() - popup.height() // 2
        y = max(
            geometry.top() + ui_px(4),
            min(
                y,
                geometry.bottom() - popup.height() - ui_px(4),
            ),
        )

        popup.move(x, y)
        popup.show()
        popup.raise_()
        self._hover_popup = popup

    def _hide_hover_popup(self) -> None:
        if self._hover_popup is not None:
            self._hover_popup.close()
            self._hover_popup.deleteLater()
            self._hover_popup = None


class AttributesSidebar(QFrame):
    def __init__(
        self,
        attributes: Counter,
        database: MistfallDatabase | None,
        parent: QWidget | None = None,
        active_weapon_slot: int = DEFAULT_ACTIVE_WEAPON_SLOT,
        weapon_changed=None,
    ):
        super().__init__(parent)
        self.setObjectName("attributesSidebar")
        self.setFixedWidth(ui_px(284))

        root = QVBoxLayout(self)
        root.setContentsMargins(ui_px(10), ui_px(8), ui_px(10), ui_px(8))
        root.setSpacing(ui_px(3))

        title_row = QHBoxLayout()
        title_row.setSpacing(ui_px(4))

        title = QLabel("Атрибуты")
        title.setObjectName("attributesTitle")
        title_row.addWidget(title)
        title_row.addStretch(1)

        for slot, caption in ((10, "I"), (11, "II")):
            button = QPushButton(caption)
            button.setObjectName("weaponToggle")
            button.setCheckable(True)
            button.setChecked(active_weapon_slot == slot)
            button.setFixedSize(ui_px(28), ui_px(22))
            button.setToolTip(
                "Выбери активное оружие. В итоговые атрибуты входит только один оружейный слот."
            )
            if weapon_changed is not None:
                button.clicked.connect(lambda _checked=False, s=slot: weapon_changed(s))
            title_row.addWidget(button)

        root.addLayout(title_row)

        if attributes:
            for name, level in sorted(
                attributes.items(),
                key=lambda p: (-p[1], ru_affix(p[0])),
            ):
                root.addWidget(AttributeRow(name, level, database, compact=True))
        else:
            empty = QLabel("Нет активных атрибутов")
            empty.setObjectName("muted")
            empty.setWordWrap(True)
            root.addWidget(empty)

        root.addStretch(1)


class CompactAffixRow(QFrame):
    """Small game-like affix row for item descriptions/tooltips."""

    def __init__(
        self,
        name: str,
        level: int = 1,
        database: MistfallDatabase | None = None,
        suffix: str = "",
        icon_size: int = 36,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self.setObjectName("compactAffixRow")

        row = QHBoxLayout(self)
        row.setContentsMargins(0, ui_px(2), 0, ui_px(2))
        row.setSpacing(ui_px(9))

        icon = QLabel()
        setup_affix_icon_label(icon, name, icon_size)
        row.addWidget(icon, 0, Qt.AlignVCenter)

        label = QLabel(f"{ru_affix(name)}  Lv.{level}{suffix}")
        label.setObjectName("compactAffixText")
        label.setWordWrap(True)
        row.addWidget(label, 1)

        if database:
            desc = affix_description(database, name)
            effect = affix_current_effect(database, name, level)
            tooltip = f"<b>{ru_affix(name)} · Lv.{level}</b>"
            if desc:
                tooltip += f"<br>{desc}"
            if effect:
                tooltip += f"<br><br><b>Эффект уровня:</b><br>{effect}"
            self.setToolTip(tooltip)
            icon.setToolTip(tooltip)
            label.setToolTip(tooltip)


class ItemHoverPopup(QFrame):
    """Game-like informational card shown while the cursor is over an item tile."""

    def __init__(self, decoded: DecodedItem, database: MistfallDatabase):
        super().__init__(None, Qt.ToolTip)
        self.setObjectName("itemHoverPopup")
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self.setFixedWidth(405)

        item = decoded.item or {}
        grade = int(item.get("g", 0) or 0)
        rarity_color = RARITY_COLORS.get(grade, "#b99b70")

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 16, 18, 16)
        root.setSpacing(9)

        header = QHBoxLayout()
        title_box = QVBoxLayout()
        title = QLabel(item_name_ru(item, str(decoded.cfg)))
        title.setWordWrap(True)
        title.setStyleSheet(
            f"color: {rarity_color}; font-family: Georgia; font-size: 21px; font-weight: 600;"
        )
        title_box.addWidget(title)

        subtitle = QLabel(f"{database.rarity_name(grade)} · {SLOT_RU.get(decoded.slot, decoded.slot)}")
        subtitle.setObjectName("muted")
        title_box.addWidget(subtitle)
        header.addLayout(title_box, 1)

        icon = ItemTile._load_local_icon(decoded)
        if icon is not None:
            icon_label = QLabel()
            icon_label.setFixedSize(94, 94)
            icon_label.setAlignment(Qt.AlignCenter)
            icon_label.setPixmap(icon.scaled(90, 90, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            header.addWidget(icon_label)
        root.addLayout(header)

        stats = item_stats_text(item)
        if stats:
            for line in stats:
                stat = QLabel("▪ " + line)
                stat.setObjectName("hoverStat")
                stat.setWordWrap(True)
                root.addWidget(stat)

        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setObjectName("hoverSeparator")
        root.addWidget(line)

        any_affix = False
        if item.get("i"):
            name = str(item["i"])
            innate_title = QLabel("Врождённый атрибут")
            innate_title.setObjectName("hoverSourceTitle")
            root.addWidget(innate_title)
            root.addWidget(CompactAffixRow(name, 1, database, icon_size=36))
            any_affix = True

        for gem in decoded.gems:
            attrs = [str(a) for a in (gem.get("a") or [])]

            gem_header = QHBoxLayout()
            gem_header.setSpacing(ui_px(8))
            gem_header.addWidget(
                make_gem_icon_label(gem, 46),
                0,
                Qt.AlignVCenter,
            )

            gem_meta = QVBoxLayout()
            gem_meta.setContentsMargins(0, 0, 0, 0)
            gem_meta.setSpacing(ui_px(4))

            gem_title = QLabel(
                f"<b>{gem_short_type_text(gem)}</b>"
            )
            gem_title.setObjectName("hoverGemTitle")
            gem_meta.addWidget(gem_title)

            gem_meta.addWidget(
                make_gem_affix_icons(
                    gem,
                    icon_size=30,
                    spacing=4,
                ),
                0,
                Qt.AlignLeft,
            )
            gem_header.addLayout(gem_meta, 1)
            root.addLayout(gem_header)

            any_affix = True

        if not any_affix:
            no_affix = QLabel("Атрибутов и камней нет")
            no_affix.setObjectName("muted")
            root.addWidget(no_affix)

        contribution = Counter()
        if item.get("i"):
            contribution[str(item["i"])] += 1
        for gem in decoded.gems:
            for name in gem.get("a", []) or []:
                contribution[str(name)] += 1

        if contribution:
            line2 = QFrame()
            line2.setFrameShape(QFrame.HLine)
            line2.setObjectName("hoverSeparator")
            root.addWidget(line2)

            summary_title = QLabel("Вклад предмета")
            summary_title.setObjectName("hoverSummaryTitle")
            root.addWidget(summary_title)

            for name, amount in sorted(
                contribution.items(),
                key=lambda p: (-p[1], ru_affix(p[0])),
            ):
                root.addWidget(
                    CompactAffixRow(
                        name,
                        amount,
                        database,
                        suffix=f"   (+{amount})",
                        icon_size=34,
                    )
                )

        hint = QLabel("ЛКМ — открыть подробные сведения")
        hint.setObjectName("hoverHint")
        root.addWidget(hint)

        self.adjustSize()


class AffixCatalogDialog(QDialog):
    def __init__(self, database: MistfallDatabase, parent: QWidget | None = None):
        super().__init__(parent)
        self.database = database
        self.setWindowTitle("Все атрибуты Mistfall Hunter")
        self.resize(1040, 760)

        root = QVBoxLayout(self)
        root.setContentsMargins(22, 18, 22, 18)
        root.setSpacing(10)

        title = QLabel("Все атрибуты")
        title.setObjectName("dialogTitle")
        root.addWidget(title)

        subtitle = QLabel(
            "Полный основной список из русской версии игры. "
            "Наведи курсор на строку в сборке, чтобы увидеть текущий эффект."
        )
        subtitle.setObjectName("muted")
        subtitle.setWordWrap(True)
        root.addWidget(subtitle)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        host = QWidget()
        grid = QGridLayout(host)
        grid.setContentsMargins(0, 4, 0, 4)
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(10)

        for idx, name in enumerate(GAME_AFFIX_ORDER):
            panel = QFrame()
            panel.setObjectName("affixCatalogCard")
            box = QVBoxLayout(panel)
            box.setContentsMargins(12, 10, 12, 10)
            box.setSpacing(5)

            top = QHBoxLayout()
            icon = QLabel()
            setup_affix_icon_label(icon, name, 42)
            top.addWidget(icon)
            nm = QLabel(ru_affix(name))
            nm.setObjectName("catalogAffixName")
            top.addWidget(nm, 1)
            box.addLayout(top)

            desc = QLabel(affix_description(database, name))
            desc.setObjectName("catalogDescription")
            desc.setWordWrap(True)
            box.addWidget(desc)

            raw = database.data.get("affixes", {}).get(name, {})
            effects = raw.get("eff", []) if isinstance(raw, dict) else []
            translated = []
            for level, effect in enumerate(effects, start=1):
                effect_ru = affix_current_effect(database, name, level)
                if effect_ru:
                    translated.append(f"Ур. {level}: {effect_ru}")
            if translated:
                levels = QLabel("\n".join(translated))
                levels.setObjectName("catalogLevels")
                levels.setWordWrap(True)
                box.addWidget(levels)

            grid.addWidget(panel, idx // 2, idx % 2)

        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        scroll.setWidget(host)
        root.addWidget(scroll, 1)

        close = QDialogButtonBox(QDialogButtonBox.Close)
        close.rejected.connect(self.reject)
        close.accepted.connect(self.accept)
        close.button(QDialogButtonBox.Close).clicked.connect(self.accept)
        root.addWidget(close)


class ItemTile(QFrame):
    clicked = Signal(object)

    def __init__(self, decoded: DecodedItem | None, database: MistfallDatabase | None, size: int = 64):
        super().__init__()
        self.decoded = decoded
        self.database = database
        self._hover_popup: ItemHoverPopup | None = None
        logical_size = ui_px(size)
        self._logical_size = logical_size
        self.setFixedSize(logical_size, logical_size)
        self.setObjectName("itemTile")
        self.setCursor(Qt.PointingHandCursor if decoded and decoded.item else Qt.ArrowCursor)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(ui_px(4), ui_px(4), ui_px(4), ui_px(4))
        layout.setSpacing(ui_px(1))

        center = QLabel()
        center.setAlignment(Qt.AlignCenter)
        center.setWordWrap(True)
        center.setObjectName("itemGlyph")
        layout.addWidget(center, 1)

        grade = 0
        if decoded and decoded.item:
            item = decoded.item
            grade = int(item.get("g", 0) or 0)
            icon = self._load_local_icon(decoded)
            if icon is not None:
                center.setPixmap(icon.scaled(max(1, logical_size - ui_px(10)), max(1, logical_size - ui_px(10)), Qt.KeepAspectRatio, Qt.SmoothTransformation))
            else:
                words = [w for w in item_name_ru(item, "?").replace("'", " ").replace("«", " ").replace("»", " ").split() if w]
                initials = "".join(word[0].upper() for word in words[:2]) or SLOT_SHORT.get(decoded.slot, "?")
                center.setText(initials)

            gem_line = []
            if item.get("i"):
                gem_line.append(ru_affix(str(item["i"])))
            for gem in decoded.gems:
                gem_line.extend(ru_affix(str(a)) for a in (gem.get("a") or []))
            tooltip = [
                f"<b>{item_name_ru(item, str(decoded.cfg))}</b>",
                f"{SLOT_RU.get(decoded.slot, decoded.slot)} · {database.rarity_name(grade) if database else grade}",
                f"ID: {decoded.cfg}",
            ]
            if gem_line:
                tooltip.append("Атрибуты: " + ", ".join(gem_line))
            if decoded.gems:
                tooltip.append("Камни: " + ", ".join(gem_name_ru(g, str(g.get("id", "?"))) for g in decoded.gems))
            stats = item_stats_text(item)
            if stats:
                tooltip.append("<br>".join(stats))
            tooltip.append("Нажми, чтобы открыть подробности")
            self._fallback_tooltip = "<br>".join(tooltip)
        else:
            center.setText("—")
            if decoded:
                self.setToolTip(f"{SLOT_RU.get(decoded.slot, decoded.slot)}: пусто")

        border = RARITY_COLORS.get(grade, "#463a2b")
        bg = QColor(border)
        # WEBP предметов прозрачные: оттенок редкости формирует сама клетка.
        if grade:
            bg = bg.darker(285)
        else:
            bg = QColor("#0c0d0c")

        self._tile_bg = bg.name()
        self._tile_border = border
        self._apply_tile_style(False)

    def _apply_tile_style(self, highlighted: bool) -> None:
        border = "#f5f3eb" if highlighted else self._tile_border
        border_width = 2 if highlighted else 1
        self.setStyleSheet(
            f"QFrame#itemTile {{ "
            f"background: {self._tile_bg}; "
            f"border: {border_width}px solid {border}; "
            "}"
            "QLabel#itemGlyph { "
            "color: #c6b99f; background: transparent; border: none; "
            "font-size: 17px; font-weight: 600; "
            "}"
        )

    def enterEvent(self, event) -> None:  # noqa: N802
        if self.decoded and self.decoded.item:
            self._apply_tile_style(True)
        if self.decoded and self.decoded.item and self.database:
            self._show_hover_popup()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:  # noqa: N802
        self._apply_tile_style(False)
        self._hide_hover_popup()
        super().leaveEvent(event)

    def _show_hover_popup(self) -> None:
        self._hide_hover_popup()
        if not self.decoded or not self.decoded.item or not self.database:
            return

        popup = ItemHoverPopup(self.decoded, self.database)
        popup.adjustSize()

        right_pos = self.mapToGlobal(QPoint(self.width() + 10, -8))
        left_pos = self.mapToGlobal(QPoint(-popup.width() - 10, -8))
        center = self.mapToGlobal(self.rect().center())
        screen = QApplication.screenAt(center)
        geometry = screen.availableGeometry() if screen else QApplication.primaryScreen().availableGeometry()

        x = right_pos.x()
        if x + popup.width() > geometry.right():
            x = left_pos.x()
        x = max(geometry.left() + 4, min(x, geometry.right() - popup.width() - 4))

        y = right_pos.y()
        y = max(geometry.top() + 4, min(y, geometry.bottom() - popup.height() - 4))

        popup.move(x, y)
        popup.show()
        popup.raise_()
        self._hover_popup = popup

    def _hide_hover_popup(self) -> None:
        if self._hover_popup is not None:
            self._hover_popup.close()
            self._hover_popup.deleteLater()
            self._hover_popup = None

    def mousePressEvent(self, event) -> None:
        self._hide_hover_popup()
        if event.button() == Qt.LeftButton and self.decoded and self.decoded.item:
            self.clicked.emit(self.decoded)
        super().mousePressEvent(event)

    @staticmethod
    def _load_local_icon(decoded: DecodedItem) -> QPixmap | None:
        if not decoded.item:
            return None

        item = decoded.item
        class_name = str(item.get("_class_name", "") or "")
        class_folder = CLASS_ICON_FOLDERS.get(class_name)
        item_name = str(item.get("n", "") or "")

        # 1) Самый точный способ: icon_map.txt + папка конкретного класса.
        mapped_name = mapped_item_icon_filename(class_name, item_name)
        if mapped_name and class_folder:
            path = find_icon_path(mapped_name, class_folder)
            if path is not None:
                pixmap = QPixmap(str(path))
                if not pixmap.isNull():
                    return pixmap

        # 2) Поле ic из базы, но сначала тоже строго в папке класса.
        icon_name = str(item.get("ic", "") or "")
        if icon_name:
            path = find_icon_path(icon_name, class_folder)
            if path is not None and not is_legacy_myth_placeholder(
                path, class_name, decoded.cfg
            ):
                pixmap = QPixmap(str(path))
                if not pixmap.isNull():
                    return pixmap

        # 3) Совместимость с файлами, названными cfgId.
        for fallback_name in (f"{decoded.cfg}.webp", f"{decoded.cfg}.png"):
            path = find_icon_path(fallback_name, class_folder)
            if path is not None and not is_legacy_myth_placeholder(
                path, class_name, decoded.cfg
            ):
                pixmap = QPixmap(str(path))
                if not pixmap.isNull():
                    return pixmap

        return None


class ItemDetailsDialog(QDialog):
    def __init__(self, decoded_item: DecodedItem, database: MistfallDatabase, parent: QWidget | None = None):
        super().__init__(parent)
        self.decoded_item = decoded_item
        self.database = database
        item = decoded_item.item or {}
        self.setWindowTitle(item_name_ru(item, str(decoded_item.cfg)))
        self.resize(760, 670)

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(ui_px(7))

        header = QHBoxLayout()
        title_box = QVBoxLayout()
        title = QLabel(item_name_ru(item, str(decoded_item.cfg)))
        title.setObjectName("dialogTitle")
        title.setWordWrap(True)
        title_box.addWidget(title)
        grade = int(item.get("g", 0) or 0)
        subtitle = QLabel(
            f"{database.rarity_name(grade)} · {SLOT_RU.get(decoded_item.slot, decoded_item.slot)} · ID {decoded_item.cfg}"
        )
        subtitle.setObjectName("muted")
        title_box.addWidget(subtitle)
        header.addLayout(title_box, 1)
        root.addLayout(header)

        stats_box = QFrame()
        stats_box.setObjectName("detailsPanel")
        stats_layout = QVBoxLayout(stats_box)
        stats_layout.setContentsMargins(16, 14, 16, 14)
        stats_title = QLabel("Характеристики предмета")
        stats_title.setObjectName("sectionTitle")
        stats_layout.addWidget(stats_title)
        stats = item_stats_text(item, include_combat=True)
        if stats:
            for line in stats:
                stats_layout.addWidget(QLabel(line))
        else:
            stats_layout.addWidget(QLabel("—"))
        root.addWidget(stats_box)

        contribution = Counter()
        if item.get("i"):
            contribution[str(item["i"])] += 1
        for gem in decoded_item.gems:
            for affix in gem.get("a", []) or []:
                contribution[str(affix)] += 1

        affix_box = QFrame()
        affix_box.setObjectName("detailsPanel")
        affix_layout = QVBoxLayout(affix_box)
        affix_layout.setContentsMargins(16, 14, 16, 14)
        affix_title = QLabel("Атрибуты и камни")
        affix_title.setObjectName("sectionTitle")
        affix_layout.addWidget(affix_title)

        if item.get("i"):
            name = str(item["i"])
            innate_title = QLabel("Врождённый атрибут")
            innate_title.setObjectName("muted")
            affix_layout.addWidget(innate_title)
            affix_layout.addWidget(CompactAffixRow(name, 1, database, icon_size=40))

        sockets = item.get("s") or []
        gem_by_id = database.gem_by_id
        for idx, socket in enumerate(sockets):
            try:
                socket_type, socket_level = int(socket[0]), int(socket[1])
            except Exception:
                socket_type, socket_level = 0, 0
            gem_id = decoded_item.gem_ids[idx] if idx < len(decoded_item.gem_ids) else 0
            gem = gem_by_id.get(int(gem_id)) if gem_id else None
            socket_name = SOCKET_RU.get(socket_type, str(socket_type))
            if gem:
                gem_level = int(gem.get("l", 0) or 0)
                gem_type = int(gem.get("t", 0) or 0)
                valid_type = socket_type == -1 or socket_type == gem_type
                valid_level = gem_level <= socket_level
                state = "✓" if valid_type and valid_level else "⚠"

                gem_row = QHBoxLayout()
                gem_row.setSpacing(ui_px(10))
                gem_row.addWidget(
                    make_gem_icon_label(gem, 52),
                    0,
                    Qt.AlignVCenter,
                )

                gem_meta = QVBoxLayout()
                gem_meta.setContentsMargins(0, 0, 0, 0)
                gem_meta.setSpacing(ui_px(4))

                line = QLabel(
                    f"{state} Слот {idx + 1}: "
                    f"{socket_name} ранг {socket_level} · "
                    f"{gem_short_type_text(gem)}"
                )
                line.setWordWrap(True)
                line.setObjectName("hoverGemTitle")
                gem_meta.addWidget(line)

                gem_meta.addWidget(
                    make_gem_affix_icons(
                        gem,
                        icon_size=32,
                        spacing=5,
                    ),
                    0,
                    Qt.AlignLeft,
                )

                gem_row.addLayout(gem_meta, 1)
                affix_layout.addLayout(gem_row)
            else:
                affix_layout.addWidget(
                    QLabel(f"Слот {idx + 1}: {socket_name} ранг {socket_level} — пусто")
                )

        if contribution:
            contribution_title = QLabel("Вклад этого предмета")
            contribution_title.setObjectName("sectionTitle")
            affix_layout.addWidget(contribution_title)
            for name, level in sorted(
                contribution.items(),
                key=lambda p: (-p[1], ru_affix(p[0])),
            ):
                effect = affix_current_effect(database, name, level)
                suffix = f"   (+{level})"
                if effect:
                    suffix += f"  —  {effect}"
                affix_layout.addWidget(
                    CompactAffixRow(name, level, database, suffix=suffix, icon_size=38)
                )
        root.addWidget(affix_box)

        lore = item_lore_ru(item)
        if lore:
            lore_title = QLabel("Описание")
            lore_title.setObjectName("sectionTitle")
            root.addWidget(lore_title)
            lore_label = QLabel(lore)
            lore_label.setWordWrap(True)
            lore_label.setObjectName("muted")
            root.addWidget(lore_label)

        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)


class BuildDetailsDialog(QDialog):
    def __init__(self, title: str, decoded: DecodedBuild, database: MistfallDatabase, parent: QWidget | None = None):
        super().__init__(parent)
        self.decoded = decoded
        self.database = database
        self.setWindowTitle(f"{title} — сведения")
        self.resize(1050, 660)

        root = QVBoxLayout(self)
        root.setContentsMargins(22, 18, 22, 18)
        root.setSpacing(12)

        heading = QLabel(title)
        heading.setObjectName("dialogTitle")
        root.addWidget(heading)

        sub = QLabel(CLASS_RU.get(decoded.class_name, decoded.class_name))
        sub.setObjectName("muted")
        root.addWidget(sub)

        code_row = QHBoxLayout()
        code_edit = QLineEdit(decoded.code)
        code_edit.setReadOnly(True)
        copy_btn = QPushButton("Копировать код")
        copy_btn.clicked.connect(lambda: QApplication.clipboard().setText(decoded.code))
        code_row.addWidget(code_edit, 1)
        code_row.addWidget(copy_btn)
        root.addLayout(code_row)

        body = QHBoxLayout()
        body.setSpacing(18)

        table = QTableWidget(0, 6)
        table.setHorizontalHeaderLabels(["Слот", "Предмет", "Редкость", "Характеристики", "Врождённый", "Камни / атрибуты"])
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.setAlternatingRowColors(True)
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        table.horizontalHeader().setSectionResizeMode(5, QHeaderView.Stretch)

        by_slot = {entry.slot: entry for entry in decoded.items}
        for slot in DISPLAY_SLOT_ORDER:
            decoded_item = by_slot[slot]
            row = table.rowCount()
            table.insertRow(row)
            item = decoded_item.item
            table.setItem(row, 0, QTableWidgetItem(SLOT_RU.get(decoded_item.slot, str(decoded_item.slot))))
            if not item:
                table.setItem(row, 1, QTableWidgetItem("—"))
                table.setItem(row, 2, QTableWidgetItem("—"))
                table.setItem(row, 3, QTableWidgetItem("—"))
                table.setItem(row, 4, QTableWidgetItem("—"))
                table.setItem(row, 5, QTableWidgetItem("—"))
                continue

            grade = int(item.get("g", 0) or 0)
            innate = ru_affix(str(item.get("i"))) if item.get("i") else "—"
            gem_parts = []
            for gem in decoded_item.gems:
                attrs = [
                    ru_affix(str(a))
                    for a in (gem.get("a") or [])
                ]
                attr_text = " + ".join(attrs) if attrs else "—"
                gem_parts.append(
                    f"{gem_short_type_text(gem)}: {attr_text}"
                )
            table.setItem(row, 1, QTableWidgetItem(f"{item_name_ru(item, str(decoded_item.cfg))}\nID {decoded_item.cfg}"))
            table.setItem(row, 2, QTableWidgetItem(database.rarity_name(grade)))
            table.setItem(row, 3, QTableWidgetItem("\n".join(item_stats_text(item))))
            table.setItem(row, 4, QTableWidgetItem(innate))
            table.setItem(row, 5, QTableWidgetItem("\n".join(gem_parts) if gem_parts else "—"))
            table.setRowHeight(row, 68)

        row_items = [by_slot[slot] for slot in DISPLAY_SLOT_ORDER]

        def open_row_details(row: int, _column: int) -> None:
            if 0 <= row < len(row_items) and row_items[row].item:
                ItemDetailsDialog(row_items[row], database, self).exec()

        table.cellDoubleClicked.connect(open_row_details)
        table.setToolTip("Двойной щелчок по строке — подробности предмета")
        body.addWidget(table, 3)

        attr_panel = QFrame()
        attr_panel.setObjectName("detailsPanel")
        attr_panel.setMinimumWidth(270)
        attr_layout = QVBoxLayout(attr_panel)
        attr_layout.setContentsMargins(16, 16, 16, 16)
        attr_layout.setSpacing(8)
        attr_title = QLabel("Атрибуты сборки")
        attr_title.setObjectName("sectionTitle")
        attr_layout.addWidget(attr_title)

        active_weapon_text = "Оружие I" if decoded.active_weapon_slot == 10 else "Оружие II"
        active_note = QLabel(
            f"Расчёт: броня + украшения + {active_weapon_text}. "
            "Активное оружие не записывается в код сборки."
        )
        active_note.setObjectName("muted")
        active_note.setWordWrap(True)
        attr_layout.addWidget(active_note)

        if decoded.attributes:
            for name, level in sorted(decoded.attributes.items(), key=lambda pair: (-pair[1], ru_affix(pair[0]))):
                row = QHBoxLayout()
                effect = affix_current_effect(database, name, level)
                label = QLabel(ru_affix(name) + (f"\n{effect}" if effect else ""))
                label.setWordWrap(True)
                label.setToolTip(affix_description(database, name))
                value = QLabel(f"Lv.{level}")
                value.setObjectName("gold")
                value.setToolTip(affix_description(database, name))
                row.addWidget(label, 1)
                row.addWidget(value)
                attr_layout.addLayout(row)
        else:
            label = QLabel("Атрибуты не найдены")
            label.setObjectName("muted")
            attr_layout.addWidget(label)
        attr_layout.addStretch(1)
        body.addWidget(attr_panel, 1)

        root.addLayout(body, 1)

        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)


class EditBuildDialog(QDialog):
    def __init__(self, name: str, code: str, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle("Изменить сборку")
        self.resize(620, 180)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)

        self.name_edit = QLineEdit(name)
        self.name_edit.setPlaceholderText("Название сборки")
        self.code_edit = QLineEdit(code)
        self.code_edit.setPlaceholderText("Код Mistfall Hunter")
        layout.addWidget(QLabel("Название"))
        layout.addWidget(self.name_edit)
        layout.addWidget(QLabel("Код"))
        layout.addWidget(self.code_edit)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)


class BuildCard(QFrame):
    copy_requested = Signal(int)
    edit_requested = Signal(int)
    creator_edit_requested = Signal(int)
    delete_requested = Signal(int)
    details_requested = Signal(int)
    weapon_requested = Signal(int, int)

    def __init__(self, index: int, build: dict[str, str], decoded: DecodedBuild | None, database: MistfallDatabase | None):
        super().__init__()
        self.index = index
        self.build = build
        self.decoded = decoded
        self.database = database
        self.setObjectName("buildCard")
        attribute_rows = len(decoded.attributes) if decoded else 0

        # 5 вертикальных рядов экипировки по 64px + 4 промежутка по 6px,
        # плюс заголовок и мета-строка.
        equipment_height = 5 * 64 + 4 * 6
        target_height_physical = max(
            455,
            62 + 59 * attribute_rows,
        )
        self.setFixedSize(
            ui_px(BUILD_CARD_WIDTH_PHYSICAL),
            ui_px(target_height_physical),
        )
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        outer = QHBoxLayout(self)
        outer.setContentsMargins(ui_px(9), ui_px(8), ui_px(8), ui_px(8))
        outer.setSpacing(ui_px(8))
        outer.setAlignment(Qt.AlignLeft | Qt.AlignTop)

        left_widget = QWidget()
        left_widget.setFixedWidth(ui_px(2 * 64 + 6))
        left = QVBoxLayout(left_widget)
        left.setContentsMargins(0, 0, 0, 0)
        left.setSpacing(ui_px(5))

        header = QHBoxLayout()
        title = QLabel(build.get("name", "Без названия"))
        title.setObjectName("buildTitle")
        title.setTextInteractionFlags(Qt.TextSelectableByMouse)
        edit_small = QPushButton("✎")
        edit_small.setObjectName("tinyButton")
        edit_small.setFixedSize(ui_px(22), ui_px(22))
        edit_small.setToolTip("Изменить название или код")
        edit_small.clicked.connect(lambda: self.edit_requested.emit(self.index))
        header.addWidget(title)
        header.addWidget(edit_small)
        header.addStretch(1)
        left.addLayout(header)

        meta_text = "База предметов не загружена"
        if decoded:
            meta_text = f"Активных атрибутов: {len(decoded.attributes)}"
        meta = QLabel(meta_text)
        meta.setObjectName("buildMeta")
        meta.setWordWrap(True)
        left.addWidget(meta)

        items_wrap = QWidget()
        items_grid = QGridLayout(items_wrap)
        items_grid.setContentsMargins(0, 0, 0, 0)
        items_grid.setHorizontalSpacing(ui_px(6))
        items_grid.setVerticalSpacing(ui_px(6))
        items_grid.setAlignment(Qt.AlignLeft | Qt.AlignTop)

        by_slot = {entry.slot: entry for entry in decoded.items} if decoded else {}
        for slot in DISPLAY_SLOT_ORDER:
            tile = ItemTile(by_slot.get(slot), database, size=64)
            if database:
                tile.clicked.connect(
                    lambda decoded_item, db=database:
                    ItemDetailsDialog(decoded_item, db, self).exec()
                )

            row, col, row_span, col_span, alignment = EQUIPMENT_GRID_LAYOUT[slot]
            items_grid.addWidget(
                tile,
                row,
                col,
                row_span,
                col_span,
                alignment,
            )

        items_wrap.setFixedSize(
            ui_px(2 * 64 + 6),
            ui_px(equipment_height),
        )
        left.addWidget(items_wrap, 0, Qt.AlignHCenter | Qt.AlignTop)

        if decoded is None and database is not None:
            err = QLabel("Не удалось расшифровать этот код")
            err.setObjectName("errorText")
            left.addWidget(err)

        outer.addWidget(left_widget)

        if decoded and decoded.attributes:
            sidebar = AttributesSidebar(
                decoded.attributes,
                database,
                self,
                active_weapon_slot=decoded.active_weapon_slot,
                weapon_changed=lambda slot: self.weapon_requested.emit(self.index, slot),
            )
            outer.addWidget(sidebar)

        actions = QVBoxLayout()
        actions.setSpacing(ui_px(6))
        actions.addStretch(1)

        info = self._action_button("i", "Сведения")
        info.clicked.connect(lambda: self.details_requested.emit(self.index))

        edit_creator = self._action_button("✎", "Редактировать сборку")
        edit_creator.setProperty("editor", True)
        edit_creator.clicked.connect(
            lambda: self.creator_edit_requested.emit(self.index)
        )

        copy = self._action_button("↗", "Скопировать код")
        copy.clicked.connect(lambda: self.copy_requested.emit(self.index))

        delete = self._action_button("✕", "Удалить")
        delete.setProperty("danger", True)
        delete.clicked.connect(lambda: self.delete_requested.emit(self.index))

        actions.addWidget(info)
        actions.addWidget(edit_creator)
        actions.addWidget(copy)
        actions.addWidget(delete)
        actions.addStretch(1)
        outer.addLayout(actions)

    @staticmethod
    def _action_button(text: str, tooltip: str) -> QPushButton:
        button = QPushButton(text)
        button.setObjectName("squareAction")
        button.setFixedSize(ui_px(50), ui_px(50))
        button.setToolTip(tooltip)
        return button


class SavedBuildsPage(QWidget):
    copy_requested = Signal(int)
    edit_requested = Signal(int)
    creator_edit_requested = Signal(int)
    delete_requested = Signal(int)
    details_requested = Signal(int)
    refresh_data_requested = Signal()
    affix_catalog_requested = Signal()
    weapon_requested = Signal(int, int)

    def __init__(self):
        super().__init__()
        self.repo: BuildRepository | None = None
        self.database: MistfallDatabase | None = None
        self.decoded_cache: dict[int, DecodedBuild | None] = {}
        self.active_class: str | None = None
        self._last_column_count = 0

        root = QVBoxLayout(self)
        root.setContentsMargins(0, ui_px(5), 0, 0)
        root.setSpacing(12)

        tools = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("Поиск по названию, коду, классу или атрибутам…")
        self.search.textChanged.connect(self.render)
        self.affixes_button = QPushButton("Все атрибуты")
        self.affixes_button.clicked.connect(self.affix_catalog_requested.emit)
        self.refresh_button = QPushButton("Обновить базу")
        self.refresh_button.clicked.connect(self.refresh_data_requested.emit)
        tools.addWidget(self.search, 1)
        tools.addWidget(self.affixes_button)
        tools.addWidget(self.refresh_button)
        root.addLayout(tools)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.scroll_host = QWidget()
        self.grid = QGridLayout(self.scroll_host)
        self.grid.setContentsMargins(0, 0, 0, 0)
        self.grid.setHorizontalSpacing(ui_px(8))
        self.grid.setVerticalSpacing(ui_px(8))
        self.grid.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.scroll_host.setMinimumWidth(
            ui_px(3 * BUILD_CARD_WIDTH_PHYSICAL + 2 * BUILD_CARD_GAP_PHYSICAL)
        )
        self.scroll.setWidget(self.scroll_host)
        root.addWidget(self.scroll, 1)

    def _column_count(self) -> int:
        # По запросу интерфейс сборок всегда строится в 3 колонки.
        # FixedSize у карточек не даёт им ужиматься; на узком окне
        # QScrollArea просто покажет горизонтальную прокрутку.
        return 3

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        columns = self._column_count()
        if columns != self._last_column_count:
            self._last_column_count = columns
            QTimer.singleShot(0, self.render)

    def set_state(
        self,
        repo: BuildRepository,
        database: MistfallDatabase | None,
        active_class: str | None = None,
    ) -> None:
        self.repo = repo
        self.database = database
        self.active_class = active_class
        self.redecode()
        self.render()

    def redecode(self) -> None:
        self.decoded_cache.clear()
        if not self.repo or not self.database:
            return
        for index, build in enumerate(self.repo.builds):
            try:
                self.decoded_cache[index] = self.database.decode(build["code"], int(build.get("weapon_slot", DEFAULT_ACTIVE_WEAPON_SLOT)))
            except Exception:
                self.decoded_cache[index] = None

    def render(self) -> None:
        while self.grid.count():
            item = self.grid.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        if not self.repo:
            return

        query = self.search.text().strip().lower()
        visible: list[tuple[int, dict[str, str]]] = []
        for index, build in enumerate(self.repo.builds):
            decoded = self.decoded_cache.get(index)
            build_class = str(build.get("class_name", "") or "")
            if not build_class and decoded:
                build_class = decoded.class_name

            if self.active_class and build_class != self.active_class:
                continue

            haystack = [build.get("name", ""), build.get("code", "")]
            if decoded:
                haystack.append(decoded.class_name)
                haystack.extend(decoded.attributes.keys())
                haystack.extend(ru_affix(name) for name in decoded.attributes.keys())
            if query and query not in " ".join(haystack).lower():
                continue
            visible.append((index, build))

        if not visible:
            class_text = CLASS_RU.get(self.active_class or "", self.active_class or "")
            message = "Сохранённых сборок пока нет."
            if class_text:
                message = f"Для класса «{class_text}» пока нет сохранённых сборок."
            empty = QLabel(message + "\nОткрой вкладку «Импорт сборки» и вставь код из игры.")
            empty.setObjectName("emptyState")
            empty.setAlignment(Qt.AlignCenter)
            self.grid.addWidget(empty, 0, 0, 1, 3)
            return

        for n, (index, build) in enumerate(visible):
            card = BuildCard(
                index,
                build,
                self.decoded_cache.get(index),
                self.database,
            )
            card.copy_requested.connect(self.copy_requested)
            card.edit_requested.connect(self.edit_requested)
            card.creator_edit_requested.connect(
                self.creator_edit_requested
            )
            card.delete_requested.connect(self.delete_requested)
            card.details_requested.connect(self.details_requested)
            card.weapon_requested.connect(self.weapon_requested)
            columns = self._column_count()
            self._last_column_count = columns
            self.grid.addWidget(card, n // columns, n % columns)

        for column in range(3):
            self.grid.setColumnStretch(column, 0)


class ImportPage(QWidget):
    save_requested = Signal(str, str, int)

    def __init__(self):
        super().__init__()
        self.database: MistfallDatabase | None = None
        self.current_decoded: DecodedBuild | None = None
        self.active_weapon_slot = DEFAULT_ACTIVE_WEAPON_SLOT

        root = QVBoxLayout(self)
        root.setContentsMargins(45, 22, 45, 25)
        root.setSpacing(14)

        box = QFrame()
        box.setObjectName("importBox")
        form = QVBoxLayout(box)
        form.setContentsMargins(22, 20, 22, 20)
        form.setSpacing(10)

        label = QLabel("Код сборки")
        label.setObjectName("sectionTitle")
        form.addWidget(label)

        self.code_edit = QLineEdit()
        self.code_edit.setPlaceholderText(
            "Вставь или введи код сборки — расшифровка выполняется автоматически"
        )
        self.code_edit.textChanged.connect(self._code_changed)
        form.addWidget(self.code_edit)

        self.status = QLabel("Вставь код из Mistfall Hunter.")
        self.status.setObjectName("muted")
        form.addWidget(self.status)
        root.addWidget(box)

        self.preview = QFrame()
        self.preview.setObjectName("previewPanel")
        preview_layout = QHBoxLayout(self.preview)
        preview_layout.setContentsMargins(22, 18, 22, 18)
        preview_layout.setSpacing(24)

        left = QVBoxLayout()
        self.preview_class = QLabel("Предпросмотр")
        self.preview_class.setObjectName("previewTitle")
        left.addWidget(self.preview_class)

        self.tiles_host = QWidget()
        self.tiles_grid = QGridLayout(self.tiles_host)
        self.tiles_grid.setContentsMargins(0, 0, 0, 0)
        self.tiles_grid.setHorizontalSpacing(ui_px(6))
        self.tiles_grid.setVerticalSpacing(ui_px(6))
        self.tiles_grid.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        left.addWidget(self.tiles_host)
        preview_layout.addLayout(left, 3)

        right = QFrame()
        right.setObjectName("detailsPanel")
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(18, 16, 18, 16)
        attr_title = QLabel("Атрибуты")
        attr_title.setObjectName("sectionTitle")
        right_layout.addWidget(attr_title)

        weapon_row = QHBoxLayout()
        weapon_help = QLabel("Активное оружие")
        weapon_help.setObjectName("attributeWeaponNote")
        weapon_help.setToolTip(
            "Код сборки содержит оба оружия, но не содержит выбранный активный слот."
        )
        weapon_row.addWidget(weapon_help)
        weapon_row.addStretch(1)
        self.weapon_buttons: dict[int, QPushButton] = {}
        for slot, caption in ((10, "I"), (11, "II")):
            button = QPushButton(caption)
            button.setObjectName("weaponToggle")
            button.setCheckable(True)
            button.setFixedSize(ui_px(34), ui_px(26))
            button.clicked.connect(lambda _checked=False, s=slot: self.set_active_weapon(s))
            self.weapon_buttons[slot] = button
            weapon_row.addWidget(button)
        right_layout.addLayout(weapon_row)

        weapon_warning = QLabel("Важно: активное оружие не хранится в коде сборки — выбери I или II как в игре.")
        weapon_warning.setObjectName("attributeWeaponNote")
        weapon_warning.setWordWrap(True)
        right_layout.addWidget(weapon_warning)

        self.attr_host = QWidget()
        self.attr_layout = QVBoxLayout(self.attr_host)
        self.attr_layout.setContentsMargins(0, 0, 0, 0)
        self.attr_layout.setSpacing(7)
        right_layout.addWidget(self.attr_host)
        right_layout.addStretch(1)
        preview_layout.addWidget(right, 2)

        root.addWidget(self.preview, 1)

        save_row = QHBoxLayout()
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Название, например: Эгида 4 + Красноречие 4")
        self.save_button = QPushButton("Сохранить сборку")
        self.save_button.setObjectName("goldButton")
        self.save_button.clicked.connect(self.save_current)
        save_row.addWidget(self.name_edit, 1)
        save_row.addWidget(self.save_button)
        root.addLayout(save_row)

        self._clear_preview()

    def set_database(self, database: MistfallDatabase | None) -> None:
        self.database = database
        if database and clean_code(self.code_edit.text()):
            self.decode_current()

    def _code_changed(self, _text: str) -> None:
        code = clean_code(self.code_edit.text())
        if not code:
            self.current_decoded = None
            self.status.setText("Вставь код из Mistfall Hunter.")
            self.status.setObjectName("muted")
            self.status.style().unpolish(self.status)
            self.status.style().polish(self.status)
            self._clear_preview()
            return

        # Пробуем декодировать каждое изменение поля:
        # вставка, удаление или изменение даже одного символа.
        self.decode_current()

    def paste_clipboard(self) -> None:
        self.code_edit.setText(clean_code(QApplication.clipboard().text()))
        if self.database:
            self.decode_current()

    def decode_current(self) -> None:
        if not self.database:
            self.status.setText("База предметов ещё не загружена.")
            self.status.setObjectName("errorText")
            self.status.style().unpolish(self.status)
            self.status.style().polish(self.status)
            return

        code = clean_code(self.code_edit.text())
        try:
            decoded = self.database.decode(code, self.active_weapon_slot)
        except Exception as exc:
            self.current_decoded = None
            self.status.setText(f"Ошибка: {exc}")
            self.status.setObjectName("errorText")
            self.status.style().unpolish(self.status)
            self.status.style().polish(self.status)
            self._clear_preview()
            return

        self.current_decoded = decoded
        self.status.setText("Код успешно расшифрован.")
        self.status.setObjectName("successText")
        self.status.style().unpolish(self.status)
        self.status.style().polish(self.status)
        self._render_preview(decoded)

        if not self.name_edit.text().strip():
            attrs = " + ".join(f"{ru_affix(k)} {v}" for k, v in sorted(decoded.attributes.items(), key=lambda p: (-p[1], ru_affix(p[0]))))
            self.name_edit.setText(attrs or CLASS_RU.get(decoded.class_name, decoded.class_name))

    def _clear_layout(self, layout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
                continue
            child_layout = item.layout()
            if child_layout is not None:
                self._clear_layout(child_layout)
                child_layout.deleteLater()

    def _clear_preview(self) -> None:
        self._clear_layout(self.tiles_grid)
        self._clear_layout(self.attr_layout)
        self.preview_class.setText("Предпросмотр сборки")
        placeholder = QLabel("После расшифровки здесь появятся 9 предметов и итоговые атрибуты.")
        placeholder.setObjectName("muted")
        placeholder.setWordWrap(True)
        placeholder.setAlignment(Qt.AlignCenter)
        self.tiles_grid.addWidget(placeholder, 0, 0, 5, 2)
        attr = QLabel("—")
        attr.setObjectName("muted")
        self.attr_layout.addWidget(attr)

    def _render_preview(self, decoded: DecodedBuild) -> None:
        self._clear_layout(self.tiles_grid)
        self._clear_layout(self.attr_layout)
        self.preview_class.setText(CLASS_RU.get(decoded.class_name, decoded.class_name))

        by_slot = {entry.slot: entry for entry in decoded.items}
        for slot in DISPLAY_SLOT_ORDER:
            tile = ItemTile(by_slot.get(slot), self.database, size=64)
            if self.database:
                tile.clicked.connect(
                    lambda decoded_item, db=self.database:
                    ItemDetailsDialog(decoded_item, db, self).exec()
                )
            row, col, row_span, col_span, alignment = EQUIPMENT_GRID_LAYOUT[slot]
            self.tiles_grid.addWidget(
                tile,
                row,
                col,
                row_span,
                col_span,
                alignment,
            )

        for slot, button in self.weapon_buttons.items():
            button.blockSignals(True)
            button.setChecked(decoded.active_weapon_slot == slot)
            button.blockSignals(False)

        if decoded.attributes:
            for name, level in sorted(decoded.attributes.items(), key=lambda p: (-p[1], ru_affix(p[0]))):
                self.attr_layout.addWidget(AttributeRow(name, level, self.database))
        else:
            label = QLabel("Атрибуты не найдены")
            label.setObjectName("muted")
            self.attr_layout.addWidget(label)

    def set_active_weapon(self, weapon_slot: int) -> None:
        if weapon_slot not in WEAPON_SLOTS:
            return
        self.active_weapon_slot = weapon_slot
        for slot, button in self.weapon_buttons.items():
            button.blockSignals(True)
            button.setChecked(slot == weapon_slot)
            button.blockSignals(False)
        if self.current_decoded:
            self.current_decoded.active_weapon_slot = weapon_slot
            self.current_decoded.attributes = self.current_decoded.attributes_for_weapon(weapon_slot)
            self._render_preview(self.current_decoded)

    def save_current(self) -> None:
        if not self.current_decoded:
            self.decode_current()
        if not self.current_decoded:
            return
        name = self.name_edit.text().strip() or "Без названия"
        self.save_requested.emit(name, self.current_decoded.code, self.current_decoded.active_weapon_slot)



class BuilderSlotTile(QFrame):
    clicked = Signal(int)

    def __init__(self, slot: int, parent: QWidget | None = None):
        super().__init__(parent)
        self.slot = slot
        self.decoded_item: DecodedItem | None = None
        self.database: MistfallDatabase | None = None
        self.selected = False

        self.setObjectName("builderSlotTile")
        self.setFixedSize(ui_px(82), ui_px(88))
        self.setCursor(Qt.PointingHandCursor)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(ui_px(4), ui_px(4), ui_px(4), ui_px(3))
        layout.setSpacing(ui_px(2))

        self.icon = QLabel()
        self.icon.setFixedSize(ui_px(64), ui_px(64))
        self.icon.setAlignment(Qt.AlignCenter)
        self.icon.setObjectName("builderSlotIcon")
        layout.addWidget(self.icon, 0, Qt.AlignCenter)

        self.caption = QLabel(SLOT_RU.get(slot, str(slot)))
        self.caption.setObjectName("builderSlotCaption")
        self.caption.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.caption)

        self._apply_style()

    def set_item(
        self,
        decoded_item: DecodedItem | None,
        database: MistfallDatabase | None,
    ) -> None:
        self.decoded_item = decoded_item
        self.database = database
        self.icon.clear()

        grade = 0
        if decoded_item and decoded_item.item:
            grade = int(decoded_item.item.get("g", 0) or 0)
            pixmap = ItemTile._load_local_icon(decoded_item)
            if pixmap is not None:
                size = ui_px(60)
                self.icon.setPixmap(
                    pixmap.scaled(
                        size,
                        size,
                        Qt.KeepAspectRatio,
                        Qt.SmoothTransformation,
                    )
                )
            else:
                self.icon.setText(SLOT_SHORT.get(self.slot, "?"))

            self.setToolTip(
                f"{SLOT_RU.get(self.slot, self.slot)}\n"
                f"{item_name_ru(decoded_item.item, str(decoded_item.cfg))}"
            )
        else:
            self.icon.setText(SLOT_SHORT.get(self.slot, "?"))
            self.setToolTip(SLOT_RU.get(self.slot, str(self.slot)))

        self._grade = grade
        self._apply_style()

    def set_selected(self, selected: bool) -> None:
        self.selected = bool(selected)
        self._apply_style()

    def _apply_style(self) -> None:
        grade = getattr(self, "_grade", 0)
        rarity = RARITY_COLORS.get(grade, "#4b4031")
        background = QColor(rarity)
        background = background.darker(320 if grade else 500)
        border = "#f2efe7" if self.selected else rarity
        width = 2 if self.selected else 1

        self.setStyleSheet(
            f"QFrame#builderSlotTile {{"
            f"background:{background.name()};"
            f"border:{width}px solid {border};"
            f"}}"
            "QLabel#builderSlotIcon { border:none; background:transparent; "
            "color:#d8c7a7; font-size:16px; font-weight:700; }"
            "QLabel#builderSlotCaption { border:none; background:transparent; "
            "color:#8f887c; font-size:9px; }"
        )

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.slot)
        super().mousePressEvent(event)




class BuilderItemChoiceTile(QFrame):
    selected_cfg = Signal(int)

    def __init__(
        self,
        item: dict[str, Any] | None,
        slot: int,
        database: MistfallDatabase | None,
        class_name: str | None,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self.item = item
        self.slot = slot
        self.database = database
        self.class_name = class_name
        self.cfg = int((item or {}).get("id", 0) or 0)
        self.selected = False

        self.setObjectName("builderItemChoice")
        self.setFixedSize(ui_px(104), ui_px(118))
        self.setCursor(Qt.PointingHandCursor)

        root = QVBoxLayout(self)
        root.setContentsMargins(
            ui_px(4), ui_px(4), ui_px(4), ui_px(4)
        )
        root.setSpacing(ui_px(3))

        self.icon = QLabel()
        self.icon.setFixedSize(ui_px(78), ui_px(78))
        self.icon.setAlignment(Qt.AlignCenter)
        self.icon.setObjectName("builderChoiceIcon")
        root.addWidget(self.icon, 0, Qt.AlignCenter)

        if item:
            title_text = item_name_ru(item, str(self.cfg))
        else:
            title_text = "Пусто"

        self.title = QLabel(title_text)
        self.title.setObjectName("builderChoiceName")
        self.title.setAlignment(Qt.AlignCenter)
        self.title.setWordWrap(True)
        self.title.setMaximumHeight(ui_px(28))
        root.addWidget(self.title)

        self._render_icon()
        self._apply_style()

    def _render_icon(self) -> None:
        if not self.item:
            self.icon.setText("—")
            return

        item_copy = dict(self.item)
        if self.class_name:
            item_copy["_class_name"] = self.class_name

        decoded = DecodedItem(
            slot=self.slot,
            cfg=self.cfg,
            item=item_copy,
            gem_ids=[],
            gems=[],
        )
        pixmap = ItemTile._load_local_icon(decoded)
        if pixmap is not None:
            size = ui_px(74)
            self.icon.setPixmap(
                pixmap.scaled(
                    size,
                    size,
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation,
                )
            )
        else:
            self.icon.setText(SLOT_SHORT.get(self.slot, "?"))

        if self.database:
            grade = int(self.item.get("g", 0) or 0)
            innate = (
                ru_affix(str(self.item.get("i")))
                if self.item.get("i")
                else "без врождённого атрибута"
            )
            sockets = len(self.item.get("s") or [])
            variants = len(self.item.get("_variant_cfgs", []) or [])
            variant_text = (
                f"\nВариантов в базе: {variants}"
                if variants > 1
                else ""
            )
            self.setToolTip(
                f"{item_name_ru(self.item, str(self.cfg))}\n"
                f"{self.database.rarity_name(grade)}\n"
                f"{innate}\n"
                f"Слотов самоцветов: {sockets}"
                f"{variant_text}"
            )

    def _apply_style(self) -> None:
        grade = int((self.item or {}).get("g", 0) or 0)
        rarity = RARITY_COLORS.get(grade, "#4b4031")
        background = QColor(rarity)
        background = background.darker(310 if grade else 520)

        border = "#f4f1e9" if self.selected else rarity
        border_width = 2 if self.selected else 1

        self.setStyleSheet(
            f"QFrame#builderItemChoice {{"
            f"background:{background.name()};"
            f"border:{border_width}px solid {border};"
            f"}}"
            "QLabel#builderChoiceIcon {"
            "border:none; background:transparent; color:#cbb58b;"
            "font-size:22px; font-weight:700;"
            "}"
            "QLabel#builderChoiceName {"
            "border:none; background:transparent; color:#bcb3a5;"
            "font-size:9px;"
            "}"
        )

    def set_selected(self, selected: bool) -> None:
        self.selected = bool(selected)
        self._apply_style()

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.LeftButton:
            self.selected_cfg.emit(self.cfg)
        super().mousePressEvent(event)


class BuilderTargetRow(QFrame):
    remove_requested = Signal(object)
    choose_requested = Signal(object)
    changed = Signal()

    def __init__(
        self,
        initial_affix: str | None = None,
        initial_level: int = 1,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self._affix_name = str(initial_affix or "")
        self.setObjectName("builderTargetRow")

        row = QHBoxLayout(self)
        row.setContentsMargins(ui_px(3), ui_px(3), ui_px(3), ui_px(3))
        row.setSpacing(ui_px(6))

        self.icon = QLabel()
        self.icon.setFixedSize(ui_px(42), ui_px(42))
        self.icon.setAlignment(Qt.AlignCenter)
        self.icon.setObjectName("builderTargetIcon")
        row.addWidget(self.icon)

        self.affix_button = QPushButton()
        self.affix_button.setObjectName("targetAffixButton")
        self.affix_button.setCursor(Qt.PointingHandCursor)
        self.affix_button.clicked.connect(
            lambda: self.choose_requested.emit(self)
        )
        row.addWidget(self.affix_button, 1)

        self.level_spin = QSpinBox()
        self.level_spin.setRange(1, 7)
        self.level_spin.setPrefix("Lv. ")
        self.level_spin.setValue(max(1, min(int(initial_level), 7)))
        self.level_spin.setFixedWidth(ui_px(76))
        self.level_spin.valueChanged.connect(
            lambda _value: self.changed.emit()
        )
        row.addWidget(self.level_spin)

        remove = QPushButton("×")
        remove.setObjectName("targetRemoveButton")
        remove.setFixedSize(ui_px(32), ui_px(32))
        remove.clicked.connect(
            lambda: self.remove_requested.emit(self)
        )
        row.addWidget(remove)

        self._refresh_affix()

    def _refresh_affix(self) -> None:
        if self._affix_name:
            setup_affix_icon_label(
                self.icon,
                self._affix_name,
                42,
            )
            self.affix_button.setText(
                ru_affix(self._affix_name)
            )
            self.level_spin.setEnabled(True)
        else:
            self.icon.clear()
            self.icon.setStyleSheet(
                "background:#111411; border:1px solid #3b403a;"
            )
            self.affix_button.setText("Выбрать атрибут")
            self.level_spin.setEnabled(False)

    def set_affix(self, name: str | None) -> None:
        self._affix_name = str(name or "")
        self._refresh_affix()
        self.changed.emit()

    def affix_name(self) -> str:
        return self._affix_name

    def level(self) -> int:
        return int(self.level_spin.value())


class AffixPickerTile(QFrame):
    selected = Signal(str)

    def __init__(
        self,
        affix_name: str,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self.affix_name = affix_name
        self.setObjectName("affixPickerTile")
        self.setFixedSize(ui_px(112), ui_px(88))
        self.setCursor(Qt.PointingHandCursor)

        root = QVBoxLayout(self)
        root.setContentsMargins(ui_px(4), ui_px(4), ui_px(4), ui_px(4))
        root.setSpacing(ui_px(3))

        icon = QLabel()
        setup_affix_icon_label(icon, affix_name, 54)
        root.addWidget(icon, 0, Qt.AlignHCenter)

        title = QLabel(ru_affix(affix_name))
        title.setObjectName("affixPickerTileName")
        title.setAlignment(Qt.AlignHCenter | Qt.AlignTop)
        title.setWordWrap(True)
        root.addWidget(title, 1)

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.LeftButton:
            self.selected.emit(self.affix_name)
        super().mousePressEvent(event)


class AffixPickerOverlay(QFrame):
    affix_selected = Signal(str)
    closed = Signal()

    CATEGORY_ORDER = (
        ("utility", "Поддержка"),
        ("defense", "Защита"),
        ("offense", "Атака"),
    )

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("affixPickerOverlay")
        self.setFixedSize(ui_px(760), ui_px(790))
        self.hide()

        root = QVBoxLayout(self)
        root.setContentsMargins(
            ui_px(16), ui_px(12), ui_px(16), ui_px(14)
        )
        root.setSpacing(ui_px(8))

        header = QHBoxLayout()
        title = QLabel("Выберите атрибут")
        title.setObjectName("affixPickerTitle")
        header.addWidget(title)
        header.addStretch(1)

        close_button = QPushButton("×")
        close_button.setObjectName("affixPickerClose")
        close_button.setFixedSize(ui_px(34), ui_px(34))
        close_button.clicked.connect(self.close_picker)
        header.addWidget(close_button)
        root.addLayout(header)

        subtitle = QLabel(
            "Атрибуты сгруппированы так же, как в игре: "
            "Поддержка, Защита и Атака."
        )
        subtitle.setObjectName("muted")
        root.addWidget(subtitle)

        self.scroll = QScrollArea()
        self.scroll.setObjectName("affixPickerScroll")
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.host = QWidget()
        self.sections = QVBoxLayout(self.host)
        self.sections.setContentsMargins(
            ui_px(4), ui_px(4), ui_px(4), ui_px(8)
        )
        self.sections.setSpacing(ui_px(10))
        self.sections.setAlignment(Qt.AlignTop)
        self.scroll.setWidget(self.host)
        root.addWidget(self.scroll, 1)

    def rebuild(self, affix_names: list[str]) -> None:
        while self.sections.count():
            item = self.sections.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        available = set(affix_names)

        for category, category_title in self.CATEGORY_ORDER:
            names = [
                name
                for name in GAME_AFFIX_ORDER
                if name in available
                and AFFIX_CATEGORY.get(name) == category
            ]
            if not names:
                continue

            section = QFrame()
            section.setObjectName("affixPickerSection")
            section_layout = QVBoxLayout(section)
            section_layout.setContentsMargins(
                ui_px(8), ui_px(6), ui_px(8), ui_px(8)
            )
            section_layout.setSpacing(ui_px(5))

            title = QLabel(category_title)
            title.setObjectName("affixPickerCategoryTitle")
            section_layout.addWidget(title)

            grid_host = QWidget()
            grid = QGridLayout(grid_host)
            grid.setContentsMargins(0, 0, 0, 0)
            grid.setHorizontalSpacing(ui_px(5))
            grid.setVerticalSpacing(ui_px(5))
            grid.setAlignment(Qt.AlignLeft | Qt.AlignTop)

            columns = 5
            for index, name in enumerate(names):
                tile = AffixPickerTile(name)
                tile.selected.connect(self.pick)
                grid.addWidget(
                    tile,
                    index // columns,
                    index % columns,
                )

            section_layout.addWidget(grid_host)
            self.sections.addWidget(section)

        self.sections.addStretch(1)

    def pick(self, name: str) -> None:
        self.affix_selected.emit(name)
        self.hide()

    def close_picker(self) -> None:
        self.hide()
        self.closed.emit()



class BuilderAffixFilterOverlay(QFrame):
    """Visual filter picker for the manual item browser."""

    filter_selected = Signal(str)

    CATEGORY_ORDER = (
        ("utility", "Поддержка"),
        ("defense", "Защита"),
        ("offense", "Атака"),
    )

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("builderAffixFilterOverlay")
        self.setFixedSize(ui_px(690), ui_px(700))
        self.hide()

        root = QVBoxLayout(self)
        root.setContentsMargins(ui_px(14), ui_px(12), ui_px(14), ui_px(14))
        root.setSpacing(ui_px(8))

        header = QHBoxLayout()
        title = QLabel("Фильтр по эффектам")
        title.setObjectName("affixPickerTitle")
        header.addWidget(title)
        header.addStretch(1)

        close_button = QPushButton("×")
        close_button.setObjectName("affixPickerClose")
        close_button.setFixedSize(ui_px(34), ui_px(34))
        close_button.clicked.connect(self.hide)
        header.addWidget(close_button)
        root.addLayout(header)

        quick = QHBoxLayout()
        quick.setSpacing(ui_px(7))

        any_button = QPushButton("Все эффекты")
        any_button.setObjectName("filterQuickButton")
        any_button.clicked.connect(lambda: self.pick("__ANY__"))
        quick.addWidget(any_button)

        none_button = QPushButton("Без врождённого атрибута")
        none_button.setObjectName("filterQuickButton")
        none_button.clicked.connect(lambda: self.pick("__NONE__"))
        quick.addWidget(none_button)
        quick.addStretch(1)
        root.addLayout(quick)

        self.scroll = QScrollArea()
        self.scroll.setObjectName("affixPickerScroll")
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.host = QWidget()
        self.sections = QVBoxLayout(self.host)
        self.sections.setContentsMargins(ui_px(4), ui_px(4), ui_px(4), ui_px(8))
        self.sections.setSpacing(ui_px(9))
        self.sections.setAlignment(Qt.AlignTop)
        self.scroll.setWidget(self.host)
        root.addWidget(self.scroll, 1)

    def rebuild(self, affix_names: list[str]) -> None:
        while self.sections.count():
            item = self.sections.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        available = set(affix_names)
        for category, category_title in self.CATEGORY_ORDER:
            names = [
                name
                for name in GAME_AFFIX_ORDER
                if name in available and AFFIX_CATEGORY.get(name) == category
            ]
            if not names:
                continue

            section = QFrame()
            section.setObjectName("affixPickerSection")
            section_layout = QVBoxLayout(section)
            section_layout.setContentsMargins(ui_px(7), ui_px(6), ui_px(7), ui_px(7))
            section_layout.setSpacing(ui_px(5))

            label = QLabel(category_title)
            label.setObjectName("affixPickerCategoryTitle")
            section_layout.addWidget(label)

            grid_host = QWidget()
            grid = QGridLayout(grid_host)
            grid.setContentsMargins(0, 0, 0, 0)
            grid.setHorizontalSpacing(ui_px(5))
            grid.setVerticalSpacing(ui_px(5))
            grid.setAlignment(Qt.AlignLeft | Qt.AlignTop)

            columns = 5
            for index, name in enumerate(names):
                tile = AffixPickerTile(name)
                tile.selected.connect(self.pick)
                grid.addWidget(tile, index // columns, index % columns)

            section_layout.addWidget(grid_host)
            self.sections.addWidget(section)

        self.sections.addStretch(1)

    def pick(self, value: str) -> None:
        self.filter_selected.emit(value)
        self.hide()




class RarityDiamondButton(QFrame):
    clicked = Signal(int)

    def __init__(
        self,
        grade: int,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self.grade = int(grade)
        self.selected = False

        self.setObjectName("rarityDiamondButton")
        self.setFixedSize(ui_px(42), ui_px(42))
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip(RARITY_RU.get(self.grade, str(self.grade)))

    @staticmethod
    def _diamond(cx: int, cy: int, radius: int) -> QPolygon:
        return QPolygon(
            [
                QPoint(cx, cy - radius),
                QPoint(cx + radius, cy),
                QPoint(cx, cy + radius),
                QPoint(cx - radius, cy),
            ]
        )

    def set_selected(self, selected: bool) -> None:
        self.selected = bool(selected)
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)

        cx = self.width() // 2
        cy = self.height() // 2
        color = QColor(RARITY_COLORS.get(self.grade, "#777777"))

        outer_r = max(ui_px(10), min(self.width(), self.height()) // 2 - ui_px(2))
        frame_r = max(ui_px(8), outer_r - ui_px(3))
        fill_r = max(ui_px(6), outer_r - ui_px(7))
        shine_r = max(ui_px(4), fill_r - ui_px(3))

        # Soft dark outer shadow.
        painter.setBrush(QColor(0, 0, 0, 140))
        painter.setPen(QPen(QColor("#181b19"), max(1, ui_px(2))))
        painter.drawPolygon(
            self._diamond(cx + ui_px(1), cy + ui_px(1), frame_r)
        )

        if self.selected:
            # Game-like white/gold selected frame.
            painter.setBrush(Qt.NoBrush)
            painter.setPen(QPen(QColor("#f2eee6"), max(1, ui_px(2))))
            painter.drawPolygon(self._diamond(cx, cy, outer_r))
            painter.setPen(QPen(QColor("#d2a34b"), max(1, ui_px(2))))
            painter.drawPolygon(self._diamond(cx, cy, frame_r))
        else:
            painter.setBrush(Qt.NoBrush)
            painter.setPen(QPen(QColor("#474c48"), max(1, ui_px(2))))
            painter.drawPolygon(self._diamond(cx, cy, frame_r))

        # Colored rarity gem.
        fill = QColor(color)
        if not self.selected:
            fill = fill.darker(125)

        painter.setBrush(fill)
        edge = QColor(color).lighter(145)
        painter.setPen(QPen(edge, max(1, ui_px(1))))
        painter.drawPolygon(self._diamond(cx, cy, fill_r))

        # Small inner shine.
        shine = QColor(255, 255, 255, 60 if self.selected else 34)
        painter.setBrush(Qt.NoBrush)
        painter.setPen(QPen(shine, max(1, ui_px(1))))
        painter.drawPolygon(
            self._diamond(cx, cy - ui_px(1), shine_r)
        )

        painter.end()

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.grade)
        super().mousePressEvent(event)




class BuilderGemChoiceTile(QFrame):
    selected_gem = Signal(int)

    def __init__(
        self,
        gem: dict[str, Any] | None,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self.gem = gem
        self.gem_id = int((gem or {}).get("id", 0) or 0)
        self.selected = False

        self.setObjectName("builderGemChoice")
        self.setFixedSize(ui_px(94), ui_px(104))
        self.setCursor(Qt.PointingHandCursor)

        root = QVBoxLayout(self)
        root.setContentsMargins(
            ui_px(4), ui_px(4), ui_px(4), ui_px(4)
        )
        root.setSpacing(ui_px(3))

        self.icon = QLabel()
        self.icon.setFixedSize(ui_px(62), ui_px(62))
        self.icon.setAlignment(Qt.AlignCenter)
        self.icon.setObjectName("builderGemIcon")
        root.addWidget(self.icon, 0, Qt.AlignHCenter)

        self.affix_host = QWidget()
        self.affix_layout = QHBoxLayout(self.affix_host)
        self.affix_layout.setContentsMargins(0, 0, 0, 0)
        self.affix_layout.setSpacing(ui_px(3))
        self.affix_layout.setAlignment(Qt.AlignCenter)
        root.addWidget(self.affix_host, 0, Qt.AlignHCenter)

        self.empty_title = QLabel("")
        self.empty_title.setObjectName("builderGemName")
        self.empty_title.setAlignment(Qt.AlignHCenter)
        root.addWidget(self.empty_title)

        self._render()
        self._apply_style()

    def _clear_affix_icons(self) -> None:
        while self.affix_layout.count():
            item = self.affix_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def _render(self) -> None:
        self._clear_affix_icons()

        if not self.gem:
            self.icon.setPixmap(QPixmap())
            self.icon.setText("—")
            self.empty_title.setText("Пусто")
            self.setToolTip("Оставить слот самоцвета пустым")
            return

        self.empty_title.setText("")

        pixmap = gem_icon_pixmap(self.gem, 58)
        if pixmap is not None:
            size = ui_px(58)
            self.icon.setPixmap(
                pixmap.scaled(
                    size,
                    size,
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation,
                )
            )
            self.icon.setText("")
        else:
            self.icon.setPixmap(QPixmap())
            self.icon.setText("◆")

        attrs = [str(a) for a in (self.gem.get("a") or [])]
        rank = int(self.gem.get("l", 0) or 0)

        # No more long "Бесплотность + Братство" captions.
        # Show the actual attribute icons like the game does.
        for name in attrs:
            attr_icon = QLabel()
            setup_affix_icon_label(attr_icon, name, 25)
            attr_icon.setToolTip(ru_affix(name))
            self.affix_layout.addWidget(attr_icon)

        tooltip_lines = [
            gem_name_ru(self.gem, str(self.gem_id)),
            f"Ранг {rank}",
        ]
        if attrs:
            tooltip_lines.append(
                "Атрибуты: "
                + " + ".join(ru_affix(name) for name in attrs)
            )
        self.setToolTip("\\n".join(tooltip_lines))

    def _apply_style(self) -> None:
        if not self.gem:
            border = "#f2eee5" if self.selected else "#4f473b"
            bg = "#0b0b09"
        else:
            rank = int(self.gem.get("l", 0) or 0)
            base = "#81642e" if rank >= 2 else "#4a4e48"
            border = "#f2eee5" if self.selected else base
            bg = "#0b0d0b"

        width = 2 if self.selected else 1
        self.setStyleSheet(
            f"QFrame#builderGemChoice {{"
            f"background:{bg};"
            f"border:{width}px solid {border};"
            f"}}"
            "QLabel#builderGemIcon {"
            "border:none; background:transparent; color:#d8c49b;"
            "font-size:22px;"
            "}"
            "QLabel#builderGemName {"
            "border:none; background:transparent; color:#bcb5aa;"
            "font-size:9px;"
            "}"
        )

    def set_selected(self, selected: bool) -> None:
        self.selected = bool(selected)
        self._apply_style()

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.LeftButton:
            self.selected_gem.emit(self.gem_id)
        super().mousePressEvent(event)




class BuilderSocketSlotCard(QFrame):
    clicked = Signal(int)

    def __init__(
        self,
        socket_index: int,
        socket_type: int,
        socket_level: int,
        gem: dict[str, Any] | None,
        selected: bool = False,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)

        self.socket_index = int(socket_index)
        self.selected = bool(selected)
        self.setObjectName("builderSocketCard")
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(ui_px(104))

        root = QHBoxLayout(self)
        root.setContentsMargins(
            ui_px(8), ui_px(7), ui_px(8), ui_px(7)
        )
        root.setSpacing(ui_px(9))

        icon = QLabel()
        icon.setObjectName("builderSocketCardIcon")
        icon.setFixedSize(ui_px(64), ui_px(64))
        icon.setAlignment(Qt.AlignCenter)

        if gem:
            pm = gem_icon_pixmap(gem, 60)
            if pm is not None:
                icon.setPixmap(
                    pm.scaled(
                        ui_px(60),
                        ui_px(60),
                        Qt.KeepAspectRatio,
                        Qt.SmoothTransformation,
                    )
                )
        else:
            icon.setText("—")

        root.addWidget(icon, 0, Qt.AlignVCenter)

        meta = QVBoxLayout()
        meta.setContentsMargins(0, 0, 0, 0)
        meta.setSpacing(ui_px(3))

        title = QLabel(
            f"Слот {socket_index + 1}"
        )
        title.setObjectName("builderSocketCardTitle")
        meta.addWidget(title)

        subtype = QLabel(
            f"{SOCKET_RU.get(socket_type, 'Самоцвет')} · ранг {socket_level}"
        )
        subtype.setObjectName("builderSocketCardMeta")
        meta.addWidget(subtype)

        if gem:
            meta.addWidget(
                make_gem_affix_icons(
                    gem,
                    icon_size=28,
                    spacing=4,
                ),
                0,
                Qt.AlignLeft,
            )
        else:
            empty = QLabel("Пусто")
            empty.setObjectName("muted")
            meta.addWidget(empty)

        meta.addStretch(1)
        root.addLayout(meta, 1)

        self._apply_style()

    def _apply_style(self) -> None:
        border = "#efe9df" if self.selected else "#343a35"
        glow = "#8b641f" if self.selected else "#101310"
        width = 2 if self.selected else 1

        self.setStyleSheet(
            f"QFrame#builderSocketCard {{"
            f"background:{glow};"
            f"border:{width}px solid {border};"
            f"}}"
            "QLabel#builderSocketCardIcon {"
            "background:#090b09; border:1px solid #353b35;"
            "color:#d7b36d; font-size:28px;"
            "}"
            "QLabel#builderSocketCardTitle {"
            "background:transparent; border:none;"
            "color:#d5bf99; font-family:Georgia;"
            "font-size:13px; font-weight:600;"
            "}"
            "QLabel#builderSocketCardMeta {"
            "background:transparent; border:none;"
            "color:#8f897f; font-size:10px;"
            "}"
        )

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.socket_index)
        super().mousePressEvent(event)


class BuilderGemInventoryRow(QFrame):
    selected_gem = Signal(int)

    def __init__(
        self,
        gem: dict[str, Any] | None,
        selected: bool = False,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)

        self.gem = gem
        self.gem_id = int((gem or {}).get("id", 0) or 0)
        self.selected = bool(selected)

        self.setObjectName("builderGemInventoryRow")
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(ui_px(82))

        root = QHBoxLayout(self)
        root.setContentsMargins(
            ui_px(10), ui_px(8), ui_px(11), ui_px(8)
        )
        root.setSpacing(ui_px(10))

        gem_icon = QLabel()
        gem_icon.setObjectName("builderGemInventoryIcon")
        gem_icon.setFixedSize(ui_px(62), ui_px(62))
        gem_icon.setAlignment(Qt.AlignCenter)

        if gem:
            pm = gem_icon_pixmap(gem, 60)
            if pm is not None:
                gem_icon.setPixmap(
                    pm.scaled(
                        ui_px(60),
                        ui_px(60),
                        Qt.KeepAspectRatio,
                        Qt.SmoothTransformation,
                    )
                )
        else:
            gem_icon.setText("—")

        root.addWidget(gem_icon, 0, Qt.AlignVCenter)

        # Put attribute icons immediately next to the gem image, as in the
        # in-game list. Mixed stones naturally show both icons side by side.
        if gem:
            root.addWidget(
                make_gem_affix_icons(
                    gem,
                    icon_size=34,
                    spacing=4,
                ),
                0,
                Qt.AlignVCenter,
            )

        center = QVBoxLayout()
        center.setContentsMargins(0, 0, 0, 0)
        center.setSpacing(ui_px(4))

        if gem:
            title = QLabel(
                gem_name_ru(gem, str(self.gem_id))
            )
            rank = int(gem.get("l", 0) or 0)
            subtitle_text = f"Самоцвет · ранг {rank}"
        else:
            title = QLabel("Пусто")
            subtitle_text = "Убрать самоцвет из слота"

        title.setObjectName("builderGemInventoryTitle")
        title.setWordWrap(False)
        center.addWidget(title)

        subtitle = QLabel(subtitle_text)
        subtitle.setObjectName("builderGemInventoryMeta")
        center.addWidget(subtitle)

        root.addLayout(center, 1)

        self._apply_style()

    def _apply_style(self) -> None:
        if self.selected:
            border = "#f0eadf"
            bg = "#17130d"
            width = 2
        else:
            border = "#343935"
            bg = "#080a08"
            width = 1

        self.setStyleSheet(
            f"QFrame#builderGemInventoryRow {{"
            f"background:{bg};"
            f"border:{width}px solid {border};"
            f"}}"
            "QFrame#builderGemInventoryRow:hover {"
            "background:#12130f; border:2px solid #e0b35f;"
            "}"
            "QLabel#builderGemInventoryIcon {"
            "background:transparent; border:none;"
            "color:#d7b36d; font-size:28px;"
            "}"
            "QLabel#builderGemInventoryTitle {"
            "background:transparent; border:none;"
            "color:#c8c0b4; font-family:Georgia;"
            "font-size:14px; font-weight:600;"
            "}"
            "QLabel#builderGemInventoryMeta {"
            "background:transparent; border:none;"
            "color:#766f65; font-size:10px;"
            "}"
        )

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.LeftButton:
            self.selected_gem.emit(self.gem_id)
        super().mousePressEvent(event)




class BuildCreatorPage(QWidget):
    apply_edit_requested = Signal(int, str, str, int)
    save_copy_requested = Signal(str, str, int)
    cancel_edit_requested = Signal()

    """
    Visual build creator:
    - direct item selection by thumbnails;
    - requested-attribute auto solver;
    - live Gear Code generation.
    """

    def __init__(self):
        super().__init__()
        self.database: MistfallDatabase | None = None
        self.class_name: str | None = None
        self.active_slot = 10
        self.active_weapon_slot = DEFAULT_ACTIVE_WEAPON_SLOT
        self.auto_rarity_grade = 6
        self.auto_rarity_buttons: dict[int, RarityDiamondButton] = {}

        # Manual item-browser filters. None means "all rarities".
        # __ANY__ / __NONE__ mirror the hidden compatibility combo values.
        self.item_rarity_filter_grade: int | None = None
        self.item_affix_filter = "__ANY__"
        self.item_rarity_filter_buttons: dict[int, RarityDiamondButton] = {}

        self.slot_cfg: dict[int, int] = {
            slot: 0 for slot in DISPLAY_SLOT_ORDER
        }
        self.slot_gems: dict[int, list[int]] = {
            slot: [] for slot in DISPLAY_SLOT_ORDER
        }
        self.slot_tiles: dict[int, BuilderSlotTile] = {}
        self.item_choice_tiles: list[BuilderItemChoiceTile] = []
        self.socket_combos: list[QComboBox] = []
        self.socket_tile_groups: list[list[BuilderGemChoiceTile]] = []
        self.active_socket_index = 0
        self.socket_slot_cards: list[BuilderSocketSlotCard] = []
        self.gem_inventory_rows: list[BuilderGemInventoryRow] = []
        self.target_rows: list[BuilderTargetRow] = []
        self._target_row_for_picker: BuilderTargetRow | None = None
        self._updating_editor = False

        self.editing_build_index: int | None = None
        self.editing_original_name = ""
        self.editing_original_code = ""

        root = QVBoxLayout(self)
        root.setContentsMargins(
            ui_px(22), ui_px(10), ui_px(22), ui_px(16)
        )
        root.setSpacing(ui_px(8))

        header = QHBoxLayout()
        title = QLabel("Создание сборки")
        title.setObjectName("previewTitle")
        header.addWidget(title)
        header.addStretch(1)
        self.class_label = QLabel("Класс не выбран")
        self.class_label.setObjectName("currentClassLabel")
        header.addWidget(self.class_label)
        root.addLayout(header)

        content = QHBoxLayout()
        content.setSpacing(ui_px(12))

        # ====================================================
        # LEFT — equipment
        # ====================================================
        equipment_panel = QFrame()
        equipment_panel.setObjectName("previewPanel")
        equipment_panel.setFixedWidth(ui_px(194))
        equipment_layout = QVBoxLayout(equipment_panel)
        equipment_layout.setContentsMargins(
            ui_px(10), ui_px(10), ui_px(10), ui_px(12)
        )
        equipment_layout.setSpacing(ui_px(7))

        equipment_title = QLabel("Экипировка")
        equipment_title.setObjectName("sectionTitle")
        equipment_layout.addWidget(equipment_title)

        self.equipment_host = QWidget()
        grid = QGridLayout(self.equipment_host)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(ui_px(7))
        grid.setVerticalSpacing(ui_px(7))

        for slot in DISPLAY_SLOT_ORDER:
            tile = BuilderSlotTile(slot)
            tile.clicked.connect(self.select_slot)
            self.slot_tiles[slot] = tile
            row, col, row_span, col_span, alignment = (
                EQUIPMENT_GRID_LAYOUT[slot]
            )
            grid.addWidget(
                tile,
                row,
                col,
                row_span,
                col_span,
                alignment,
            )

        equipment_layout.addWidget(
            self.equipment_host,
            0,
            Qt.AlignHCenter | Qt.AlignTop,
        )
        equipment_layout.addStretch(1)
        content.addWidget(equipment_panel, 0)

        # ====================================================
        # CENTER — visual item selector
        # ====================================================
        editor_panel = QFrame()
        editor_panel.setObjectName("detailsPanel")
        editor_panel.setMinimumWidth(ui_px(690))
        editor_layout = QVBoxLayout(editor_panel)
        editor_layout.setContentsMargins(
            ui_px(14), ui_px(11), ui_px(14), ui_px(12)
        )
        editor_layout.setSpacing(ui_px(6))

        self.slot_title = QLabel("Оружие I")
        self.slot_title.setObjectName("sectionTitle")
        editor_layout.addWidget(self.slot_title)

        # Hidden compatibility combos remain as an internal model.
        # The visible UI below uses game-like rarity diamonds and a visual
        # effect picker instead of long dropdown lists.
        self.rarity_combo = QComboBox(editor_panel)
        self.rarity_combo.hide()

        self.affix_combo = QComboBox(editor_panel)
        self.affix_combo.hide()

        # Game-like manual filters: rarity diamonds + effect picker.
        self.item_filter_bar = QFrame()
        self.item_filter_bar.setObjectName("builderItemFilterBar")
        filter_bar_layout = QHBoxLayout(self.item_filter_bar)
        filter_bar_layout.setContentsMargins(0, 0, 0, 0)
        filter_bar_layout.setSpacing(ui_px(7))

        rarity_filter_panel = QFrame()
        rarity_filter_panel.setObjectName("builderFilterGroup")
        rarity_filter_layout = QHBoxLayout(rarity_filter_panel)
        rarity_filter_layout.setContentsMargins(
            ui_px(10), ui_px(4), ui_px(8), ui_px(4)
        )
        rarity_filter_layout.setSpacing(ui_px(1))

        rarity_filter_title = QLabel("Редкость")
        rarity_filter_title.setObjectName("builderFilterTitle")
        rarity_filter_layout.addWidget(rarity_filter_title)
        rarity_filter_layout.addSpacing(ui_px(8))

        for grade in range(1, 8):
            button = RarityDiamondButton(grade)
            button.setFixedSize(ui_px(34), ui_px(34))
            button.clicked.connect(self.set_item_rarity_filter)
            self.item_rarity_filter_buttons[grade] = button
            rarity_filter_layout.addWidget(button)

        rarity_filter_layout.addStretch(1)
        filter_bar_layout.addWidget(rarity_filter_panel, 1)

        effect_filter_panel = QFrame()
        effect_filter_panel.setObjectName("builderFilterGroup")
        effect_filter_layout = QHBoxLayout(effect_filter_panel)
        effect_filter_layout.setContentsMargins(
            ui_px(8), ui_px(4), ui_px(8), ui_px(4)
        )
        effect_filter_layout.setSpacing(ui_px(6))

        self.item_effect_filter_icon = QLabel()
        self.item_effect_filter_icon.setFixedSize(ui_px(30), ui_px(30))
        self.item_effect_filter_icon.setAlignment(Qt.AlignCenter)
        self.item_effect_filter_icon.setVisible(False)
        effect_filter_layout.addWidget(self.item_effect_filter_icon)

        self.item_effect_filter_button = QPushButton("Эффекты атрибутов  ▾")
        self.item_effect_filter_button.setObjectName("builderEffectFilterButton")
        self.item_effect_filter_button.clicked.connect(
            self.show_item_affix_filter_picker
        )
        effect_filter_layout.addWidget(self.item_effect_filter_button, 1)

        self.item_effect_clear_button = QPushButton("×")
        self.item_effect_clear_button.setObjectName("builderFilterClearButton")
        self.item_effect_clear_button.setFixedSize(ui_px(30), ui_px(30))
        self.item_effect_clear_button.setToolTip("Сбросить фильтр эффекта")
        self.item_effect_clear_button.clicked.connect(
            lambda: self.set_item_affix_filter("__ANY__")
        )
        self.item_effect_clear_button.hide()
        effect_filter_layout.addWidget(self.item_effect_clear_button)

        effect_filter_panel.setMinimumWidth(ui_px(270))
        filter_bar_layout.addWidget(effect_filter_panel, 0)

        editor_layout.addWidget(self.item_filter_bar)

        self.item_scroll = QScrollArea()
        self.item_scroll.setObjectName("builderItemScroll")
        self.item_scroll.setWidgetResizable(True)
        self.item_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarAsNeeded
        )
        self.item_scroll.setVerticalScrollBarPolicy(
            Qt.ScrollBarAlwaysOff
        )
        self.item_scroll.setFixedHeight(ui_px(136))

        self.item_grid_host = QWidget()
        self.item_grid = QGridLayout(self.item_grid_host)
        self.item_grid.setContentsMargins(
            ui_px(5), ui_px(5), ui_px(5), ui_px(5)
        )
        self.item_grid.setHorizontalSpacing(ui_px(7))
        self.item_grid.setVerticalSpacing(ui_px(7))
        self.item_grid.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.item_scroll.setWidget(self.item_grid_host)
        editor_layout.addWidget(self.item_scroll)

        socket_title = QLabel(
            "Самоцветы / дополнительные атрибуты"
        )
        socket_title.setObjectName("builderFieldLabel")
        editor_layout.addWidget(socket_title)

        self.sockets_host = QFrame()
        self.sockets_host.setObjectName("builderSocketWorkspace")
        self.sockets_layout = QHBoxLayout(self.sockets_host)
        self.sockets_layout.setContentsMargins(
            ui_px(6), ui_px(6), ui_px(6), ui_px(6)
        )
        self.sockets_layout.setSpacing(ui_px(8))
        editor_layout.addWidget(self.sockets_host, 1)

        content.addWidget(editor_panel, 1)

        # ====================================================
        # RIGHT — tabbed attributes panel
        # ====================================================
        attr_panel = QFrame()
        attr_panel.setObjectName("detailsPanel")
        attr_panel.setFixedWidth(ui_px(420))

        attr_outer = QVBoxLayout(attr_panel)
        attr_outer.setContentsMargins(
            ui_px(7), ui_px(7), ui_px(7), ui_px(7)
        )
        attr_outer.setSpacing(0)

        self.creator_side_tabs = QTabWidget()
        self.creator_side_tabs.setObjectName("creatorSideTabs")
        self.creator_side_tabs.setDocumentMode(True)
        self.creator_side_tabs.tabBar().setExpanding(True)
        self.creator_side_tabs.tabBar().setDrawBase(False)
        self.creator_side_tabs.tabBar().setUsesScrollButtons(False)
        attr_outer.addWidget(self.creator_side_tabs)

        # ----------------------------------------------------
        # Tab 1: auto pick
        # ----------------------------------------------------
        auto_tab = QWidget()
        auto_layout = QVBoxLayout(auto_tab)
        auto_layout.setContentsMargins(
            ui_px(8), ui_px(8), ui_px(8), ui_px(8)
        )
        auto_layout.setSpacing(ui_px(6))

        target_header = QHBoxLayout()
        target_title = QLabel("Автоподбор атрибутов")
        target_title.setObjectName("sectionTitle")
        target_header.addWidget(target_title)
        target_header.addStretch(1)

        add_target_button = QPushButton("＋")
        add_target_button.setObjectName("targetAddButton")
        add_target_button.setToolTip(
            "Добавить желаемый атрибут"
        )
        add_target_button.setFixedSize(ui_px(34), ui_px(34))
        add_target_button.clicked.connect(self.add_target_row)
        target_header.addWidget(add_target_button)
        auto_layout.addLayout(target_header)

        target_help = QLabel(
            "Задай нужные уровни. Программа сама подберёт "
            "реальные предметы и самоцветы."
        )
        target_help.setObjectName("muted")
        target_help.setWordWrap(True)
        auto_layout.addWidget(target_help)

        rarity_panel = QFrame()
        rarity_panel.setObjectName("autoRarityPanel")
        rarity_layout = QHBoxLayout(rarity_panel)
        rarity_layout.setContentsMargins(
            ui_px(7), ui_px(5), ui_px(7), ui_px(5)
        )
        rarity_layout.setSpacing(ui_px(2))

        rarity_title = QLabel("Редкость")
        rarity_title.setObjectName("autoRarityTitle")
        rarity_layout.addWidget(rarity_title)
        rarity_layout.addSpacing(ui_px(8))

        # User requested the practical set range:
        # green Rare -> blue Excellent -> purple Epic -> gold Legendary.
        for grade in (3, 4, 5, 6):
            button = RarityDiamondButton(grade)
            button.setFixedSize(ui_px(38), ui_px(38))
            button.clicked.connect(self.set_auto_rarity)
            self.auto_rarity_buttons[grade] = button
            rarity_layout.addWidget(button)

        rarity_layout.addSpacing(ui_px(8))

        self.auto_rarity_name_label = QLabel("Легендарный")
        self.auto_rarity_name_label.setObjectName("autoRarityName")
        self.auto_rarity_name_label.setMinimumWidth(ui_px(92))
        self.auto_rarity_name_label.setAlignment(
            Qt.AlignVCenter | Qt.AlignLeft
        )
        rarity_layout.addWidget(self.auto_rarity_name_label, 1)

        auto_layout.addWidget(rarity_panel)
        self._refresh_auto_rarity_buttons()

        self.include_second_weapon = QCheckBox("Добавлять второе оружие")
        self.include_second_weapon.setObjectName("secondWeaponCheck")
        self.include_second_weapon.setChecked(False)
        self.include_second_weapon.setToolTip(
            "По умолчанию автоподбор использует только активное оружие. "
            "Второй слот останется пустым."
        )
        auto_layout.addWidget(self.include_second_weapon)

        self.target_scroll = QScrollArea()
        self.target_scroll.setObjectName("builderTargetScroll")
        self.target_scroll.setWidgetResizable(True)
        self.target_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarAlwaysOff
        )
        self.target_scroll.setMinimumHeight(ui_px(220))

        self.target_host = QWidget()
        self.target_layout = QVBoxLayout(self.target_host)
        self.target_layout.setContentsMargins(
            0, ui_px(2), 0, ui_px(2)
        )
        self.target_layout.setSpacing(ui_px(6))
        self.target_layout.setAlignment(Qt.AlignTop)
        self.target_scroll.setWidget(self.target_host)
        auto_layout.addWidget(self.target_scroll, 1)

        auto_pick = QPushButton("Подобрать сборку")
        auto_pick.setObjectName("goldButton")
        auto_pick.clicked.connect(self.auto_pick_build)
        auto_layout.addWidget(auto_pick)

        self.auto_status = QLabel("")
        self.auto_status.setObjectName("muted")
        self.auto_status.setWordWrap(True)
        auto_layout.addWidget(self.auto_status)

        self.creator_side_tabs.addTab(auto_tab, "Автоподбор")

        # ----------------------------------------------------
        # Tab 2: resulting attributes
        # ----------------------------------------------------
        result_tab = QWidget()
        result_layout = QVBoxLayout(result_tab)
        result_layout.setContentsMargins(
            ui_px(8), ui_px(8), ui_px(8), ui_px(8)
        )
        result_layout.setSpacing(ui_px(6))

        attr_header = QHBoxLayout()
        attr_title = QLabel("Итоговые атрибуты")
        attr_title.setObjectName("sectionTitle")
        attr_header.addWidget(attr_title)
        attr_header.addStretch(1)

        self.creator_weapon_buttons: dict[int, QPushButton] = {}
        for slot, caption in ((10, "I"), (11, "II")):
            button = QPushButton(caption)
            button.setObjectName("weaponToggle")
            button.setCheckable(True)
            button.setFixedSize(ui_px(30), ui_px(24))
            button.clicked.connect(
                lambda _checked=False, s=slot:
                self.set_active_weapon(s)
            )
            self.creator_weapon_buttons[slot] = button
            attr_header.addWidget(button)

        result_layout.addLayout(attr_header)

        self.creator_attr_scroll = QScrollArea()
        self.creator_attr_scroll.setObjectName("creatorAttrScroll")
        self.creator_attr_scroll.setWidgetResizable(True)
        self.creator_attr_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarAlwaysOff
        )

        self.creator_attr_host = QWidget()
        self.creator_attr_layout = QVBoxLayout(
            self.creator_attr_host
        )
        self.creator_attr_layout.setContentsMargins(0, 0, 0, 0)
        self.creator_attr_layout.setSpacing(ui_px(3))
        self.creator_attr_layout.setAlignment(Qt.AlignTop)
        self.creator_attr_scroll.setWidget(self.creator_attr_host)
        result_layout.addWidget(self.creator_attr_scroll, 1)

        self.creator_side_tabs.addTab(result_tab, "Итоговые")

        content.addWidget(attr_panel, 0)
        root.addLayout(content, 1)

        # ====================================================
        # Generated code
        # ====================================================
        code_panel = QFrame()
        code_panel.setObjectName("importBox")
        code_layout = QVBoxLayout(code_panel)
        code_layout.setContentsMargins(
            ui_px(14), ui_px(9), ui_px(14), ui_px(9)
        )
        code_layout.setSpacing(ui_px(5))

        code_title = QLabel("Готовый код сборки")
        code_title.setObjectName("sectionTitle")
        code_layout.addWidget(code_title)

        code_row = QHBoxLayout()
        self.generated_code = QLineEdit()
        self.generated_code.setReadOnly(True)
        self.generated_code.setPlaceholderText(
            "Код появится автоматически после выбора класса"
        )
        code_row.addWidget(self.generated_code, 1)

        copy_button = QPushButton("Копировать код")
        copy_button.setObjectName("goldButton")
        copy_button.clicked.connect(
            self.copy_generated_code
        )
        code_row.addWidget(copy_button)

        reset_button = QPushButton("Сбросить сборку")
        reset_button.clicked.connect(self.reset_build)
        code_row.addWidget(reset_button)

        code_layout.addLayout(code_row)

        # ----------------------------------------------------
        # Editing an existing saved build
        # ----------------------------------------------------
        self.edit_mode_panel = QFrame()
        self.edit_mode_panel.setObjectName("creatorEditPanel")
        edit_mode_layout = QHBoxLayout(self.edit_mode_panel)
        edit_mode_layout.setContentsMargins(
            ui_px(8), ui_px(7), ui_px(8), ui_px(7)
        )
        edit_mode_layout.setSpacing(ui_px(7))

        self.edit_mode_label = QLabel("Редактирование сборки")
        self.edit_mode_label.setObjectName("creatorEditLabel")
        edit_mode_layout.addWidget(self.edit_mode_label)

        self.edit_name = QLineEdit()
        self.edit_name.setPlaceholderText("Название сборки")
        self.edit_name.setMinimumWidth(ui_px(250))
        edit_mode_layout.addWidget(self.edit_name, 1)

        self.apply_edit_button = QPushButton("Применить изменения")
        self.apply_edit_button.setObjectName("goldButton")
        self.apply_edit_button.clicked.connect(
            self.apply_current_edit
        )
        edit_mode_layout.addWidget(self.apply_edit_button)

        self.save_copy_button = QPushButton("Сохранить отдельно")
        self.save_copy_button.setObjectName("secondaryButton")
        self.save_copy_button.clicked.connect(
            self.save_current_as_copy
        )
        edit_mode_layout.addWidget(self.save_copy_button)

        self.cancel_edit_button = QPushButton("Отмена")
        self.cancel_edit_button.setObjectName("secondaryButton")
        self.cancel_edit_button.clicked.connect(
            self.cancel_edit_requested.emit
        )
        edit_mode_layout.addWidget(self.cancel_edit_button)

        self.edit_mode_panel.setVisible(False)
        code_layout.addWidget(self.edit_mode_panel)

        self.creator_status = QLabel(
            "Выбери предметы вручную или используй автоподбор."
        )
        self.creator_status.setObjectName("muted")
        code_layout.addWidget(self.creator_status)

        root.addWidget(code_panel)

        # Встроенный выбор атрибута — не отдельное окно.
        self.affix_picker = AffixPickerOverlay(self)
        self.affix_picker.affix_selected.connect(
            self._affix_picker_selected
        )

        # Отдельный визуальный выбор эффекта для фильтра предметов.
        self.item_affix_filter_picker = BuilderAffixFilterOverlay(self)
        self.item_affix_filter_picker.filter_selected.connect(
            self.set_item_affix_filter
        )

        self._refresh_item_filter_ui()
        self.select_slot(10)

    # --------------------------------------------------------
    # State
    # --------------------------------------------------------
    def set_state(
        self,
        database: MistfallDatabase | None,
        class_name: str | None,
    ) -> None:
        class_changed = class_name != self.class_name
        self.database = database
        self.class_name = class_name

        self.class_label.setText(
            CLASS_RU.get(
                class_name or "",
                class_name or "Класс не выбран",
            )
        )

        if class_changed:
            self.finish_edit_mode()
            self.item_rarity_filter_grade = None
            self.item_affix_filter = "__ANY__"
            self.slot_cfg = {
                slot: 0 for slot in DISPLAY_SLOT_ORDER
            }
            self.slot_gems = {
                slot: [] for slot in DISPLAY_SLOT_ORDER
            }
            self.active_slot = 10
            self._clear_target_rows()

        if self.database:
            self.affix_picker.rebuild(
                self._available_affixes()
            )
            self.item_affix_filter_picker.rebuild(
                self._available_affixes()
            )

        self._refresh_editor()
        self._update_generated()

    def _class_items(
        self,
        slot: int,
    ) -> list[dict[str, Any]]:
        if not self.database or not self.class_name:
            return []
        try:
            return self.database.class_slot_items(
                self.class_name,
                slot,
            )
        except Exception:
            return []

    # --------------------------------------------------------
    # Existing build editing
    # --------------------------------------------------------
    def load_build_for_edit(
        self,
        index: int,
        name: str,
        code: str,
        weapon_slot: int = DEFAULT_ACTIVE_WEAPON_SLOT,
    ) -> DecodedBuild:
        if not self.database:
            raise ValueError("База предметов ещё не загружена")

        if weapon_slot not in WEAPON_SLOTS:
            weapon_slot = DEFAULT_ACTIVE_WEAPON_SLOT

        decoded = self.database.decode(code, weapon_slot)

        # If this build belongs to another class, initialize the creator
        # with that class first, then load all actual cfg/gem values.
        self.set_state(self.database, decoded.class_name)

        self.slot_cfg = {
            slot: 0 for slot in DISPLAY_SLOT_ORDER
        }
        self.slot_gems = {
            slot: [] for slot in DISPLAY_SLOT_ORDER
        }

        for decoded_item in decoded.items:
            if decoded_item.slot not in self.slot_cfg:
                continue
            self.slot_cfg[decoded_item.slot] = int(
                decoded_item.cfg or 0
            )
            self.slot_gems[decoded_item.slot] = list(
                decoded_item.gem_ids
            )

        self.active_weapon_slot = weapon_slot
        self.active_slot = 10

        self.editing_build_index = int(index)
        self.editing_original_name = str(name or "Без названия")
        self.editing_original_code = clean_code(code)

        self.edit_name.setText(self.editing_original_name)
        self.edit_mode_label.setText(
            f"Редактируется: {self.editing_original_name}"
        )
        self.edit_mode_panel.setVisible(True)

        self._clear_target_rows()
        self.select_slot(10)
        self._refresh_editor()
        self._update_generated()

        self.creator_status.setText(
            "Сборка загружена для редактирования. "
            "После изменений можно обновить оригинал "
            "или сохранить отдельную копию."
        )
        return decoded

    def finish_edit_mode(self) -> None:
        self.editing_build_index = None
        self.editing_original_name = ""
        self.editing_original_code = ""
        if hasattr(self, "edit_name"):
            self.edit_name.clear()
        if hasattr(self, "edit_mode_panel"):
            self.edit_mode_panel.setVisible(False)

    def apply_current_edit(self) -> None:
        if self.editing_build_index is None:
            return

        code = clean_code(self.generated_code.text())
        if not code:
            self.creator_status.setText(
                "Не удалось получить код изменённой сборки."
            )
            return

        name = (
            self.edit_name.text().strip()
            or self.editing_original_name
            or "Без названия"
        )
        self.apply_edit_requested.emit(
            self.editing_build_index,
            name,
            code,
            self.active_weapon_slot,
        )

    def save_current_as_copy(self) -> None:
        if self.editing_build_index is None:
            return

        code = clean_code(self.generated_code.text())
        if not code:
            self.creator_status.setText(
                "Не удалось получить код изменённой сборки."
            )
            return

        typed_name = self.edit_name.text().strip()
        if (
            not typed_name
            or typed_name == self.editing_original_name
        ):
            typed_name = (
                (self.editing_original_name or "Сборка")
                + " (копия)"
            )

        self.save_copy_requested.emit(
            typed_name,
            code,
            self.active_weapon_slot,
        )

    # --------------------------------------------------------
    # Slot / manual item selection
    # --------------------------------------------------------
    def select_slot(self, slot: int) -> None:
        if slot not in DISPLAY_SLOT_ORDER:
            return

        self.active_slot = slot
        for current_slot, tile in self.slot_tiles.items():
            tile.set_selected(current_slot == slot)
        self._refresh_editor()

    def _refresh_editor(self) -> None:
        self._updating_editor = True
        try:
            self.slot_title.setText(
                SLOT_RU.get(
                    self.active_slot,
                    str(self.active_slot),
                )
            )

            items = self._class_items(self.active_slot)
            selected_cfg = int(
                self.slot_cfg.get(self.active_slot, 0) or 0
            )
            selected_item = next(
                (
                    item for item in items
                    if int(item.get("id", 0) or 0)
                    == selected_cfg
                ),
                None,
            )

            grades = sorted(
                {
                    int(item.get("g", 0) or 0)
                    for item in items
                    if int(item.get("g", 0) or 0)
                }
            )

            selected_grade = (
                int(selected_item.get("g", 0) or 0)
                if selected_item
                else None
            )

            self.rarity_combo.blockSignals(True)
            self.rarity_combo.clear()
            self.rarity_combo.addItem(
                "Все редкости",
                None,
            )
            for grade in grades:
                self.rarity_combo.addItem(
                    (
                        self.database.rarity_name(grade)
                        if self.database
                        else str(grade)
                    ),
                    grade,
                )

            rarity_index = self.rarity_combo.findData(
                self.item_rarity_filter_grade
            )
            if rarity_index < 0:
                rarity_index = 0
            self.rarity_combo.setCurrentIndex(rarity_index)
            self.rarity_combo.blockSignals(False)

            self._populate_affixes_and_items(
                selected_cfg
            )

            self._refresh_item_filter_ui()
            self._render_sockets()
        finally:
            self._updating_editor = False

    def _populate_affixes_and_items(
        self,
        selected_cfg: int = 0,
    ) -> None:
        items = self._class_items(self.active_slot)
        grade = self.item_rarity_filter_grade

        if grade is not None:
            items = [
                item for item in items
                if int(item.get("g", 0) or 0)
                == int(grade)
            ]

        selected_item = next(
            (
                item for item in items
                if int(item.get("id", 0) or 0)
                == int(selected_cfg or 0)
            ),
            None,
        )

        selected_affix = self.item_affix_filter

        affixes = sorted(
            {
                str(item.get("i"))
                for item in items
                if item.get("i")
            },
            key=ru_affix,
        )
        has_none = any(not item.get("i") for item in items)

        self.affix_combo.blockSignals(True)
        self.affix_combo.clear()
        self.affix_combo.addItem(
            "Любой атрибут",
            "__ANY__",
        )
        if has_none:
            self.affix_combo.addItem(
                "Без врождённого атрибута",
                "__NONE__",
            )
        for affix in affixes:
            self.affix_combo.addItem(
                ru_affix(affix),
                affix,
            )

        affix_index = self.affix_combo.findData(
            selected_affix
        )
        if affix_index < 0:
            self.item_affix_filter = "__ANY__"
            affix_index = self.affix_combo.findData("__ANY__")
        if affix_index >= 0:
            self.affix_combo.setCurrentIndex(affix_index)
        self.affix_combo.blockSignals(False)

        self._populate_items(selected_cfg)
        self._refresh_item_filter_ui()

    def _populate_items(
        self,
        selected_cfg: int = 0,
    ) -> None:
        items = self._class_items(self.active_slot)
        grade = self.item_rarity_filter_grade
        affix_filter = self.item_affix_filter

        if grade is not None:
            items = [
                item for item in items
                if int(item.get("g", 0) or 0)
                == int(grade)
            ]

        if affix_filter == "__NONE__":
            items = [
                item for item in items
                if not item.get("i")
            ]
        elif affix_filter not in (
            None,
            "__ANY__",
        ):
            items = [
                item for item in items
                if str(item.get("i", ""))
                == str(affix_filter)
            ]

        # The database contains many cfg variants of the SAME visible item
        # (different innate affix/socket layout). Showing every cfg created
        # 8-9 identical tiles. Group them by base name + rarity instead.
        grouped: dict[
            tuple[str, int],
            list[dict[str, Any]],
        ] = {}

        for item in items:
            item_name = item_name_ru(
                item,
                str(item.get("id", "")),
            )
            item_grade = int(item.get("g", 0) or 0)
            grouped.setdefault(
                (item_name, item_grade),
                [],
            ).append(item)

        selected_cfg = int(selected_cfg or 0)
        visual_items: list[dict[str, Any]] = []

        for (_name, _grade), variants in grouped.items():
            selected_variant = next(
                (
                    item
                    for item in variants
                    if int(item.get("id", 0) or 0)
                    == selected_cfg
                ),
                None,
            )

            # If there is no existing selection, prefer the neutral 3-socket
            # variant; otherwise use the first real variant matching filters.
            representative = selected_variant
            if representative is None:
                representative = next(
                    (
                        item
                        for item in variants
                        if not item.get("i")
                    ),
                    variants[0],
                )

            representative = dict(representative)
            representative["_variant_cfgs"] = [
                int(item.get("id", 0) or 0)
                for item in variants
            ]
            visual_items.append(representative)

        visual_items.sort(
            key=lambda item: (
                -int(item.get("g", 0) or 0),
                item_name_ru(
                    item,
                    str(item.get("id", "")),
                ),
            )
        )

        self._render_item_choices(
            visual_items,
            selected_cfg,
        )


    def _clear_grid(
        self,
        grid: QGridLayout,
    ) -> None:
        while grid.count():
            item = grid.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def _render_item_choices(
        self,
        items: list[dict[str, Any]],
        selected_cfg: int,
    ) -> None:
        self._clear_grid(self.item_grid)
        self.item_choice_tiles = []

        choices: list[
            tuple[dict[str, Any] | None, int]
        ] = [(None, 0)]
        choices.extend(
            (item, int(item.get("id", 0) or 0))
            for item in items
        )

        # One continuous row. No wrapping to the second line.
        for index, (item, cfg) in enumerate(choices):
            tile = BuilderItemChoiceTile(
                item,
                self.active_slot,
                self.database,
                self.class_name,
            )

            variant_cfgs = (
                list(item.get("_variant_cfgs", []))
                if item
                else [0]
            )
            tile.set_selected(
                selected_cfg in variant_cfgs
            )
            tile.selected_cfg.connect(
                self._select_item_cfg
            )
            self.item_choice_tiles.append(tile)
            self.item_grid.addWidget(
                tile,
                0,
                index,
            )

        tile_w = ui_px(104)
        gap = ui_px(7)
        total_width = (
            len(choices) * tile_w
            + max(0, len(choices) - 1) * gap
            + ui_px(12)
        )
        self.item_grid_host.setMinimumWidth(total_width)
        self.item_grid_host.setMinimumHeight(ui_px(124))

        for column in range(len(choices)):
            self.item_grid.setColumnStretch(column, 0)


    def _select_item_cfg(self, cfg: int) -> None:
        self.slot_cfg[self.active_slot] = int(cfg or 0)
        self.slot_gems[self.active_slot] = []
        self.active_socket_index = 0
        self._refresh_editor()
        self._update_generated()

    def set_item_rarity_filter(self, grade: int) -> None:
        grade = int(grade)
        # Re-clicking the selected rarity returns to the game-like "all" state.
        if self.item_rarity_filter_grade == grade:
            self.item_rarity_filter_grade = None
        else:
            self.item_rarity_filter_grade = grade
        self._filters_changed()

    def set_item_affix_filter(self, value: str) -> None:
        value = str(value or "__ANY__")
        if value not in {"__ANY__", "__NONE__"} and value not in self._available_affixes():
            value = "__ANY__"
        self.item_affix_filter = value
        self._filters_changed()

    def _refresh_item_filter_ui(self) -> None:
        for grade, button in self.item_rarity_filter_buttons.items():
            button.set_selected(grade == self.item_rarity_filter_grade)

        value = self.item_affix_filter
        self.item_effect_filter_icon.clear()
        self.item_effect_filter_icon.setPixmap(QPixmap())
        self.item_effect_filter_icon.setVisible(False)

        if value == "__ANY__":
            self.item_effect_filter_button.setText("Эффекты атрибутов  ▾")
            self.item_effect_filter_button.setToolTip("Показывать предметы с любым врождённым эффектом")
            self.item_effect_clear_button.hide()
        elif value == "__NONE__":
            self.item_effect_filter_button.setText("Без врождённого  ▾")
            self.item_effect_filter_button.setToolTip("Показывать варианты без врождённого атрибута")
            self.item_effect_clear_button.show()
        else:
            self.item_effect_filter_button.setText(f"{ru_affix(value)}  ▾")
            self.item_effect_filter_button.setToolTip(
                f"Фильтр: {ru_affix(value)}"
            )
            setup_affix_icon_label(
                self.item_effect_filter_icon,
                value,
                30,
            )
            self.item_effect_filter_icon.setVisible(True)
            self.item_effect_clear_button.show()

    def show_item_affix_filter_picker(self) -> None:
        self.item_affix_filter_picker.rebuild(
            self._available_affixes()
        )
        self._center_item_affix_filter_picker()
        self.item_affix_filter_picker.show()
        self.item_affix_filter_picker.raise_()

    def _center_item_affix_filter_picker(self) -> None:
        if not hasattr(self, "item_affix_filter_picker"):
            return
        x = max(0, (self.width() - self.item_affix_filter_picker.width()) // 2)
        y = max(0, (self.height() - self.item_affix_filter_picker.height()) // 2)
        self.item_affix_filter_picker.move(x, y)

    def _filters_changed(self) -> None:
        if self._updating_editor:
            return

        self._updating_editor = True
        try:
            # Keep the legacy hidden combos synchronized for old helper code.
            rarity_index = self.rarity_combo.findData(self.item_rarity_filter_grade)
            if rarity_index >= 0:
                self.rarity_combo.setCurrentIndex(rarity_index)
            self._populate_affixes_and_items(
                int(
                    self.slot_cfg.get(
                        self.active_slot,
                        0,
                    ) or 0
                )
            )
            self._refresh_item_filter_ui()
        finally:
            self._updating_editor = False

    def _affix_changed(self) -> None:
        if self._updating_editor:
            return

        self._updating_editor = True
        try:
            self._populate_items(
                int(
                    self.slot_cfg.get(
                        self.active_slot,
                        0,
                    ) or 0
                )
            )
        finally:
            self._updating_editor = False

    # --------------------------------------------------------
    # Sockets
    # --------------------------------------------------------
    def _clear_layout(self, layout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
                continue

            child_layout = item.layout()
            if child_layout is not None:
                self._clear_layout(child_layout)
                child_layout.deleteLater()

    def _render_sockets(self) -> None:
        self._clear_layout(self.sockets_layout)
        self.socket_combos = []
        self.socket_tile_groups = []
        self.socket_slot_cards = []
        self.gem_inventory_rows = []

        if not self.database:
            return

        cfg = int(
            self.slot_cfg.get(self.active_slot, 0) or 0
        )
        item = (
            self.database.item_by_id.get(cfg)
            if cfg
            else None
        )
        sockets = list((item or {}).get("s") or [])

        if not sockets:
            label = QLabel(
                "У выбранного варианта нет слотов "
                "для самоцветов."
            )
            label.setObjectName("muted")
            label.setWordWrap(True)
            self.sockets_layout.addWidget(label)
            self.sockets_layout.addStretch(1)
            return

        if self.active_socket_index < 0:
            self.active_socket_index = 0
        if self.active_socket_index >= len(sockets):
            self.active_socket_index = len(sockets) - 1

        current_gems = list(
            self.slot_gems.get(
                self.active_slot,
                [],
            )
        )

        # ----------------------------------------------------
        # LEFT: equipped socket list, like the game UI
        # ----------------------------------------------------
        rail = QFrame()
        rail.setObjectName("builderSocketRail")
        rail.setFixedWidth(ui_px(226))

        rail_layout = QVBoxLayout(rail)
        rail_layout.setContentsMargins(
            ui_px(6), ui_px(6), ui_px(6), ui_px(6)
        )
        rail_layout.setSpacing(ui_px(6))

        rail_title = QLabel("Экипировано")
        rail_title.setObjectName("builderSocketPaneTitle")
        rail_layout.addWidget(rail_title)

        for socket_index, socket in enumerate(sockets):
            try:
                socket_type = int(socket[0])
                socket_level = int(socket[1])
            except Exception:
                socket_type = 0
                socket_level = 0

            gem_id = (
                int(current_gems[socket_index])
                if socket_index < len(current_gems)
                else 0
            )
            gem = (
                self.database.gem_by_id.get(gem_id)
                if gem_id
                else None
            )

            card = BuilderSocketSlotCard(
                socket_index,
                socket_type,
                socket_level,
                gem,
                socket_index == self.active_socket_index,
            )
            card.clicked.connect(self._select_socket_index)
            self.socket_slot_cards.append(card)
            rail_layout.addWidget(card)

        rail_layout.addStretch(1)
        self.sockets_layout.addWidget(rail, 0)

        # ----------------------------------------------------
        # RIGHT: compatible gem inventory, vertical list
        # ----------------------------------------------------
        browser = QFrame()
        browser.setObjectName("builderGemBrowser")
        browser_layout = QVBoxLayout(browser)
        browser_layout.setContentsMargins(
            ui_px(7), ui_px(7), ui_px(7), ui_px(7)
        )
        browser_layout.setSpacing(ui_px(6))

        active_socket = sockets[self.active_socket_index]
        try:
            socket_type = int(active_socket[0])
            socket_level = int(active_socket[1])
        except Exception:
            socket_type = 0
            socket_level = 0

        browser_header = QHBoxLayout()
        browser_header.setSpacing(ui_px(6))

        browser_title = QLabel(
            f"Выбор самоцвета · "
            f"{SOCKET_RU.get(socket_type, 'Самоцвет')} "
            f"· ранг {socket_level}"
        )
        browser_title.setObjectName("builderSocketPaneTitle")
        browser_header.addWidget(browser_title)
        browser_header.addStretch(1)

        count_label = QLabel("")
        count_label.setObjectName("muted")
        browser_header.addWidget(count_label)
        browser_layout.addLayout(browser_header)

        scroll = QScrollArea()
        scroll.setObjectName("builderGemInventoryScroll")
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarAlwaysOff
        )
        scroll.setVerticalScrollBarPolicy(
            Qt.ScrollBarAsNeeded
        )

        host = QWidget()
        host.setObjectName("builderGemInventoryHost")
        gem_list = QVBoxLayout(host)
        gem_list.setContentsMargins(
            ui_px(3), ui_px(3), ui_px(3), ui_px(3)
        )
        gem_list.setSpacing(ui_px(6))
        gem_list.setAlignment(Qt.AlignTop)

        selected_gem = (
            int(current_gems[self.active_socket_index])
            if self.active_socket_index < len(current_gems)
            else 0
        )

        empty_row = BuilderGemInventoryRow(
            None,
            selected_gem == 0,
        )
        empty_row.selected_gem.connect(
            lambda gem_id, i=self.active_socket_index:
            self._socket_changed(i, gem_id)
        )
        self.gem_inventory_rows.append(empty_row)
        gem_list.addWidget(empty_row)

        compatible = self.database.compatible_gems(
            socket_type,
            socket_level,
        )
        compatible.sort(
            key=lambda gem: (
                -int(gem.get("l", 0) or 0),
                " + ".join(
                    ru_affix(str(a))
                    for a in (gem.get("a") or [])
                ),
                int(gem.get("id", 0) or 0),
            )
        )

        for gem in compatible:
            gem_id = int(gem.get("id", 0) or 0)
            row = BuilderGemInventoryRow(
                gem,
                gem_id == selected_gem,
            )
            row.selected_gem.connect(
                lambda selected_id, i=self.active_socket_index:
                self._socket_changed(i, selected_id)
            )
            self.gem_inventory_rows.append(row)
            gem_list.addWidget(row)

        gem_list.addStretch(1)
        count_label.setText(f"{len(compatible)} вариантов")
        scroll.setWidget(host)
        browser_layout.addWidget(scroll, 1)

        self.sockets_layout.addWidget(browser, 1)

    def _select_socket_index(self, socket_index: int) -> None:
        self.active_socket_index = int(socket_index)
        self._render_sockets()


    def _socket_changed(
        self,
        socket_index: int,
        gem_id: int,
    ) -> None:
        gems = list(
            self.slot_gems.get(
                self.active_slot,
                [],
            )
        )
        while len(gems) <= socket_index:
            gems.append(0)

        gems[socket_index] = int(gem_id or 0)
        self.slot_gems[self.active_slot] = gems
        self._render_sockets()
        self._update_generated()

    # --------------------------------------------------------
    # Auto-build rarity
    # --------------------------------------------------------
    def set_auto_rarity(self, grade: int) -> None:
        grade = int(grade)
        if grade not in (3, 4, 5, 6):
            return

        self.auto_rarity_grade = grade
        self._refresh_auto_rarity_buttons()
        self._target_changed()

    def _refresh_auto_rarity_buttons(self) -> None:
        for grade, button in self.auto_rarity_buttons.items():
            button.set_selected(grade == self.auto_rarity_grade)

        if hasattr(self, "auto_rarity_name_label"):
            self.auto_rarity_name_label.setText(
                RARITY_RU.get(
                    self.auto_rarity_grade,
                    str(self.auto_rarity_grade),
                )
            )
            self.auto_rarity_name_label.setStyleSheet(
                "color:"
                + RARITY_COLORS.get(
                    self.auto_rarity_grade,
                    "#c8b28d",
                )
                + ";"
            )

    # --------------------------------------------------------
    # Desired-attribute rows / auto solver
    # --------------------------------------------------------
    def _available_affixes(self) -> list[str]:
        if not self.database:
            return []

        raw_affixes = set(
            str(name)
            for name in self.database.data.get(
                "affixes",
                {},
            )
        )

        result = [
            name
            for name in GAME_AFFIX_ORDER
            if name in raw_affixes
        ]
        result.extend(
            sorted(
                raw_affixes - set(result),
                key=ru_affix,
            )
        )
        return result

    def add_target_row(
        self,
        affix: str | None = None,
        level: int = 1,
    ) -> None:
        if not self.database:
            return

        row = BuilderTargetRow(
            affix,
            level,
        )
        row.remove_requested.connect(
            self.remove_target_row
        )
        row.choose_requested.connect(
            self.show_affix_picker
        )
        row.changed.connect(
            self._target_changed
        )

        self.target_rows.append(row)
        self.target_layout.addWidget(row)
        self._target_changed()

    def show_affix_picker(
        self,
        row: BuilderTargetRow,
    ) -> None:
        self._target_row_for_picker = row
        self.affix_picker.rebuild(
            self._available_affixes()
        )
        self._center_affix_picker()
        self.affix_picker.show()
        self.affix_picker.raise_()

    def _affix_picker_selected(
        self,
        name: str,
    ) -> None:
        row = self._target_row_for_picker
        self._target_row_for_picker = None

        if row is None or row not in self.target_rows:
            return

        row.set_affix(name)

    def _center_affix_picker(self) -> None:
        if not hasattr(self, "affix_picker"):
            return

        x = max(
            0,
            (self.width() - self.affix_picker.width()) // 2,
        )
        y = max(
            0,
            (self.height() - self.affix_picker.height()) // 2,
        )
        self.affix_picker.move(x, y)

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        if (
            hasattr(self, "affix_picker")
            and self.affix_picker.isVisible()
        ):
            self._center_affix_picker()
        if (
            hasattr(self, "item_affix_filter_picker")
            and self.item_affix_filter_picker.isVisible()
        ):
            self._center_item_affix_filter_picker()


    def remove_target_row(
        self,
        row: BuilderTargetRow,
    ) -> None:
        if row not in self.target_rows:
            return

        if self._target_row_for_picker is row:
            self._target_row_for_picker = None
            self.affix_picker.hide()

        self.target_rows.remove(row)
        self.target_layout.removeWidget(row)
        row.deleteLater()
        self._target_changed()

    def _clear_target_rows(self) -> None:
        for row in list(self.target_rows):
            self.target_layout.removeWidget(row)
            row.deleteLater()
        self.target_rows.clear()

    def _target_changed(self) -> None:
        targets = self.requested_attributes()
        rarity_name = RARITY_RU.get(
            self.auto_rarity_grade,
            str(self.auto_rarity_grade),
        )

        if not targets:
            self.auto_status.setText(
                f"Редкость: {rarity_name}. Желаемые атрибуты не заданы."
            )
            return

        parts = [
            f"{ru_affix(name)} Lv.{level}"
            for name, level in targets.items()
        ]
        self.auto_status.setText(
            f"Редкость: {rarity_name} · Нужно: " + " · ".join(parts)
        )

    def requested_attributes(self) -> dict[str, int]:
        result: dict[str, int] = {}

        for row in self.target_rows:
            name = row.affix_name()
            if not name:
                continue
            result[name] = max(
                result.get(name, 0),
                row.level(),
            )

        return result

    def auto_pick_build(self) -> None:
        if not self.database or not self.class_name:
            self.auto_status.setText(
                "Сначала выбери класс."
            )
            return

        targets = self.requested_attributes()
        if not targets:
            self.auto_status.setText(
                "Добавь хотя бы один желаемый атрибут."
            )
            return

        self.auto_status.setText(
            "Подбираю предметы и самоцветы…"
        )
        QApplication.processEvents()

        try:
            result = self.database.auto_build_for_attributes(
                self.class_name,
                targets,
                self.active_weapon_slot,
                self.include_second_weapon.isChecked(),
                self.auto_rarity_grade,
            )
        except Exception as exc:
            self.auto_status.setText(
                f"Автоподбор не удался: {exc}"
            )
            return

        self.slot_cfg = {
            slot: int(result["slot_cfg"].get(slot, 0) or 0)
            for slot in DISPLAY_SLOT_ORDER
        }
        self.slot_gems = {
            slot: list(
                result["slot_gems"].get(slot, [])
            )
            for slot in DISPLAY_SLOT_ORDER
        }

        self._refresh_editor()
        decoded = self._update_generated()

        if decoded is None:
            self.auto_status.setText(
                "Сборка подобрана, но код не удалось проверить."
            )
            return

        missing: list[str] = []
        for name, requested_level in targets.items():
            actual_level = int(
                decoded.attributes.get(name, 0)
            )
            if actual_level < requested_level:
                missing.append(
                    f"{ru_affix(name)} "
                    f"{actual_level}/{requested_level}"
                )

        if missing:
            rarity_name = RARITY_RU.get(
                self.auto_rarity_grade,
                str(self.auto_rarity_grade),
            )
            self.auto_status.setText(
                f"{rarity_name}: точное сочетание не найдено. "
                "Подобран максимально близкий вариант: "
                + ", ".join(missing)
            )
        else:
            target_text = " · ".join(
                f"{ru_affix(name)} Lv."
                f"{int(decoded.attributes.get(name, 0))}"
                for name in targets
            )
            rarity_name = RARITY_RU.get(
                self.auto_rarity_grade,
                str(self.auto_rarity_grade),
            )
            self.auto_status.setText(
                f"Подобрано [{rarity_name}]: " + target_text
            )

    # --------------------------------------------------------
    # Build state
    # --------------------------------------------------------
    def clear_active_slot(self) -> None:
        self.slot_cfg[self.active_slot] = 0
        self.slot_gems[self.active_slot] = []
        self._refresh_editor()
        self._update_generated()

    def reset_build(self) -> None:
        self.slot_cfg = {
            slot: 0 for slot in DISPLAY_SLOT_ORDER
        }
        self.slot_gems = {
            slot: [] for slot in DISPLAY_SLOT_ORDER
        }
        self._refresh_editor()
        self._update_generated()
        self.auto_status.setText("")

    def set_active_weapon(
        self,
        weapon_slot: int,
    ) -> None:
        if weapon_slot not in WEAPON_SLOTS:
            return

        self.active_weapon_slot = weapon_slot
        self._update_generated()

    def _update_generated(
        self,
    ) -> DecodedBuild | None:
        self._clear_layout(self.creator_attr_layout)

        for slot, button in (
            self.creator_weapon_buttons.items()
        ):
            button.blockSignals(True)
            button.setChecked(
                slot == self.active_weapon_slot
            )
            button.blockSignals(False)

        if not self.database or not self.class_name:
            self.generated_code.clear()
            self.creator_status.setText(
                "Сначала выбери класс."
            )
            for tile in self.slot_tiles.values():
                tile.set_item(
                    None,
                    self.database,
                )
            return None

        try:
            code = self.database.encode(
                self.class_name,
                self.slot_cfg,
                self.slot_gems,
            )
            decoded = self.database.decode(
                code,
                self.active_weapon_slot,
            )
        except Exception as exc:
            self.generated_code.clear()
            self.creator_status.setText(
                f"Ошибка генерации: {exc}"
            )
            self.creator_status.setObjectName(
                "errorText"
            )
            self.creator_status.style().unpolish(
                self.creator_status
            )
            self.creator_status.style().polish(
                self.creator_status
            )
            return None

        self.generated_code.setText(code)
        self.creator_status.setText(
            "Код обновляется автоматически "
            "после каждого изменения."
        )
        self.creator_status.setObjectName(
            "successText"
        )
        self.creator_status.style().unpolish(
            self.creator_status
        )
        self.creator_status.style().polish(
            self.creator_status
        )

        by_slot = {
            item.slot: item
            for item in decoded.items
        }
        for slot, tile in self.slot_tiles.items():
            tile.set_item(
                by_slot.get(slot),
                self.database,
            )
            tile.set_selected(
                slot == self.active_slot
            )

        if decoded.attributes:
            for name, level in sorted(
                decoded.attributes.items(),
                key=lambda pair: (
                    -pair[1],
                    ru_affix(pair[0]),
                ),
            ):
                self.creator_attr_layout.addWidget(
                    AttributeRow(
                        name,
                        level,
                        self.database,
                        compact=True,
                    )
                )
        else:
            label = QLabel(
                "Пока нет активных атрибутов"
            )
            label.setObjectName("muted")
            self.creator_attr_layout.addWidget(label)

        return decoded

    def copy_generated_code(self) -> None:
        code = clean_code(
            self.generated_code.text()
        )
        if not code:
            return

        QApplication.clipboard().setText(code)
        self.creator_status.setText(
            "Код сборки скопирован в буфер обмена."
        )


class MainTabs(QTabBar):
    pass


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.resize(ui_px(1610), ui_px(1250))
        self.setMinimumSize(1060, 720)

        self._centered_once = False

        self.repo = BuildRepository(BUILDS_FILE)
        self.active_class: str | None = None
        self.database: MistfallDatabase | None = None
        self.download_thread: DatabaseDownloadThread | None = None

        self._build_ui()
        self._load_initial_database()
        self.refresh_pages()
        self.show_class_selection()

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        if self._centered_once:
            return
        self._centered_once = True
        self.center_on_screen()

    def center_on_screen(self) -> None:
        screen = QApplication.primaryScreen()
        if screen is None:
            return

        available = screen.availableGeometry()
        frame = self.frameGeometry()
        frame.moveCenter(available.center())
        self.move(frame.topLeft())

    def _build_ui(self) -> None:
        central = QWidget()
        central.setObjectName("root")
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(ui_px(28), ui_px(18), ui_px(28), ui_px(14))
        root.setSpacing(0)

        title = QLabel("Изменить сборку")
        title.setAlignment(Qt.AlignCenter)
        title.setObjectName("mainTitle")

        title_glow = QGraphicsDropShadowEffect(title)
        title_glow.setBlurRadius(ui_px(22))
        title_glow.setOffset(0, 0)
        title_glow.setColor(QColor(225, 142, 24, 150))
        title.setGraphicsEffect(title_glow)

        root.addWidget(title)

        self.title_ornament = AccentLine()
        root.addWidget(self.title_ornament)

        class_row = QHBoxLayout()
        class_row.setContentsMargins(0, 0, 0, ui_px(4))
        class_row.setSpacing(ui_px(8))

        self.change_class_button = QPushButton("← Сменить класс")
        self.change_class_button.setObjectName("changeClassButton")
        self.change_class_button.clicked.connect(self.show_class_selection)
        class_row.addWidget(self.change_class_button)

        self.current_class_label = QLabel("Класс не выбран")
        self.current_class_label.setObjectName("currentClassLabel")
        class_row.addWidget(self.current_class_label)

        class_row.addStretch(1)
        root.addLayout(class_row)

        tab_row = QHBoxLayout()
        tab_row.addStretch(1)
        self.tab_saved = QPushButton("Мои сборки")
        self.tab_import = QPushButton("Импорт сборки")
        self.tab_creator = QPushButton("Создание сборки")
        for button in (self.tab_saved, self.tab_import, self.tab_creator):
            button.setObjectName("tabButton")
            button.setCheckable(True)
            button.setAutoExclusive(True)
            button.setMinimumWidth(ui_px(180))
            button.setFixedHeight(ui_px(52))
        self.tab_saved.setChecked(True)
        self.tab_saved.clicked.connect(lambda: self._set_page(0))
        self.tab_import.clicked.connect(lambda: self._set_page(1))
        self.tab_creator.clicked.connect(lambda: self._set_page(3))
        tab_row.addWidget(self.tab_saved)
        tab_row.addWidget(self.tab_import)
        tab_row.addWidget(self.tab_creator)
        tab_row.addStretch(1)
        root.addLayout(tab_row)

        self.stack = QStackedWidget()
        self.saved_page = SavedBuildsPage()
        self.import_page = ImportPage()
        self.class_select_page = ClassSelectPage()
        self.creator_page = BuildCreatorPage()

        self.stack.addWidget(self.saved_page)          # 0
        self.stack.addWidget(self.import_page)         # 1
        self.stack.addWidget(self.class_select_page)   # 2
        self.stack.addWidget(self.creator_page)        # 3
        root.addWidget(self.stack, 1)

        self.saved_page.copy_requested.connect(self.copy_build)
        self.saved_page.edit_requested.connect(self.edit_build)
        self.saved_page.creator_edit_requested.connect(
            self.open_build_in_creator
        )
        self.saved_page.delete_requested.connect(self.delete_build)
        self.saved_page.details_requested.connect(self.show_details)
        self.saved_page.refresh_data_requested.connect(lambda: self.download_database(manual=True))
        self.saved_page.affix_catalog_requested.connect(self.show_affix_catalog)
        self.saved_page.weapon_requested.connect(self.set_build_weapon)
        self.import_page.save_requested.connect(self.add_build)
        self.class_select_page.class_selected.connect(self.select_class)

        self.creator_page.apply_edit_requested.connect(
            self.apply_creator_edit
        )
        self.creator_page.save_copy_requested.connect(
            self.save_creator_copy
        )
        self.creator_page.cancel_edit_requested.connect(
            self.cancel_creator_edit
        )

        footer = QHBoxLayout()
        self.status_label = QLabel("Готово")
        self.status_label.setObjectName("muted")
        self.count_label = QLabel()
        self.count_label.setObjectName("muted")
        open_folder = QPushButton("Папка данных")
        open_folder.setObjectName("linkButton")
        open_folder.clicked.connect(self.open_data_folder)
        footer.addWidget(self.status_label)
        footer.addStretch(1)
        footer.addWidget(self.count_label)
        footer.addWidget(open_folder)
        root.addLayout(footer)

    def _sync_build_classes(self) -> None:
        """Миграция старого builds.json: дописывает класс, расшифровав код."""
        if not self.database:
            return

        changed = False
        for build in self.repo.builds:
            if build.get("class_name"):
                continue
            try:
                decoded = self.database.decode(
                    build["code"],
                    int(build.get("weapon_slot", DEFAULT_ACTIVE_WEAPON_SLOT)),
                )
            except Exception:
                continue
            build["class_name"] = decoded.class_name
            changed = True

        if changed:
            self.repo.save()

    def _set_class_navigation_visible(self, visible: bool) -> None:
        self.change_class_button.setVisible(visible)
        self.current_class_label.setVisible(visible)
        self.tab_saved.setVisible(visible)
        self.tab_import.setVisible(visible)
        self.tab_creator.setVisible(visible)

    def show_class_selection(self) -> None:
        """Показывает выбор класса прямо внутри главного окна."""
        self._sync_build_classes()
        self.class_select_page.set_state(self.repo, self.active_class)
        self._set_class_navigation_visible(False)
        self.stack.setCurrentIndex(2)

    def select_class(self, class_name: str) -> None:
        self.active_class = class_name
        self.current_class_label.setText(
            CLASS_RU.get(self.active_class, self.active_class)
        )
        self._set_class_navigation_visible(True)
        self.search_class_hint()
        self.refresh_pages()
        self._set_page(0)

    def search_class_hint(self) -> None:
        if not hasattr(self, "saved_page"):
            return
        class_text = CLASS_RU.get(self.active_class or "", self.active_class or "")
        if class_text:
            self.saved_page.search.setPlaceholderText(
                f"Поиск в сборках класса «{class_text}»…"
            )
        else:
            self.saved_page.search.setPlaceholderText(
                "Поиск по названию, коду или атрибутам…"
            )

    def _set_page(self, index: int) -> None:
        self.stack.setCurrentIndex(index)
        self.tab_saved.setChecked(index == 0)
        self.tab_import.setChecked(index == 1)
        self.tab_creator.setChecked(index == 3)

    def _load_initial_database(self) -> None:
        candidates = [CACHE_DATA_FILE, BUNDLED_DATA_FILE]
        for path in candidates:
            if not path.exists():
                continue
            try:
                self.database = MistfallDatabase(load_json_file(path))
                self.status_label.setText(f"База предметов: {path.name}")
                return
            except Exception:
                continue
        self.status_label.setText("Загрузка базы предметов…")
        self.download_database(manual=False)

    def download_database(self, manual: bool) -> None:
        if self.download_thread and self.download_thread.isRunning():
            if manual:
                self.status_label.setText("База уже загружается…")
            return
        self.status_label.setText("Обновление базы предметов…")
        self.download_thread = DatabaseDownloadThread(self)
        self.download_thread.loaded.connect(self._database_downloaded)
        self.download_thread.failed.connect(self._database_failed)
        self.download_thread.start()

    def _database_downloaded(self, data: dict, source: str) -> None:
        try:
            CACHE_DATA_FILE.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        except Exception:
            pass
        self.database = MistfallDatabase(data)
        self.status_label.setText("База предметов обновлена")
        self.refresh_pages()

    def _database_failed(self, error: str) -> None:
        if self.database:
            self.status_label.setText("Не удалось обновить базу — используется локальная копия")
        else:
            self.status_label.setText("Не удалось загрузить базу предметов")
            QMessageBox.warning(
                self,
                "База предметов",
                "Не удалось загрузить данные Mistfall Builder.\n\n"
                "Положи mistfall_data.json рядом со скриптом или проверь интернет.\n\n"
                + error,
            )
        self.refresh_pages()

    def refresh_pages(self) -> None:
        self._sync_build_classes()
        self.saved_page.set_state(self.repo, self.database, self.active_class)
        self.import_page.set_database(self.database)
        self.creator_page.set_state(self.database, self.active_class)
        if hasattr(self, "class_select_page"):
            self.class_select_page.set_state(self.repo, self.active_class)

        if self.active_class:
            class_count = sum(
                1 for build in self.repo.builds
                if build.get("class_name") == self.active_class
            )
            self.count_label.setText(
                f"{CLASS_RU.get(self.active_class, self.active_class)}: {class_count} сборок"
            )
        else:
            self.count_label.setText(f"Всего сохранено: {len(self.repo.builds)}")

    def add_build(self, name: str, code: str, weapon_slot: int = DEFAULT_ACTIVE_WEAPON_SLOT) -> bool:
        code = clean_code(code)
        if any(build["code"] == code for build in self.repo.builds):
            QMessageBox.information(self, "Уже сохранено", "Такая сборка уже есть в списке.")
            return False

        decoded: DecodedBuild | None = None
        class_name = ""
        if self.database:
            try:
                decoded = self.database.decode(code, weapon_slot)
                class_name = decoded.class_name
            except Exception as exc:
                QMessageBox.warning(self, "Неверный код", str(exc))
                return False

        self.repo.add(name, code, weapon_slot, class_name)

        if class_name and class_name != self.active_class:
            self.active_class = class_name
            self.current_class_label.setText(CLASS_RU.get(class_name, class_name))
            self._set_class_navigation_visible(True)
            self.search_class_hint()

        self.refresh_pages()
        class_text = CLASS_RU.get(class_name, class_name) if class_name else ""
        self.status_label.setText(
            f"Сохранено: {name}" + (f" · {class_text}" if class_text else "")
        )
        self._set_page(0)
        return True

    def open_build_in_creator(self, index: int) -> None:
        if not self.database:
            QMessageBox.information(
                self,
                "Редактирование",
                "Сначала должна загрузиться база предметов.",
            )
            return
        if not 0 <= index < len(self.repo.builds):
            return

        build = self.repo.builds[index]
        weapon_slot = int(
            build.get(
                "weapon_slot",
                DEFAULT_ACTIVE_WEAPON_SLOT,
            )
        )
        if weapon_slot not in WEAPON_SLOTS:
            weapon_slot = DEFAULT_ACTIVE_WEAPON_SLOT

        try:
            decoded = self.database.decode(
                build["code"],
                weapon_slot,
            )
        except Exception as exc:
            QMessageBox.warning(
                self,
                "Не удалось открыть редактор",
                str(exc),
            )
            return

        if decoded.class_name != self.active_class:
            self.active_class = decoded.class_name
            self.current_class_label.setText(
                CLASS_RU.get(
                    decoded.class_name,
                    decoded.class_name,
                )
            )
            self._set_class_navigation_visible(True)
            self.search_class_hint()
            self.refresh_pages()

        try:
            self.creator_page.load_build_for_edit(
                index,
                build.get("name", "Без названия"),
                build["code"],
                weapon_slot,
            )
        except Exception as exc:
            QMessageBox.warning(
                self,
                "Не удалось открыть редактор",
                str(exc),
            )
            return

        self._set_page(3)
        self.status_label.setText(
            f"Редактирование: {build.get('name', 'Без названия')}"
        )

    def apply_creator_edit(
        self,
        index: int,
        name: str,
        code: str,
        weapon_slot: int,
    ) -> None:
        if not 0 <= index < len(self.repo.builds):
            QMessageBox.warning(
                self,
                "Редактирование",
                "Исходная сборка больше не существует.",
            )
            return

        code = clean_code(code)

        for other_index, build in enumerate(self.repo.builds):
            if other_index == index:
                continue
            if clean_code(build.get("code", "")) == code:
                QMessageBox.information(
                    self,
                    "Такая сборка уже сохранена",
                    "Получившийся код уже используется другой "
                    "сохранённой сборкой.",
                )
                return

        if not self.database:
            return

        try:
            decoded = self.database.decode(code, weapon_slot)
        except Exception as exc:
            QMessageBox.warning(
                self,
                "Неверный код",
                str(exc),
            )
            return

        self.repo.update(
            index,
            name,
            code,
            decoded.class_name,
            weapon_slot,
        )

        self.active_class = decoded.class_name
        self.current_class_label.setText(
            CLASS_RU.get(
                decoded.class_name,
                decoded.class_name,
            )
        )
        self.creator_page.finish_edit_mode()
        self.refresh_pages()
        self.search_class_hint()
        self.status_label.setText(
            f"Изменения применены: {name}"
        )
        self._set_page(0)

    def save_creator_copy(
        self,
        name: str,
        code: str,
        weapon_slot: int,
    ) -> None:
        if self.add_build(name, code, weapon_slot):
            self.creator_page.finish_edit_mode()
            self.status_label.setText(
                f"Сохранена отдельная сборка: {name}"
            )

    def cancel_creator_edit(self) -> None:
        self.creator_page.finish_edit_mode()
        self.refresh_pages()
        self.status_label.setText("Редактирование отменено")
        self._set_page(0)

    def copy_build(self, index: int) -> None:
        if not 0 <= index < len(self.repo.builds):
            return
        build = self.repo.builds[index]
        QApplication.clipboard().setText(build["code"])
        self.status_label.setText(f"Код «{build['name']}» скопирован")

    def edit_build(self, index: int) -> None:
        if not 0 <= index < len(self.repo.builds):
            return
        build = self.repo.builds[index]
        dialog = EditBuildDialog(build["name"], build["code"], self)
        if dialog.exec() != QDialog.Accepted:
            return
        name = dialog.name_edit.text().strip() or build["name"]
        code = clean_code(dialog.code_edit.text())
        if self.database:
            try:
                self.database.decode(code)
            except Exception as exc:
                QMessageBox.warning(self, "Неверный код", str(exc))
                return
        class_name = str(build.get("class_name", "") or "")
        if self.database:
            try:
                decoded = self.database.decode(
                    code,
                    int(build.get("weapon_slot", DEFAULT_ACTIVE_WEAPON_SLOT)),
                )
                class_name = decoded.class_name
            except Exception:
                pass

        self.repo.update(index, name, code, class_name)
        if class_name and class_name != self.active_class:
            self.active_class = class_name
            self.current_class_label.setText(CLASS_RU.get(class_name, class_name))
            self._set_class_navigation_visible(True)
            self.search_class_hint()

        self.refresh_pages()
        self.status_label.setText(f"Изменено: {name}")

    def delete_build(self, index: int) -> None:
        if not 0 <= index < len(self.repo.builds):
            return
        build = self.repo.builds[index]
        answer = QMessageBox.question(
            self,
            "Удалить сборку",
            f"Удалить «{build['name']}»?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return
        self.repo.delete(index)
        self.refresh_pages()
        self.status_label.setText("Сборка удалена")

    def set_build_weapon(self, index: int, weapon_slot: int) -> None:
        if not 0 <= index < len(self.repo.builds):
            return
        if weapon_slot not in WEAPON_SLOTS:
            return
        self.repo.set_weapon_slot(index, weapon_slot)
        self.refresh_pages()
        label = "I" if weapon_slot == 10 else "II"
        self.status_label.setText(f"Активное оружие сборки: {label}")

    def show_affix_catalog(self) -> None:
        if not self.database:
            QMessageBox.information(self, "Все атрибуты", "Сначала должна загрузиться база предметов.")
            return
        AffixCatalogDialog(self.database, self).exec()

    def show_details(self, index: int) -> None:
        if not self.database:
            QMessageBox.information(self, "Сведения", "Сначала должна загрузиться база предметов.")
            return
        if not 0 <= index < len(self.repo.builds):
            return
        build = self.repo.builds[index]
        try:
            decoded = self.database.decode(build["code"], int(build.get("weapon_slot", DEFAULT_ACTIVE_WEAPON_SLOT)))
        except Exception as exc:
            QMessageBox.warning(self, "Не удалось расшифровать", str(exc))
            return
        BuildDetailsDialog(build["name"], decoded, self.database, self).exec()

    def open_data_folder(self) -> None:
        try:
            if os.name == "nt":
                os.startfile(APP_DIR)  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                os.system(f'open "{APP_DIR}"')
            else:
                os.system(f'xdg-open "{APP_DIR}"')
        except Exception as exc:
            QMessageBox.warning(self, "Папка данных", str(exc))


STYLE = r"""
QWidget#root {
    background: #080b09;
    color: #bdb7ac;
}
QWidget {
    font-family: "Segoe UI";
    font-size: 14px;
    color: #bbb6ac;
}
QLabel#mainTitle {
    font-family: Georgia, "Times New Roman";
    font-size: 38px;
    font-weight: 600;
    color: #efb74e;
    padding: 5px 0 0 0;
}
QLabel#dialogTitle, QLabel#previewTitle {
    font-family: Georgia, "Times New Roman";
    font-size: 25px;
    font-weight: 600;
    color: #ddaa57;
}
QLabel#sectionTitle {
    font-family: Georgia, "Times New Roman";
    font-size: 18px;
    font-weight: 600;
    color: #c99752;
}
QLabel#buildTitle {
    font-family: Georgia, "Times New Roman";
    font-size: 19px;
    color: #b99b70;
}
QLabel#buildMeta {
    color: #837d71;
    font-size: 12px;
}
QLabel#gold { color: #d5a353; font-weight: 600; }
QLabel#muted { color: #716d65; }
QLabel#errorText { color: #c0665f; }
QLabel#successText { color: #76a871; }
QLabel#emptyState {
    color: #6e6a61;
    font-size: 18px;
    padding: 90px;
}
QFrame#creatorEditPanel {
    background: #100d08;
    border: 1px solid #7b5626;
}
QLabel#creatorEditLabel {
    color: #e1b35d;
    font-family: Georgia, "Times New Roman";
    font-size: 13px;
    font-weight: 600;
}
QPushButton#squareAction[editor="true"] {
    color: #e2af5d;
}
QPushButton#squareAction[editor="true"]:hover {
    border-color: #e1b15d;
    color: #f4d99f;
}

QFrame#autoRarityPanel {
    background: #080907;
    border: 1px solid #4c3a24;
}
QLabel#autoRarityTitle {
    color: #b89461;
    font-family: Georgia, "Times New Roman";
    font-size: 17px;
    font-weight: 600;
}
QLabel#autoRarityName {
    font-family: Georgia, "Times New Roman";
    font-size: 12px;
    font-weight: 600;
    padding-left: 2px;
}
QFrame#rarityDiamondButton {
    background: transparent;
    border: none;
}
QFrame#builderItemFilterBar {
    background: transparent;
    border: none;
}
QFrame#builderFilterGroup {
    background: #090b09;
    border: 1px solid #4a3722;
}
QLabel#builderFilterTitle {
    background: transparent;
    border: none;
    color: #b78d55;
    font-family: Georgia, "Times New Roman";
    font-size: 17px;
    font-weight: 600;
}
QPushButton#builderEffectFilterButton {
    background: transparent;
    border: none;
    color: #a8865e;
    text-align: left;
    padding: 5px 7px;
    font-family: Georgia, "Times New Roman";
    font-size: 15px;
}
QPushButton#builderEffectFilterButton:hover {
    color: #e4b967;
}
QPushButton#builderFilterClearButton {
    background: #15110c;
    border: 1px solid #5f4427;
    color: #c8914c;
    font-size: 18px;
    padding: 0;
}
QPushButton#builderFilterClearButton:hover {
    border-color: #e8dfd1;
    color: white;
}
QFrame#builderAffixFilterOverlay {
    background: #050706;
    border: 2px solid #80602e;
}
QPushButton#filterQuickButton {
    background: #0e0d0a;
    border: 1px solid #5a4328;
    color: #c8a16a;
    padding: 7px 11px;
    font-family: Georgia, "Times New Roman";
    font-size: 13px;
}
QPushButton#filterQuickButton:hover {
    border-color: #ece6da;
    color: #f4eee4;
}

QTabWidget#creatorSideTabs::pane {
    background: #070907;
    border: 1px solid #343128;
    border-top: none;
    top: 0px;
}
QTabWidget#creatorSideTabs QTabBar {
    background: #070907;
    border: none;
}
QTabWidget#creatorSideTabs QTabBar::tab {
    background: #0a0b09;
    color: #847a69;
    border: none;
    border-bottom: 1px solid #3d352a;
    padding: 9px 12px;
    font-family: Georgia, "Times New Roman";
    font-size: 14px;
}
QTabWidget#creatorSideTabs QTabBar::tab:selected {
    color: #e5b763;
    background: #11100c;
    border-bottom: 2px solid #a36a17;
}
QTabWidget#creatorSideTabs QTabBar::tab:hover {
    color: #d2b37e;
    background: #0e0f0c;
}
QWidget#gemAffixIcons {
    background: transparent;
    border: none;
}
QFrame#builderSocketWorkspace {
    background: #070907;
    border: 1px solid #2b302c;
}
QFrame#builderSocketRail {
    background: #0a0c0a;
    border: 1px solid #34382f;
}
QFrame#builderGemBrowser {
    background: #070907;
    border: 1px solid #34382f;
}
QLabel#builderSocketPaneTitle {
    background: transparent;
    border: none;
    color: #c5a16a;
    font-family: Georgia, "Times New Roman";
    font-size: 14px;
    font-weight: 600;
}
QScrollArea#builderGemInventoryScroll {
    background: #060806;
    border: none;
}
QScrollArea#builderGemInventoryScroll QWidget#builderGemInventoryHost {
    background: #060806;
}
QFrame#builderSocketSection {
    background: #080a08;
    border: 1px solid #2f332f;
}
QScrollArea#builderGemScroll {
    background: #060806;
    border: 1px solid #262a26;
}
QScrollArea#builderGemScroll QWidget {
    background: #060806;
}
QFrame#affixPickerOverlay {
    background: #050706;
    border: 2px solid #80602e;
}
QLabel#affixPickerTitle {
    color: #e3b969;
    font-family: Georgia, "Times New Roman";
    font-size: 25px;
    font-weight: 700;
}
QPushButton#affixPickerClose {
    background: #15110c;
    border: 1px solid #644824;
    color: #d7a45c;
    font-size: 24px;
    padding: 0;
}
QPushButton#affixPickerClose:hover {
    border-color: #ece5d9;
    color: white;
}
QScrollArea#affixPickerScroll {
    background: #060806;
    border: none;
}
QFrame#affixPickerSection {
    background: #080a08;
    border: 1px solid #343027;
}
QLabel#affixPickerCategoryTitle {
    color: #b49a76;
    font-family: Georgia, "Times New Roman";
    font-size: 19px;
    font-weight: 600;
}
QFrame#affixPickerTile {
    background: #090b09;
    border: 1px solid #323631;
}
QFrame#affixPickerTile:hover {
    background: #111411;
    border: 2px solid #f1eee6;
}
QLabel#affixPickerTileName {
    background: transparent;
    border: none;
    color: #c6c1b8;
    font-family: Georgia, "Times New Roman";
    font-size: 10px;
}
QPushButton#targetAffixButton {
    background: #090b09;
    border: 1px solid #40382e;
    color: #c8b89f;
    text-align: left;
    padding: 7px 9px;
}
QPushButton#targetAffixButton:hover {
    border-color: #e4ded4;
    color: #f2ede5;
}
QCheckBox#secondWeaponCheck {
    color: #a99d8b;
    spacing: 7px;
    padding: 3px 0;
}
QCheckBox#secondWeaponCheck::indicator {
    width: 17px;
    height: 17px;
}
QCheckBox#secondWeaponCheck::indicator:unchecked {
    background: #080a08;
    border: 1px solid #5a4930;
}
QCheckBox#secondWeaponCheck::indicator:checked {
    background: #8a5a18;
    border: 1px solid #d4a95d;
}

QSpinBox {
    background: #090b09;
    border: 1px solid #4b402f;
    color: #d8c8ad;
    padding: 6px 7px;
}
QSpinBox:hover, QSpinBox:focus {
    border-color: #936a2e;
}
QScrollArea#builderItemScroll,
QScrollArea#builderTargetScroll,
QScrollArea#creatorAttrScroll {
    background: #070907;
    border: 1px solid #282b27;
}
QFrame#builderTargetRow {
    background: #090b09;
    border: 1px solid #34302a;
    padding: 2px;
}
QPushButton#targetRemoveButton {
    background: #15110c;
    border: 1px solid #594122;
    color: #d8a75c;
    font-size: 20px;
    padding: 0;
}
QPushButton#targetAddButton {
    background: #15110c;
    border: 1px solid #6a4d27;
    color: #e0ad5e;
    font-family: Arial, sans-serif;
    font-size: 20px;
    font-weight: 400;
    padding: 0px;
    margin: 0px;
    text-align: center;
}
QPushButton#targetRemoveButton:hover,
QPushButton#targetAddButton:hover {
    background: #1d160d;
    border-color: #d3a357;
    color: #f1dfbd;
}
QPushButton#targetAddButton:pressed {
    background: #2a1d0d;
    border-color: #f0c36e;
}
QComboBox {
    background: #090b09;
    border: 1px solid #4b402f;
    color: #c8c0b4;
    padding: 7px 9px;
    min-height: 22px;
}
QComboBox:hover, QComboBox:focus {
    border: 1px solid #8a6329;
}
QComboBox QAbstractItemView {
    background: #090b09;
    color: #c8c0b4;
    border: 1px solid #4b402f;
    selection-background-color: #3c2911;
    selection-color: #efc77d;
}
QLabel#builderFieldLabel,
QLabel#builderSocketLabel {
    color: #9d8d77;
    font-family: Georgia, "Times New Roman";
    font-size: 13px;
}
QPushButton#secondaryButton {
    background: #0d0e0c;
    border: 1px solid #4a3b26;
    color: #bda77f;
    padding: 7px 10px;
}
QPushButton#secondaryButton:hover {
    border-color: #9b7133;
    color: #e1c28b;
}

QLineEdit {
    background: #0c0f0d;
    border: 1px solid #383329;
    padding: 10px 12px;
    color: #d0cbc1;
    selection-background-color: #6a4818;
}
QLineEdit:focus { border: 1px solid #896124; }
QPushButton {
    background: #15130f;
    border: 1px solid #4d402c;
    color: #bca16f;
    padding: 9px 14px;
}
QPushButton:hover {
    background: #201a12;
    border-color: #7b5c2b;
    color: #e0bd7a;
}
QPushButton:pressed { background: #2b1e0d; }
QPushButton#goldButton {
    background: #4b2b07;
    border: 1px solid #9f6a20;
    color: #e1b867;
    font-weight: 600;
}
QPushButton#goldButton:hover { background: #61380a; }
QPushButton#tabButton {
    background: transparent;
    border: none;
    border-bottom: 1px solid #3f3424;
    color: #705d45;
    font-family: Georgia, "Times New Roman";
    font-size: 20px;
    padding: 6px 24px 8px 24px;
}
QPushButton#tabButton:checked {
    color: #d2a55d;
    border-bottom: 2px solid #a96d19;
}
QPushButton#tabButton:hover { color: #c49a5c; }
QPushButton#tinyButton {
    background: transparent;
    border: none;
    color: #78654a;
    padding: 0;
    font-size: 17px;
}
QPushButton#tinyButton:hover { color: #d2a55d; }
QPushButton#squareAction {
    background: #17120c;
    border: 1px solid #503b20;
    color: #d0a45d;
    font-size: 30px;
    padding: 0;
}
QPushButton#squareAction:hover { background: #2b1d0d; border-color: #8d622a; }
QPushButton#squareAction[danger="true"] { color: #c18b63; }
QPushButton#squareAction[danger="true"]:hover { background: #321713; border-color: #7f4034; }
QPushButton#linkButton {
    background: transparent;
    border: none;
    color: #7c6b50;
    padding: 6px;
}
QPushButton#linkButton:hover { color: #c29b5c; }

QFrame#classSelectPanel {
    background: #080a08;
    border: 1px solid #4f4027;
}
QLabel#classSelectTitle {
    color: #e4b45f;
    font-family: Georgia, "Times New Roman";
    font-size: 30px;
    font-weight: 700;
}
QLabel#classSelectSubtitle {
    color: #918878;
    font-size: 13px;
}
QPushButton#classSelectButton {
    background: #0b0d0b;
    border: 1px solid #5b4628;
    color: #d3bea0;
    font-family: Georgia, "Times New Roman";
    font-size: 18px;
    text-align: left;
    padding: 11px 16px;
}
QPushButton#classSelectButton:hover {
    border: 2px solid #f0ede4;
    background: #15120d;
    color: #f0c778;
}
QPushButton#classSelectButton[selected="true"] {
    background: #30200e;
    border: 1px solid #a06b22;
    color: #efc36f;
}
QPushButton#changeClassButton {
    background: #0b0c0a;
    border: 1px solid #4c3c25;
    color: #c39a61;
    padding: 6px 12px;
}
QPushButton#changeClassButton:hover {
    border: 1px solid #d8c9ae;
    color: #ead9bc;
}
QLabel#currentClassLabel {
    color: #e0b466;
    font-family: Georgia, "Times New Roman";
    font-size: 17px;
    font-weight: 600;
}

QFrame#buildCard {
    background: #0e0d0a;
    border: 1px solid #58482f;
}
QFrame#buildCard:hover { border: 1px solid #806032; }
QFrame#importBox, QFrame#previewPanel {
    background: #0d0d0a;
    border: 1px solid #55452e;
}
QFrame#detailsPanel {
    background: #080908;
    border: 1px solid #302b23;
}
QScrollArea { background: transparent; border: none; }
QScrollArea > QWidget > QWidget { background: transparent; }
QScrollBar:vertical {
    background: #070907;
    width: 13px;
    margin: 3px 2px 3px 2px;
    border: none;
}
QScrollBar::handle:vertical {
    background: #55452f;
    min-height: 42px;
    border: 1px solid #6e5737;
    border-radius: 4px;
}
QScrollBar::handle:vertical:hover {
    background: #765a34;
    border-color: #9b733d;
}
QScrollBar::handle:vertical:pressed {
    background: #9a6c2b;
    border-color: #c58c36;
}
QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {
    height: 0px;
    border: none;
    background: transparent;
}
QScrollBar::add-page:vertical,
QScrollBar::sub-page:vertical {
    background: transparent;
}

QScrollBar:horizontal {
    background: #070907;
    height: 13px;
    margin: 2px 3px 2px 3px;
    border: none;
}
QScrollBar::handle:horizontal {
    background: #55452f;
    min-width: 42px;
    border: 1px solid #6e5737;
    border-radius: 4px;
}
QScrollBar::handle:horizontal:hover {
    background: #765a34;
    border-color: #9b733d;
}
QScrollBar::handle:horizontal:pressed {
    background: #9a6c2b;
    border-color: #c58c36;
}
QScrollBar::add-line:horizontal,
QScrollBar::sub-line:horizontal {
    width: 0px;
    border: none;
    background: transparent;
}
QScrollBar::add-page:horizontal,
QScrollBar::sub-page:horizontal {
    background: transparent;
}
QTableWidget {
    background: #0b0c0b;
    alternate-background-color: #10110f;
    gridline-color: #29261f;
    border: 1px solid #393127;
    selection-background-color: #3d2a12;
    selection-color: #e2cfaa;
}
QHeaderView::section {
    background: #17130e;
    color: #b89255;
    border: none;
    border-right: 1px solid #352b20;
    border-bottom: 1px solid #4a3b27;
    padding: 8px;
}

QFrame#attributesSidebar {
    background: #060706;
    border-left: 1px solid #2b251d;
    border-right: 1px solid #201c17;
}
QLabel#attributesTitle {
    font-family: Georgia, "Times New Roman";
    font-size: 18px;
    color: #c49a61;
    padding-bottom: 2px;
}
QFrame#attributeRow { background: transparent; border: none; }
QLabel#attributeName {
    color: #c2bdb4;
    font-family: Georgia, "Times New Roman";
    font-size: 15px;
}
QLabel#attributeLevel {
    color: #918a80;
    font-family: Georgia, "Times New Roman";
    font-size: 13px;
}
QLabel#attributeWeaponNote {
    color: #746d61;
    font-size: 11px;
    padding-bottom: 3px;
}
QPushButton#weaponToggle {
    background: #11110e;
    border: 1px solid #4d402c;
    color: #8f7b5b;
    padding: 0;
    font-size: 12px;
    font-weight: 600;
}
QPushButton#weaponToggle:checked {
    background: #5a3409;
    border-color: #b27a27;
    color: #f0c77a;
}
QFrame#itemHoverPopup {
    background: #080a08;
    border: 1px solid #4a4032;
}
QLabel#hoverStat {
    color: #9f9b94;
    font-size: 14px;
}
QLabel#hoverAffix {
    color: #b9b6ae;
    font-family: Georgia, "Times New Roman";
    font-size: 15px;
    padding: 2px 0;
}
QLabel#hoverGemTitle {
    color: #c59c5d;
    font-family: Georgia, "Times New Roman";
    font-size: 14px;
    padding-top: 3px;
}
QFrame#attributeHoverPopup {
    background: #050706;
    border: 1px solid #5c482d;
}
QLabel#attributePopupTitle {
    color: #c59a5d;
    font-family: Georgia, "Times New Roman";
    font-size: 24px;
    font-weight: 600;
}
QLabel#attributePopupCurrent {
    color: #8f887d;
    font-size: 12px;
}
QFrame#attributePopupSeparator {
    color: #555750;
    background: #555750;
    max-height: 1px;
    min-height: 1px;
    border: none;
}
QLabel#attributePopupSection {
    color: #a57d4b;
    font-family: Georgia, "Times New Roman";
    font-size: 16px;
    font-weight: 600;
}
QLabel#attributePopupDescription {
    color: #918d86;
    font-family: Georgia, "Times New Roman";
    font-size: 14px;
    line-height: 1.2;
}
QFrame#attributePopupLevel {
    background: transparent;
    border: none;
}
QFrame#attributePopupLevelActive {
    background: #111411;
    border: 1px solid #4b5049;
}
QLabel#attributePopupLevelNumber {
    color: #777a75;
    font-family: Georgia, "Times New Roman";
    font-size: 14px;
}
QLabel#attributePopupLevelNumberActive {
    color: #f0eee8;
    font-family: Georgia, "Times New Roman";
    font-size: 14px;
    font-weight: 600;
}
QLabel#attributePopupEffect {
    color: #747772;
    font-family: Georgia, "Times New Roman";
    font-size: 14px;
}
QLabel#attributePopupEffectActive {
    color: #f0eee8;
    font-family: Georgia, "Times New Roman";
    font-size: 14px;
    font-weight: 600;
}

QFrame#compactAffixRow {
    background: transparent;
    border: none;
}
QLabel#compactAffixText {
    color: #c0bbb0;
    font-family: Georgia, "Times New Roman";
    font-size: 14px;
}
QLabel#hoverSourceTitle {
    color: #746d61;
    font-size: 11px;
    padding-top: 2px;
}
QLabel#hoverSummaryTitle {
    color: #c9a367;
    font-family: Georgia, "Times New Roman";
    font-size: 14px;
    font-weight: 600;
    padding-top: 2px;
}
QLabel#hoverSummary {
    color: #a59d90;
    font-size: 13px;
}
QLabel#hoverHint {
    color: #635f58;
    font-size: 11px;
    padding-top: 4px;
}
QFrame#hoverSeparator {
    color: #3c3a35;
    background: #3c3a35;
    max-height: 1px;
}
QFrame#affixCatalogCard {
    background: #0b0c0a;
    border: 1px solid #352f26;
}
QLabel#catalogAffixName {
    font-family: Georgia, "Times New Roman";
    font-size: 19px;
    font-weight: 600;
    color: #c5a06b;
}
QLabel#catalogDescription {
    color: #9b968c;
    font-size: 13px;
}
QLabel#catalogLevels {
    color: #77736b;
    font-size: 12px;
}

QToolTip {
    background: #11120f;
    color: #ddd5c5;
    border: 1px solid #665034;
    padding: 6px;
}
QMessageBox { background: #0d0e0c; }
QDialog { background: #090b09; color: #bbb6ac; }
"""


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setStyle("Fusion")
    app.setStyleSheet(STYLE)

    font = QFont("Segoe UI", 10)
    app.setFont(font)

    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
