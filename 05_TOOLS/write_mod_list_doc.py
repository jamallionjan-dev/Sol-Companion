import os, re, io
WS = r"C:\Program Files (x86)\Steam\steamapps\workshop\content\108600"
LIST = r"C:\Users\JAMAL\Zomboid\mods\default.txt"
OUT = r"C:\Users\JAMAL\Desktop\Sol\DOCS\قائمة المودات بالترتيب الصحيح.md"
order = re.findall(r"mod = ([^,\r\n]+),", open(LIST, encoding="utf-8").read())
names = {}
roots = [os.path.join(WS, w, "mods") for w in os.listdir(WS)] + [r"C:\Users\JAMAL\Zomboid\mods"]
for r in roots:
    if not os.path.isdir(r): continue
    for m in os.listdir(r):
        for sub in ("42", "42.13", "42.12", "42.0", "common", ""):
            p = os.path.join(r, m, sub, "mod.info")
            if os.path.isfile(p):
                t = open(p, encoding="utf-8", errors="replace").read()
                i = re.search(r"(?mi)^id\s*=\s*\\?(.+?)\s*$", t); n = re.search(r"(?mi)^name\s*=\s*(.+?)\s*$", t)
                if i and n: names.setdefault(i.group(1).strip(), n.group(1).strip())
BODY = {
    "SPNCC": "أساس تخصيص الشخصية، بيطلبو Hotsco",
    "FemaleModelFix": "بيبدّل جسد الأنثى، بينغطّى",
    "FH": "شعر، وبيغيّر تعريف لبس",
    "TombBodyTexNUDE": "خامات جسد Tomb",
    "TombBody": "بيبدّل جسد الأنثى والرجل، جسد الأنثى بينغطّى",
    "TombBodyCompat": "لبس مفصّل على جسد Tomb",
    "TombBodyCustom": "تخصيص جسد Tomb",
    "TombWardrobeALT": "لبس إضافي مفصّل على جسد Tomb",
    "VanillaOutfitsExpanded": "بيغيّر تعريف لبس",
    "Sol": "سول. جسدها خاص فيها، وبتغيّر تعريف 18 حذاء وتنورة",
    "SpnCloth": "لبس Spongie",
    "SpnHair": "شعر Spongie",
    "HotscoNewBody": "الجسد المطلوب ولبسو. لازم يكون بعد كل اللي فوق",
    "HNBS": "مقاس Hotsco الصغير. آخر مود بالقائمة، هو اللي بيحدد الجسد",
}
BS = chr(92)
real = "C:" + BS + "Users" + BS + "JAMAL" + BS + "Zomboid" + BS + "mods" + BS + "default.txt"
L = ["# قائمة المودات بالترتيب الصحيح", "",
     "هاي قائمة المودات المفعّلة بلعبة Steam الأساسية بالترتيب اللي ترتّبت فيه يوم 2026-11-16، وعددها %d مود." % len(order), "",
     "الملف الفعلي اللي بتقرأو اللعبة: `" + real + "`. هاد الملف نسخة للقراءة والمراجعة بس، وتعديلو ما بيغيّر شي باللعبة.", "",
     "## القاعدة", "",
     "- الترتيب من فوق لتحت هو ترتيب التحميل، واللي بيتحمّل آخر شي هو اللي بيفوز إذا مودين بدّلوا نفس الملف.",
     "- الجسد المطلوب (Hotsco) ومعو ملحق المقاس لازم يكونوا آخر مودين بالقائمة.",
     "- كل مود بيغيّر جسد أو لبس أو شعر لازم يكون قبلهم.",
     "- الشخصية إلها جسد واحد: Female Model Fix و Tomb و Hotsco كلهم بيبدّلوا نفس ملف جسد الأنثى، وبيطلع بس الأخير. الباقيين بيضلّوا شغّالين بباقي ملفاتهم.", "",
     "## مودات الجسد واللبس، بترتيبها", "",
     "| الترتيب | المود | الاسم | ملاحظة |", "|---|---|---|---|"]
for i, m in enumerate(order, 1):
    if m in BODY: L.append("| %d | `%s` | %s | %s |" % (i, m, names.get(m, "").replace("|", "/"), BODY[m]))
L += ["", "## ملاحظات", "",
      "- قطع Tomb المفصّلة على جسد Tomb (Tomb Compatibility و Tomb's Wardrobe) ما بتركب على جسد Hotsco مهما كان الترتيب.",
      "- سول بتبدّل تعريف 18 حذاء وتنورة وحدة. بهالترتيب تعريف Hotsco هو اللي بيفوز، فأحذية شخصيتك بتاخد مقاس Hotsco، وسول كمان. إذا حذاء سول ما ركب صح فالحل بمود سول نفسو.",
      "- إضافة Hotsco's New Body EX مش مفعّلة. إذا تفعّلت لازم تكون بعد `HNBS`، يعني آخر شي.",
      "- مود الترتيب التلقائي `ModLoadOrderSorter_b42` بيرتّب بس لما تكبس زر الترتيب التلقائي. صار عندو ملف قواعد (`Zomboid/Lua/sorting_rules.txt`، ونسختو بـ `05_TOOLS/mod_sorting_rules`): Hotsco ومقاساتو آخر شي، ZombieBuddy أول شي، وملحقات Viewpoint بعدو. باقي المودات بيرتّبها على طريقتو.",
      "- للرجوع للقائمة القديمة أو لإعادة الترتيب: `05_TOOLS/main_body_mod_order.py` (بدون كلمة بيعرض، `apply` بيرتّب، `restore` بيرجّع القديمة).",
      "- القائمة قبل الترتيب محفوظة بـ `03_BACKUPS/main_modlist_20261116`.", "",
      "## مودات انشالت من القائمة", "",
      "| المود | السبب |", "|---|---|",
      *(["| `ProjectALifeNPCs` و `ProjectALifeJimmy` | ثقيل: كان يحاكي 10 شخصيات مع سيارات وهليكوبترات. انشال بطلب جمال |"] if not any(_i in set(order) for _i in ['ProjectALifeNPCs', 'ProjectALifeJimmy']) else []),
      *(["| `ProjectViewpointNearVegetation` | ملحق الأشجار ثلاثية الأبعاد. مبني لـ Viewpoint القديم، وهو اللي وقّف Viewpoint 0.1.7 (فشل 20 برنامج رسم، والسبب المكتوب بالسجل اسمو المختصر PVNV). ما يرجع قبل ما صاحبو يحدّثو |"] if not any(_i in set(order) for _i in ['ProjectViewpointNearVegetation']) else []),
      *(["| `ViewpointMouseRightClick`، `ViewpointCrosshairUse`، `ViewpointVisibleLoot` | شالهم جمال لأن Viewpoint 0.1.7 صار فيه شغلهم (قائمة التفاعل وعرض الأغراض) |"] if not any(_i in set(order) for _i in ['ViewpointMouseRightClick', 'ViewpointCrosshairUse', 'ViewpointVisibleLoot']) else []),
      *(["| `ViewpointCropVisibility` | Viewpoint 0.1.7 صار يبيّن المزروعات بكل مراحلها. انشال بقرار جمال يوم 2026-11-17 |"] if 'ViewpointCropVisibility' not in set(order) else []),
      *(["| `TrueHelicopterEvents` و `HeliEvent` | مودين هليكوبتر بيبدّلوا حدث الهليكوبتر الأصلي. انشالوا التنين بقرار جمال يوم 2026-11-17 |"] if not any(_i in set(order) for _i in ['TrueHelicopterEvents', 'HeliEvent']) else []),
      *(["| `PoolPit` | مبني لنسخة تانية من اللعبة: كان يطلّع خطأ جافا بكل إطار (أكتر من 10 آلاف بجلسة وحدة) ويحاول يتدخل برسم Viewpoint ويفشل |"] if not any(_i in set(order) for _i in ['PoolPit']) else []),
      *(["| `ViewpointInteriors` | داخل السيارات. مبني لـ Viewpoint 0.1.6.2، وهو اللي كان يوقّع اللعبة عند التشغيل لما Viewpoint ما يتحمّل |"] if not any(_i in set(order) for _i in ['ViewpointInteriors']) else []),
      *(["| `ViewpointDoor` | إضاءة الأبواب. وقّف Viewpoint 0.1.7: ما لقى السطر اللي بدو يعدّلو بملفات الرسم الجديدة (8 برامج رسم فشلت) |"] if not any(_i in set(order) for _i in ['ViewpointDoor']) else []),
      *(["| `OldPoint` | كود الجافا تبعو بيدخل على نظام الرسم تبع Viewpoint وهو أقدم من 0.1.7. انشال احتياطاً |"] if not any(_i in set(order) for _i in ['OldPoint']) else []),
      *(["| `TankWater` | كاتب بملفو إنو ما بيتوافق مع `StarlitLibrary` |"] if not any(_i in set(order) for _i in ['TankWater']) else []),
      *(["| `CleanUI`، `MinimalSidebar`، `moodlesinlua`، `REORDER_THE_HOTBAR` | شالهم جمال من جوّا اللعبة |", ""] if not any(_i in set(order) for _i in ['CleanUI', 'MinimalSidebar', 'moodlesinlua', 'REORDER_THE_HOTBAR']) else []),
      "القائمة قبل شيلهم (225 مود) محفوظة بـ `03_BACKUPS/main_modlist_20261116/default.before_poolpit_alife.txt`.", "",
      "## مود محلي", "",
      "- `SolFixDGVEyes`: مود محلي صغير بمجلد `C:" + chr(92) + "Users" + chr(92) + "JAMAL" + chr(92) + "Zomboid" + chr(92) + "mods`، مش من الـWorkshop. بيصلّح خطأ مود الواجهة Viewpoint Eyes مع Viewpoint 0.1.7 (سطر واحد بملف واحد). لازم يضل بعد `DGVViewpointEyes4222Patch` مباشرة. بينبنى بـ `05_TOOLS/build_dgv_eyes_fix.py`، ولازم ينعاد بناؤو أو ينطفى إذا مود الواجهة تحدّث.", "",
      "## مودات باقية وفيها مشكلة معروفة", "",
      "| المود | المشكلة |", "|---|---|",
      "| `ProjectViewpointNearVegetation`، `ViewpointFPS`، `ViewpointTileFix` | رجعوا بقرار جمال يوم 2026-11-17. الأشجار تحدّث لـ 0.1.7، والتانيين مبنيين قبل 0.1.7: إذا Viewpoint وقف، هدول أول المشتبه فيهم |",
      "| `EscapeFromZomboidFirearms` | كود الجافا تبعو بيدخل على نظام الرسم تبع Viewpoint وهو أقدم من 0.1.7. حمّل برامج الرسم تبعو بدون فشل، وبقي بطلب جمال. أول المشتبه فيه إذا Viewpoint وقف مرة تانية |",
      "| `ViewpointLivingProps` و `ProjectViewpointQOL` | خطأ واحد لكل واحد عند التحميل مع 0.1.7 (جزء من وظايفهم ما ارتبط) |",
      "| `ShelfContents3D` | بيطلّع أخطاء لما Viewpoint ما يكون محمّل |",
      "| `DGVViewpointEyes4222Patch` | ترتيبو قبل Viewpoint. ملحقات Viewpoint المفروض تيجي بعدو، بس المود ما كاتب شرط ترتيب |", "",
      "## Viewpoint 0.1.7 وملف التوقيع", "",
      "- التحديث نزل مع ملف توقيع `Viewpoint.jar.zbs` ما بيتطابق مع صفحة صاحب المود، فـ ZombieBuddy كان يرفض يحمّل Viewpoint. المشكلة عامة عند اللاعبين يوم 2026-11-16.",
      "- الملف انشال من مجلد المود بطلب جمال، فـ ZombieBuddy رجع يعتمد على الموافقة على الملف نفسو. تحديث Viewpoint الجاي بيرجّع ملف التوقيع لحالو.",
      "- إذا رجع Viewpoint ينستبعد بعد تحديث، السبب على الأغلب نفسو. السجل بيكتب: `ZBS verification invalid`.", "",
      "معظم ملحقات Viewpoint المفعّلة كود الجافا تبعهم بيستعمل أجزاء داخلية من Viewpoint، وكلهم مبنيين قبل 0.1.7. القائمة بتطلع بـ `05_TOOLS/scan_viewpoint_addons.py`.", "",
      "## القائمة الكاملة بالترتيب", "",
      "| # | المود | الاسم |", "|---|---|---|"]
for i, m in enumerate(order, 1): L.append("| %d | `%s` | %s |" % (i, m, names.get(m, "").replace("|", "/")))
io.open(OUT, "w", encoding="utf-8", newline="\n").write("\n".join(L) + "\n")
print("written", len(order), "mods; with a name", sum(1 for m in order if m in names), "; body rows", sum(1 for m in order if m in BODY))
