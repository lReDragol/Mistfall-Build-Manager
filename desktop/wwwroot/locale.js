import * as catalogStrings from "./catalog-strings.js";

const rows = `editor|Создание сборки|Create build|Crear configuración
soulBrand|Клеймо души|Soul Brand|Marca del alma
autoBrand|Подбирать клеймо души|Suggest a Soul Brand|Sugerir marca del alma
brandOutsideCode|Клеймо сохраняется в Forge отдельно. Код игры его не передаёт.|Forge saves the Brand separately. The game code does not include it.|Forge guarda la marca por separado. El código del juego no la incluye.
brandLevel|Уровень клейма|Brand level|Nivel de marca
brandEffects|Атрибуты клейма|Brand attributes|Atributos de la marca
brandChooseKind|Выбери тип эффекта для этого слота.|Choose an effect type for this slot.|Elige un tipo de efecto para esta ranura.
brandSearch|Поиск по названию|Search by name|Buscar por nombre
brandClear|Очистить слот|Clear effect|Vaciar ranura
brandChoose|Выбери клеймо в каталоге.|Choose a Soul Brand from the catalog.|Elige una marca del alma en el catálogo.
brandRemove|Снять клеймо|Remove Brand|Quitar marca
brandPending|Примени или отмени изменения клейма перед сохранением сборки.|Apply or cancel the Brand changes before saving this build.|Aplica o cancela los cambios de la marca antes de guardar la configuración.
brandInvalidValue|Проверь значения характеристик: они должны быть в указанном диапазоне.|Check stat values: they must be within the indicated range.|Revisa los valores: deben estar dentro del intervalo indicado.
brandApply|Применить|Apply|Aplicar
brandNone|Без клейма|No Brand|Sin marca
brandLesser|Малое клеймо души|Lesser Soul Brand|Marca del alma menor
brandMedium|Среднее клеймо души|Medium Soul Brand|Marca del alma media
brandGreater|Большое клеймо души|Greater Soul Brand|Marca del alma mayor
brandSuperb|Высшее клеймо души|Superb Soul Brand|Marca del alma suprema
brandCap|Обычное улучшение: до ур. {cap}. Перековка: до ур. {max}.|Normal upgrades: up to Lv. {cap}. Reshaping: up to Lv. {max}.|Mejora normal: hasta niv. {cap}. Remodelado: hasta niv. {max}.
brandEffect|Эффект {index}|Effect {index}|Efecto {index}
brandKindStat|Характеристика|Basic attribute|Atributo básico
brandKindAffix|Фиксированный атрибут|Fixed affix|Afijo fijo
brandKindGem|Ячейка самоцвета|Gem socket|Ranura de gema
brandKindTalent|Талант|Talent|Talento
brandPick|Выбрать…|Choose…|Elegir…
brandStat6|Макс. энергия|Max energy|Energía máxima
brandStat8|Сила лечения|Healing done|Curación realizada
brandStat9|Крит. урон|Critical damage|Daño crítico
brandStat17|Урон по монстрам|Monster damage bonus|Daño a monstruos
brandStat21|Пробивание защиты|Defense penetration|Penetración de defensa
brandStat31|Скорость перезарядки умений|Skill cooldown speed|Velocidad de recarga
brandStat32|Снижение расхода энергии|Skill energy cost reduction|Reducción del coste de energía
brandStat42|Сопротивление жаре|Heat resistance|Resistencia al calor
invalid-brand|Проверь редкость, уровень, ограничения класса и повторы. Максимум 2 атрибута и 2 ячейки (всего 3), один талант класса и один общий.|Check rarity, level, class rules and duplicates. Up to 2 fixed affixes and 2 sockets (3 combined), 1 class talent and 1 general talent.|Revisa rareza, nivel, clase y duplicados. Hasta 2 afijos fijos y 2 ranuras (3 en total), 1 talento de clase y 1 general.
brandIncomplete|Сначала выбери значение у каждого добавленного эффекта.|Choose a value for each added effect first.|Elige un valor para cada efecto añadido.
importHint|Вставь код из меню подготовки. Здесь появятся предметы, камни и атрибуты.|Paste a code from Prepare to preview its gear, gems and attributes.|Pega un código de Preparación para ver el equipo, las gemas y los atributos.
emptyLoadout|В этом коде нет предметов.|This code contains no equipment.|Este código no contiene equipo.
socketEmpty|Камень не установлен|No gem socketed|Sin gema equipada
weaponIIOnly|Оружие только в слоте II. Если игра не принимает код, попробуй перенести его в I.|Only weapon II is equipped. If the game rejects the code, try moving it to slot I.|Solo hay arma en la ranura II. Si el juego rechaza el código, prueba a moverla a la I.
moveWeapon|Перенести в I|Move to slot I|Mover a la ranura I
loadBeforeCopy|Сначала загрузи введённый код. Копируется код текущей сборки.|Load the entered code first. Copy uses the current build.|Carga primero el código introducido. Se copia el código de la configuración actual.
copiedForGame|Код скопирован. В игре: Подготовка → Управление/импорт → Импорт сборки.|Code copied. In game: Prepare → Manage/Import → Import Loadout.|Código copiado. En el juego: Preparación → Gestionar/Importar → Importar equipamiento.
scale|Масштаб|Scale|Escala
scaleAuto|Авто|Auto|Automática
invalid-scale|Выбери один из вариантов масштаба.|Choose one of the available scales.|Elige una de las escalas disponibles.
skipContent|К рабочей области|Go to workspace|Ir al área de trabajo
language|Язык|Language|Idioma
gemSearch|Поиск самоцветов по эффекту|Find gems by effect|Buscar gemas por efecto
equippedSockets|Ячейки предмета|Item sockets|Ranuras del objeto
chooseGem|Совместимые самоцветы|Compatible gems|Gemas compatibles
loadingGems|Загружаю самоцветы…|Loading gems…|Cargando gemas…
emptySocket|Оставить ячейку пустой|Leave socket empty|Dejar la ranura vacía
itemContribution|Вклад предмета в атрибуты|Item attribute contribution|Atributos que aporta el objeto
missingItemId|Неизвестный предмет · ID {id}|Unknown item · ID {id}|Objeto desconocido · ID {id}
innate|Врождённый эффект|Innate effect|Efecto innato
filterEffects|Фильтр по эффекту|Filter by effect|Filtrar por efecto
resetFilter|Сбросить фильтр|Clear filter|Quitar filtro
wineBonus|Вино триумфа: +{count} ур.|Victory Wine: +{count} levels|Vino del triunfo: +{count} niveles
editingName|Редактируется: {name}|Editing: {name}|Editando: {name}
applyChanges|Применить изменения|Apply changes|Aplicar cambios
discardEdit|Отменить правки|Discard changes|Descartar cambios
discardConfirm|Отменить правки в этой сборке? Сохранённый оригинал останется без изменений.|Discard these edits? The saved build will stay unchanged.|¿Descartar los cambios? La configuración guardada no se modificará.
copySuffix|копия|copy|copia
library|Мои сборки|My builds|Mis configuraciones
windowTitle|Изменить сборку|Modify build|Editar configuración
importBuild|Импорт сборки|Import build|Importar configuración
chooseClass|Выберите класс|Choose a class|Elige una clase
classIntro|Сохранённые сборки разделены по классам. Выбери персонажа, чтобы открыть его сборки.|Saved builds are grouped by class. Choose a character to open its builds.|Las configuraciones se agrupan por clase. Elige un personaje para abrirlas.
classNote|Класс можно сменить в любой момент.|You can switch classes at any time.|Puedes cambiar de clase en cualquier momento.
changeClass|← Сменить класс|← Change class|← Cambiar clase
buildCount-one|{count} сборка|{count} build|{count} configuración
buildCount-few|{count} сборки|{count} builds|{count} configuraciones
buildCount-many|{count} сборок|{count} builds|{count} configuraciones
buildCount-other|{count} сборок|{count} builds|{count} configuraciones
savedCount|Всего сохранено: {count}|Saved in total: {count}|Total guardadas: {count}
database|База предметов|Item database|Base de objetos
dataFolder|Папка данных|Data folder|Carpeta de datos
updateCatalog|Обновить из JSON|Update from JSON|Actualizar desde JSON
refreshCatalog|Обновить базу|Refresh database|Actualizar base de datos
importCatalogPack|Импорт базы и иконок|Import database and icons|Importar base e iconos
catalogPackMissing|Выбери папку с одним JSON каталога и подпапкой icons.|Choose a folder with one catalog JSON and an icons subfolder.|Elige una carpeta con un JSON del catálogo y una subcarpeta icons.
catalogWithIcons|База обновлена · загружено иконок: {count}.|Database updated · {count} icons loaded.|Base actualizada · {count} iconos cargados.
catalogDownloading|Загружаю базу предметов…|Downloading the item database…|Descargando la base de objetos…
catalog-busy|База уже обновляется.|The database is already updating.|La base ya se está actualizando.
catalog-download|Не удалось скачать базу. Оставил локальную копию.|Could not download the database. The local copy was kept.|No se pudo descargar la base. Se conservó la copia local.
classSearch|Поиск в сборках класса «{name}»…|Search {name} builds…|Buscar configuraciones de {name}…
loadingBuilds|Загружаю сборки…|Loading builds…|Cargando configuraciones…
allAffixes|Все атрибуты|All attributes|Todos los atributos
affixSearch|Поиск атрибутов|Search attributes|Buscar atributos
activeCount|Активных атрибутов: {count}|Active attributes: {count}|Atributos activos: {count}
details|Сведения|Details|Detalles
editBuild|Редактировать сборку|Edit build|Editar configuración
editMetadata|Название и код|Name and code|Nombre y código
copyCode|Копировать код|Copy code|Copiar código
close|Закрыть|Close|Cerrar
backEditor|← К сборке|← Back to build|← Volver al equipo
targetTitle|Автоподбор атрибутов|Attribute optimizer|Optimizador de atributos
resultTitle|Итоговые атрибуты|Resulting attributes|Atributos finales
addTarget|Добавить атрибут|Add attribute|Añadir atributo
level|Уровень|Level|Nivel
levelShort|Ур. {level}|Lv. {level}|Niv. {level}
previousPage|Предыдущая страница|Previous page|Página anterior
nextPage|Следующая страница|Next page|Página siguiente
magicShort|МАГ|MAG|MAG
physicalShort|ФИЗ|PHY|FÍS
category-utility|Поддержка|Support|Apoyo
category-defense|Защита|Defense|Defensa
category-offense|Атака|Offense|Ataque
category-other|Прочие|Other|Otros
importPreview|Предпросмотр|Preview|Vista previa
weaponNotInCode|Активное оружие не хранится в коде — выбери I или II как в игре.|The code does not store the active weapon. Select I or II as in-game.|El código no guarda el arma activa. Elige I o II como en el juego.
decoding|Читаю код…|Reading code…|Leyendo código…
importReady|Сборка распознана · {name}|Build decoded · {name}|Configuración reconocida · {name}
preview|3D-примерочная|3D fitting room|Probador 3D
editorTitle|Редактор сборок|Build editor|Editor de configuraciones
libraryTitle|Библиотека сборок|Build library|Biblioteca de configuraciones
previewTitle|Примерочная|Fitting room|Probador de equipo
career|Класс|Class|Clase
sample|Пример сборки|Try a sample build|Probar configuración de ejemplo
equipment|Экипировка|Equipment|Equipo
active|Активное оружие|Active weapon|Arma activa
reset|Сбросить сборку|Reset build|Restablecer configuración
catalog|Каталог|Catalog|Catálogo
gearSearch|Поиск предметов|Search equipment|Buscar equipo
allRarity|Все редкости|All rarities|Todas las rarezas
allEffects|Все эффекты|All effects|Todos los efectos
noInnate|Без врождённого|No innate effect|Sin efecto innato
attributes|Атрибуты|Attributes|Atributos
optimizer|Автоподбор|Optimizer|Optimizador
totals|Итоговые|Totals|Totales
weapon|Тип оружия|Weapon type|Tipo de arma
rarity|Редкость|Rarity|Rareza
wine|Вино триумфа|Victory Wine|Vino del triunfo
noWine|Без вина|No wine|Sin vino
second|Добавлять второе оружие|Include a second weapon|Incluir una segunda arma
chooseTarget|Выбери атрибут|Choose an attribute|Elige un atributo
removeTarget|Убрать атрибут|Remove target|Quitar objetivo
solve|Подобрать сборку|Optimize build|Optimizar configuración
solving|Подбираю комбинацию…|Finding a combination…|Buscando una combinación…
found|Цели выполнены|Targets matched|Objetivos cumplidos
closest|Найден ближайший вариант|Closest build found|Se encontró la opción más cercana
needTargets|Добавь желаемые атрибуты.|Add your target attributes.|Añade los atributos objetivo.
maxTargets|В автоподборе доступно до {max} целей.|The optimizer supports up to {max} targets.|El optimizador admite hasta {max} objetivos.
gearCode|Код сборки|Gear Code|Código de equipo
codePlaceholder|Вставь Gear Code из игры|Paste a Gear Code from the game|Pega el código del juego
load|Загрузить код|Load code|Cargar código
copy|Копировать|Copy|Copiar
copied|Код скопирован.|Code copied.|Código copiado.
codeLoaded|Сборка загружена. Её атрибуты добавлены в цели.|Build loaded. Its attributes are now targets.|Configuración cargada. Sus atributos son ahora objetivos.
save|Сохранить сборку|Save build|Guardar configuración
saved|Сохранённые сборки|Saved builds|Configuraciones guardadas
librarySearch|Поиск по названию или коду|Search by name or code|Buscar por nombre o código
noSaved|Нет сохранённых сборок этого класса. Импортируй код или создай сборку.|No saved builds for this class. Import a code or create a build.|No hay configuraciones de esta clase. Importa un código o crea una configuración.
open|Открыть|Open|Abrir
delete|Удалить|Delete|Eliminar
confirmDelete|Удалить сохранённую сборку «{name}»?|Delete the saved build “{name}”?|¿Eliminar la configuración «{name}»?
buildName|Название|Name|Nombre
cancel|Отмена|Cancel|Cancelar
saveCopy|Сохранить копию|Save a copy|Guardar una copia
saveAction|Сохранить|Save|Guardar
savedOk|Сборка сохранена.|Build saved.|Configuración guardada.
camera|Сбросить камеру|Reset camera|Restablecer cámara
cameraHint|Перетащи для вращения · колесо для масштаба|Drag to rotate · scroll to zoom|Arrastra para girar · rueda para acercar
equippedPreview|Модель сборки|Build preview|Vista del equipo
test|Тест|Test|Prueba
modelSettings|Настройки 3D|3D settings|Ajustes 3D
particles|Частицы|Particles|Partículas
characterAnimation|Анимация персонажа|Character animation|Animación del personaje
modelPack|Подключить папку моделей|Load model folder|Cargar carpeta de modelos
packLoaded|В папке найдено моделей: {count}.|Models found in folder: {count}.|Modelos encontrados: {count}.
packError|В папке нужны characters/<ID>.glb и/или items/<ID>.glb без повторов ID.|Use characters/<ID>.glb and/or items/<ID>.glb without duplicate IDs.|Usa characters/<ID>.glb y/o items/<ID>.glb sin IDs duplicados.
bodyMissing|Нет 3D-модели: {name}. Оригинальный GLB можно подключить в настройках 3D.|No 3D model for {name}. Load the original GLB in 3D settings.|No hay modelo 3D para {name}. Carga el GLB original en los ajustes 3D.
loadingModel|Загружаю модель класса…|Loading class model…|Cargando el modelo de la clase…
modelCoverage|Подключено моделей экипировки: {count}/{total}.|Gear models loaded: {count}/{total}.|Modelos de equipo cargados: {count}/{total}.
modelIncomplete|Без 3D-модели: {count}.|Items without a 3D model: {count}.|Objetos sin modelo 3D: {count}.
mesh-ready|Модель подключена|Model loaded|Modelo cargado
mesh-missing|Модели нет|No model|Sin modelo
mesh-loading|Загрузка модели|Loading model|Cargando modelo
mesh-error|Не удалось прочитать GLB|Could not read GLB|No se pudo leer el GLB
mesh-inactive|Неактивное оружие не отображается|Inactive weapon is not shown|El arma inactiva no se muestra
customModel|Привязать отдельный GLB|Assign an individual GLB|Asignar un GLB individual
modelHint|Выбери цель и оригинальный GLB. Модели должны совпадать по позе, масштабу и координатам. Привязки действуют до закрытия приложения.|Select a target and original GLB. All files must share a pose, scale, and origin. Assignments last until the app closes.|Elige un destino y su GLB original. Los archivos deben compartir pose, escala y origen. Las asignaciones duran hasta cerrar la aplicación.
resetModels|Отключить модели|Unload models|Quitar modelos
baseModel|Базовая модель|Base model|Modelo base
modelLoaded|Модель привязана.|Model assigned.|Modelo asignado.
modelError|Не удалось загрузить GLB.|Could not load GLB.|No se pudo cargar el GLB.
noGpu|3D недоступно. Список экипировки остаётся доступен справа.|3D is unavailable. The equipped items are listed on the right.|3D no disponible. El equipo sigue visible a la derecha.
loadingScene|Загружаю 3D-сцену…|Loading the 3D scene…|Cargando la escena 3D…
importCatalog|Импорт базы JSON|Import JSON catalog|Importar catálogo JSON
catalogTools|Данные каталога|Catalog data|Datos del catálogo
catalogOk|База обновлена.|Catalog updated.|Catálogo actualizado.
none|Пусто|Empty|Vacío
noMatches|Ничего не найдено. Измени фильтры.|No matches. Try changing the filters.|Sin resultados. Cambia los filtros.
chooseItem|Выбери предмет, чтобы увидеть параметры и ячейки самоцветов.|Select an item to see its stats and gem sockets.|Elige un objeto para ver sus estadísticas y ranuras.
noSockets|У предмета нет ячеек для самоцветов.|This item has no gem sockets.|Este objeto no tiene ranuras para gemas.
variant|Вариант предмета|Item variant|Variante del objeto
variants|{count} вар.|{count} variants|{count} variantes
gemRank|Ранг|Rank|Nivel
clearSlot|Снять предмет|Remove item|Quitar objeto
unknownItem|Для этого ID в каталоге нет карточки.|This ID has no catalog record.|Este ID no tiene ficha en el catálogo.
missingEffect|Нет активных атрибутов.|No active attributes.|No hay atributos activos.
code-length|Вставь код длиной до 320 символов.|Paste a code up to 320 characters.|Pega un código de hasta 320 caracteres.
code-character|В коде есть недопустимый символ.|The code contains an invalid character.|El código contiene un carácter no válido.
code-header|Это не Gear Code Mistfall Hunter.|This is not a Mistfall Hunter Gear Code.|No es un código de Mistfall Hunter.
code-truncated|Код обрезан. Скопируй его целиком.|The code is incomplete. Copy it again.|El código está incompleto. Cópialo de nuevo.
code-version|Эта версия кода не поддерживается.|This code version is unsupported.|Esta versión del código no es compatible.
legacyCodeNote|Игра больше не принимает этот формат. Обнови код перед копированием.|The game no longer accepts this format. Upgrade the code before copying it.|El juego ya no acepta este formato. Actualiza el código antes de copiarlo.
upgradeCode|Обновить код|Upgrade code|Actualizar código
upgradedCode|Код обновлён до v{version}.|Code upgraded to v{version}.|Código actualizado a v{version}.
upgradedEffects|Код обновлён до v{version}. В этих слотах эффекты изменились: {slots}. Проверь атрибуты перед импортом в игру.|Code upgraded to v{version}. Effects changed in these slots: {slots}. Review the affixes before importing in game.|Código actualizado a v{version}. Cambiaron los efectos en estas ranuras: {slots}. Revisa los afijos antes de importarlo al juego.
upgrade-item|Нельзя обновить код: в новой базе нет одного из вариантов предметов.|Cannot upgrade: an item variant is missing from the new catalog.|No se puede actualizar: falta una variante de objeto en el catálogo nuevo.
upgrade-gem|Нельзя обновить код без потери самоцвета. Старая сборка не изменена.|Cannot upgrade without losing a gem. The old build was not changed.|No se puede actualizar sin perder una gema. No se cambió la configuración antigua.
code-class|В коде указан неизвестный класс или слот.|The code contains an unknown class or slot.|El código contiene una clase o ranura desconocida.
code-item|Предмет отсутствует в таблице этого слота.|The item is missing from this slot's table.|El objeto no figura en la tabla de esa ranura.
code-gem|Код содержит несовместимый индекс самоцвета.|The code contains an incompatible gem index.|El código contiene un índice de gema incompatible.
build-name|Введи название до 100 символов.|Enter a name up to 100 characters.|Introduce un nombre de hasta 100 caracteres.
build-missing|Сборка уже удалена.|This build has already been deleted.|La configuración ya se eliminó.
invalid-targets|Проверь список желаемых атрибутов.|Check your target attributes.|Revisa los atributos objetivo.
no-items|У этого оружия или слота нет предметов выбранной редкости.|This weapon or slot has no items of that rarity.|El arma o la ranura no tiene objetos de esa rareza.
choose-weapon|Выбери тип оружия для класса.|Choose a weapon type for this class.|Elige un tipo de arma para esta clase.
solver-busy|Идёт другой подбор. Повтори позже.|Another optimization is running. Try again shortly.|Hay otra optimización en curso. Inténtalo de nuevo.
catalog-version|Таблицы Gear Code не совпадают с текущей базой.|Gear Code tables do not match the current catalog.|Las tablas de códigos no coinciden con el catálogo actual.
invalid-catalog|Нужен совместимый JSON-каталог Mistfall Builder.|Select a compatible Mistfall Builder JSON catalog.|Selecciona un catálogo JSON compatible de Mistfall Builder.
internal-error|Ошибка приложения. Повтори действие.|An application error occurred. Try again.|Ocurrió un error. Inténtalo de nuevo.
edit|Редактировать слот|Edit slot|Editar ranura
holyHint|Священное оружие, легендарные доспехи.|Holy weapon, legendary armor.|Arma sagrada, armadura legendaria.
magic|Магические аксессуары|Magic accessories|Accesorios mágicos
physical|Физические аксессуары|Physical accessories|Accesorios físicos
attack|Атака|Attack|Ataque
defence|Защита|Defense|Defensa
maxHealth|Здоровье|Health|Salud
combatValue|Боевая ценность|Combat value|Valor de combate
physicalIncrease|Физ. урон|Physical damage|Daño físico
magicalIncrease|Маг. урон|Magic damage|Daño mágico
physicalReduction|Физ. защита|Physical resistance|Resistencia física
magicalReduction|Маг. защита|Magic resistance|Resistencia mágica
criticalReduction|Крит. защита|Critical resistance|Resistencia crítica
blockRate|Блок|Block|Bloqueo`;

const messages = Object.fromEntries(rows.split("\n").map(row => {
    const [key, ru, en, es] = row.split("|");
    return [key, {ru, en, es}];
}));
const group = {
    item: {
        "Worn Hunter's Javelin":["Потёртое копьё охотника","Worn Hunter's Javelin","Jabalina desgastada del cazador"],
        "Refugee Javelin":["Копьё беженца","Refugee Javelin","Jabalina del refugiado"],
        "Ritual Javelin":["Ритуальное копьё","Ritual Javelin","Jabalina ritual"],
        "Falcon Javelin":["Соколиное копьё","Falcon Javelin","Jabalina del halcón"],
        "Dragonhunter Javelin":["Копьё охотника на драконов","Dragonhunter Javelin","Jabalina cazadragones"],
        "Nightveil Needle":["Игла ночной завесы","Nightveil Needle","Aguja del velo nocturno"],
        "Moon Deity - Soulrend Javelin":["Лунное божество — копьё разрыва душ","Moon Deity - Soulrend Javelin","Deidad lunar - Jabalina desgarralmas"],
    },
    slot: {
        0:["Шлем","Head","Cabeza"],1:["Нагрудник","Chest","Torso"],2:["Наручи","Bracers","Brazales"],
        3:["Штаны","Legs","Piernas"],4:["Сапоги","Boots","Botas"],5:["Ожерелье","Necklace","Collar"],
        6:["Кольцо","Ring","Anillo"],10:["Оружие I","Weapon I","Arma I"],11:["Оружие II","Weapon II","Arma II"],
    },
    rarity: [
        ["Неизвестно","Unknown","Desconocido"],["Повреждённый","Damaged","Dañado"],["Обычный","Common","Común"],
        ["Редкий","Rare","Raro"],["Отличный","Excellent","Excelente"],["Эпический","Epic","Épico"],
        ["Легендарный","Legendary","Legendario"],["Священный","Holy","Sagrado"],
    ],
    class: {
        10:["Наёмник","Mercenary","Mercenario"],11:["Чародей","Sorcerer","Hechicero"],
        12:["Чёрная стрела","Blackarrow","Flecha Negra"],13:["Тенестрикс","Shadowstrix","Shadowstrix"],
        14:["Провидец","Seer","Vidente"],15:["Иссохший рыцарь","Withered Knight","Caballero Marchito"],
    },
    weapon: {
        Bow:["Лук","Bow","Arco"],Javelin:["Метательное копьё","Javelin","Jabalina"],Hammer:["Молот","Hammer","Martillo"],
        "Sword and Shield":["Меч и щит","Sword and shield","Espada y escudo"],Staff:["Посох","Staff","Bastón"],
        Catalyst:["Катализатор","Catalyst","Catalizador"],Mace:["Булава","Mace","Maza"],Dagger:["Кинжал","Dagger","Daga"],
        "Dual Blades":["Парные клинки","Dual blades","Hojas dobles"],Greatsword:["Двуручный меч","Greatsword","Mandoble"],
        "Polearm and Shield":["Древковое и щит","Polearm and shield","Arma de asta y escudo"],
    },
    gem: {"-1":["Универсальный","Universal","Universal"],1:["Агат","Agate","Ágata"],2:["Аметист","Amethyst","Amatista"],
        3:["Лунный камень","Moonstone","Piedra lunar"],4:["Перидот","Peridot","Peridoto"]},
    wine: {1:["Тоник смертного","Mortal Tonic","Tónico mortal"],2:["Эль героя","Hero's Ale","Cerveza heroica"],
        3:["Кровь войны","Warblood","Sangre de guerra"],4:["Напиток богов","Gods' Brew","Brebaje divino"]},
    affix: {
        Aegis:["Эгида","Aegis","Égida"],Valor:["Доблесть","Valor","Valor"],Dominion:["Господство","Dominion","Dominio"],
        Cripple:["Калечение","Cripple","Lisiar"],"Side by Side":["Плечом к плечу","Side by Side","Codo con codo"],
        Fervid:["Пыл","Fervid","Ardor"],Fervor:["Рвение","Fervor","Fervor"],Swift:["Быстрота","Swift","Rapidez"],
        Focused:["Концентрация","Focused","Concentración"],Tenacious:["Живучесть","Tenacious","Tenacidad"],
        Resilience:["Выносливость","Resilience","Resiliencia"],Eloquence:["Красноречие","Eloquence","Elocuencia"],
        Brotherhood:["Братство","Brotherhood","Hermandad"],Creation:["Создание","Creation","Creación"],
        "Spirit Shield":["Щит духа","Spirit Shield","Escudo espiritual"],"Distant Ward":["Дальняя защита","Distant Ward","Resguardo a distancia"],
        Vitality:["Энергичность","Vitality","Vitalidad"],Curse:["Проклятие","Curse","Maldición"],Seamless:["Непрерывность","Seamless","Fluidez"],
        Smiting:["Угнетение","Smiting","Castigo"],Ranged:["Дальний бой","Ranged","A distancia"],
        Skypiercing:["Небесный пронзатель","Skypiercing","Perforacielos"],Blessing:["Благословение","Blessing","Bendición"],
        Bulwark:["Защита","Bulwark","Baluarte"],Burst:["Взрыв","Burst","Estallido"],Deft:["Ловкость","Deft","Destreza"],
        Ethereal:["Бесплотность","Ethereal","Etéreo"],"Iron Helmet":["Железный шлем","Iron Helmet","Yelmo de hierro"],
        Elusive:["Неуловимость","Elusive","Escurridizo"],"Sleight of Hand":["Ловкость","Sleight of Hand","Prestidigitación"],
        "Sky Piercer":["Небесный пронзатель","Sky Piercer","Perforacielos"],"Spirit Spring":["Источник духа","Spirit Spring","Manantial espiritual"],
        "Physical Damage Reduction":["Физическое сопротивление","Physical Damage Reduction","Resistencia física"],
        "Magic Damage Reduction":["Магическое сопротивление","Magic Damage Reduction","Resistencia mágica"],
        Powerful:["Физическая мощь","Powerful","Potente"],Wise:["Магическая мощь","Wise","Sabio"],
        "Critical Damage":["Критический урон","Critical Damage","Daño crítico"],"Defense Penetration":["Пробивание защиты","Defense Penetration","Penetración de defensa"],
        Lifebane:["Губитель жизни","Lifebane","Azote vital"],Siphon:["Поглощение","Siphon","Absorción"],
        "Skill Energy Cost Reduction":["Снижение расхода энергии умений","Skill Energy Cost Reduction","Menor coste de habilidades"],
        "Block Energy Cost Reduction":["Снижение расхода энергии блока","Block Energy Cost Reduction","Menor coste de bloqueo"],
        "Energy Recovery Speed Increase":["Скорость восстановления энергии","Energy Recovery Speed Increase","Recuperación de energía"],
        Seeker:["Ловец","Seeker","Buscador"],Stoic:["Стоик","Stoic","Estoicismo"],Strife:["Раздор","Strife","Discordia"],
        Unyielding:["Непреклонность","Unyielding","Inquebrantable"],Wealth:["Богатство","Wealth","Riqueza"],Wrath:["Гнев","Wrath","Ira"],
    },
};
export let language = "ru";
export function setLanguage(code) { if (["ru","en","es"].includes(code)) language = code; }
export function t(key, values = {}) {
    return (messages[key]?.[language] ?? key).replace(/\{(\w+)\}/g, (_, k) => values[k] ?? "");
}
export function term(kind, key, fallback=String(key)) { return group[kind]?.[key]?.[["ru", "en", "es"].indexOf(language)] ?? fallback; }
function catalogText(rows,key,offset=0) {
    return language==="en" || !Object.hasOwn(rows,key) ? undefined : rows[key][offset+(language==="es"?1:0)] || undefined;
}
export const catalogItemName = name => catalogText(catalogStrings.names,name);
export const catalogItemLore = text => catalogText(catalogStrings.lore,text);
export const catalogGemName = name => catalogText(catalogStrings.gems,name);
export const talentName = talent => catalogText(catalogStrings.talents,talent.id) ?? talent.name;
export const talentDescription = talent => catalogText(catalogStrings.talents,talent.id,2) ?? talent.desc;

const effectLabels = [
    ["Block Damage Reduction Rate","Снижение урона при блоке","Reducción de daño al bloquear"],
    ["Critical Damage Resistance","Сопротивление критическому урону","Resistencia al daño crítico"],
    ["Defense Penetration","Пробивание защиты","Penetración de defensa"],
    ["Physical Damage","Физический урон","Daño físico"],["Magic Damage","Магический урон","Daño mágico"],
    ["Physical Resistance","Физическое сопротивление","Resistencia física"],["Magic Resistance","Магическое сопротивление","Resistencia mágica"],
    ["Maximum Health","Максимальное здоровье","Salud máxima"],["Maximum Energy","Максимальная энергия","Energía máxima"],
    ["Movement Speed","Скорость передвижения","Velocidad de movimiento"],["Chanting Speed","Скорость произнесения","Velocidad de conjuración"],
    ["Skill Cooldown Speed","Скорость перезарядки умений","Velocidad de recarga de habilidades"],
    ["Charging Speed","Скорость заряда","Velocidad de carga"],["Interaction Speed","Скорость взаимодействия","Velocidad de interacción"],
    ["Dodge Energy Cost Reduction","Снижение расхода энергии на уклонение","Reducción de energía al esquivar"],
    ["Skill Energy Cost Reduction","Снижение расхода энергии умений","Reducción de energía de habilidades"],
    ["Block Energy Cost Reduction","Снижение расхода энергии блока","Reducción de energía al bloquear"],
    ["Fall Damage Resistance","Сопротивление урону от падения","Resistencia al daño de caída"],
    ["Shield Strength","Прочность щита","Resistencia del escudo"],["Buff Duration","Длительность положительных эффектов","Duración de mejoras"],
    ["Debuff Duration","Длительность отрицательных эффектов","Duración de penalizaciones"],["Execution Damage","Урон казни","Daño de ejecución"],
    ["Attack","Атака","Ataque"],["Defense","Защита","Defensa"],["Healing","Лечение","Curación"],
];
const effectTerms = new Map(effectLabels.map(([key,ru,es])=>[key,{ru,es}]));
const numericEffect = new RegExp("\\b(?:"+[...effectTerms.keys()].join("|")+")(?=\\s+[+-]\\d)","g");
export function effectText(value="") {
    if(language==="en") return value;
    return catalogText(catalogStrings.affixes,value) ?? catalogText(catalogStrings.effects,value) ??
        value.replace(numericEffect,key=>effectTerms.get(key)[language]).replace(/(\d)\.(?=\d)/g,"$1,");
}
