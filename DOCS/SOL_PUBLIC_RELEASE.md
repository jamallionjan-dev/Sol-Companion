# Sol 0.28.3: a smart companion for Project Zomboid (Build 42.22)

## About Sol
**Sol: an AI companion for Project Zomboid (B42)**

Sol isn't a regular NPC. You chat with her in Arabic like you would with a friend, and she understands and acts. Behind her is a "mind" connected to an AI model, so there are no fixed commands: she gets the dialect and even typos, and replies in character, naturally.

- 🚗 **Driving:** She drives to any address on real roads, even through unexplored areas. Three speeds (20 / 40 / 65 km/h). She parks smartly and turns the engine off when she gets out, unless you tell her to keep it running. She honks once or all the way there. She drives KI5 vehicles, including the Bradley tank.
- 📒 **Address book:** Every brochure, map or flyer you open while she's near is saved and sorted by type. Tap a name and she drives you there.
- 🌾 **Farming:** She tills, plants and waters, and keeps caring for the farm while you're away.
- 💬 **Conversation:** She knows the street and town you're in, understands two orders in one sentence ("turn off the engine and get out"), and when something fails she tells you why in plain words.
- 😉 **Secret weapon:** comes with her in every new life.
- 🧠 **Memory:** She remembers places and addresses. When she dies she forgets everything, like a real person.
- ⏳ **Coming soon:** "Come to me by car": she grabs the nearest car and drives to you from anywhere.

**سول، رفيقة ذكية بـ Project Zomboid (B42)**

سول مش NPC عادي. بتحكي معها بالعربي متل ما بتحكي مع صاحبك، وهي بتفهم وبتنفّذ. وراها "عقل" موصول بموديل ذكاء اصطناعي، فما في أوامر ثابتة: بتفهم اللهجة وحتى الغلطات، وبتردّ بشخصيتها وبشكل طبيعي.

- 🚗 **السواقة:** بتسوق لأي عنوان عالشوارع الحقيقية، حتى بالمناطق اللي ما انكشفت. 3 سرعات (20 و40 و65). بتصف بذكاء، وبتطفي المحرك لما تنزل إلا إذا قلتلها خليه شغال. بتزمّر مرة أو طول الطريق. وبتسوق سيارات KI5، ومنها مدرعة البرادلي.
- 📒 **دفتر العناوين:** كل بروشور أو خريطة أو إعلان بتفتحو وهي جنبك بينحفظ ومرتّب حسب نوعو. بتكبس عالاسم وبتاخدك لعندو.
- 🌾 **الزراعة:** بتفلح وبتزرع وبتسقي، وبتضل تهتم بالمزرعة وإنت بعيد.
- 💬 **الحكي:** بتعرف الشارع والمدينة اللي إنتو فيهم، وبتفهم أمرين بجملة وحدة ("طفي المحرك ونزلي")، وإذا شي فشل بتقلك ليش بكلام عادي.
- 😉 **السلاح السري:** بيجي معها بكل حياة جديدة.
- 🧠 **الذاكرة:** بتتذكّر الأماكن والعناوين. ولما تموت بتنسى كلشي، متل البني آدم.
- ⏳ **قريباً:** "تعالي لعندي بالسيارة": بتاخد أقرب سيارة وبتجي لعندك من أي مكان.

> Private copy for personal use; appearance assets belong to their authors, do not redistribute.
> نسخة خاصة للاستعمال الشخصي. أشيا شكل سول ملك أصحابها، لا تنشرها.

## English
Sol is a companion who talks with you in Arabic (Levantine) and does what you ask. You type or speak to her in the Sol chat window, and her "mind" (an AI model) understands the request and carries it out in the game.

**Proven in play:**
- **Driving:** GPS driving on real roads (even unexplored areas), 3 speeds (20/40/65 km/h), getting around stuck cars.
- **Cars:** smart parking, engine off when she gets out (unless you say keep it running), lights, horn and held horn.
- **Farm and home:** full farm care, also while you are away.
- **Address book:** every map, brochure or house flyer you open near her is saved. Tap an entry and she drives you there.
- **Questions:** street and town questions, and "why did it fail".
- **Orders:** two orders in one sentence.

Built but not yet fully tested: chickens, storage sorting. Coming soon: she comes to you by car from far away.

**Requirements**
- Project Zomboid Build 42.22.
- ZombieBuddy (Steam Workshop), required. Approve Sol's Java file when it asks.
- Python 3.10+ and an AI model. Either a local server compatible with Ollama/OpenAI, such as Ollama or LM Studio, or an API key.

**Install**
1. Copy `Zomboid\mods\Sol` to `C:\Users\<you>\Zomboid\mods\`.
2. Copy `Zomboid\Lua\SolFixes_MAIN.txt` to `C:\Users\<you>\Zomboid\Lua\`. This file turns features on and off.
3. Enable ZombieBuddy, then Sol, in the game's Mods menu.
4. Start the mind: `python SolMind\sol_mind.py`. In game, open Sol's settings and set your model's address (e.g. `http://localhost:11434/v1`) and model name.
   - Optional: for a LAN server with a self-signed certificate, set the environment variable `SOL_PINNED_TLS_HOST` to its host and put its `.pem` as `SolMind\iphone_localcoder.pem`.

**License:** Sol is built on Living Fellows (MIT). See `Zomboid/mods/Sol/LICENSE.txt` and `THIRD_PARTY_ASSETS.md`.

## عربي
سول رفيقة بتحكي معك بالعربي (شامي) وبتعمل اللي بتطلبو. بتكتبلها أو بتحكيلها بشباك محادثة سول، و"عقلها" (موديل ذكاء اصطناعي) بيفهم الطلب وبينفّذو باللعبة.

**مجرّب باللعبة:**
- **السواقة:** سواقة بالـGPS عالشوارع الحقيقية (حتى المناطق اللي ما انكشفت)، و3 سرعات (20 و40 و65)، وبتلفّ حوالين السيارات العالقة.
- **السيارة:** صفّ ذكي، وبتطفي المحرك لما تنزل (إلا إذا قلتلها خليه شغال)، والضو، والزمّور والزمّور المستمر.
- **المزرعة والبيت:** اهتمام كامل بالمزرعة، حتى وإنت بعيد.
- **دفتر العناوين:** كل خريطة أو بروشور أو إعلان بيت بتفتحو وهي جنبك بينحفظ، وبتكبس عليه فبتاخدك لعندو.
- **الأسئلة:** اسم الشارع والمدينة، و"ليش ما زبطت".
- **الأوامر:** أمرين بجملة وحدة.

مبني بس لسّا ما انجرّب كامل: الدجاج، وترتيب المستودع. وقريباً: تجيك بالسيارة من بعيد.

**المتطلبات**
- Project Zomboid Build 42.22.
- ZombieBuddy من الـWorkshop (لازم). وافق على ملف جافا تبع سول لما يسألك.
- Python 3.10 أو أحدث، وموديل ذكاء اصطناعي: يا سيرفر محلي متوافق مع Ollama أو OpenAI (متل Ollama أو LM Studio)، يا مفتاح API.

**التركيب**
1. انسخ `Zomboid\mods\Sol` لـ `C:\Users\<اسمك>\Zomboid\mods\`.
2. انسخ `Zomboid\Lua\SolFixes_MAIN.txt` لـ `C:\Users\<اسمك>\Zomboid\Lua\`. هاد الملف بيشغّل وبيطفي الميزات.
3. فعّل ZombieBuddy وبعدين Sol من قائمة المودات.
4. شغّل العقل: `python SolMind\sol_mind.py`. وباللعبة، من إعدادات سول، حط عنوان الموديل (مثلاً `http://localhost:11434/v1`) واسمو.

**الترخيص:** سول مبنية على Living Fellows (رخصة MIT). شوف `Zomboid/mods/Sol/LICENSE.txt` و`THIRD_PARTY_ASSETS.md`.

---
## Public release: blocked (2026-11-11)
- **Blockers:**
  - 42/SOL_APPEARANCE_LOCAL_ONLY.txt says the appearance assets are local use only. They come from VSGirlBodyExtension, VSGirl Hair VS, Fluffy Hair / Tomb's Goth Hair and SPNCC, with no redistribution permission.
  - sound/LFUrinate.ogg is under the Pixabay licence, which restricts standalone redistribution.
  - The SolCombined.jar PlayerBodyModels patch may contain VSGirl-derived code.
- **Next:**
  1. Make a stripped build: remove those assets and the .ogg; Sol falls back to the vanilla body.
  2. Check the jar.
  3. Push to https://github.com/jamallionjan-dev/Sol-Release (empty, created by Jamal).
  4. gh release v0.28.3 with the zip.
- **Private copy:** C:\Users\JAMAL\Desktop\Sol-0.28.3-for-friend.zip, for personal sharing only.

---
## Goal from Jamal (2026-11-11 02:05): the player only opens the game and enables the mods

### Next steps (not started; stopped for budget)

**1. Bundle the mind and Python in the mod.**
- Put SolMind in `mods\Sol\42\mind\`.
- Put the official Windows embeddable Python (python.org, 3.12 amd64 embed zip; verify the sha256) in `mods\Sol\42\python\`.
- Downloading Python needs Jamal's OK (file, source, size).
- The mind is stdlib-only (lupa is only used in demo mode), so the embeddable Python should run it. Check that `._pth` allows the mind dir.

**2. Auto-start the mind from SolCombined.jar** (ZombieBuddy Java, at mod init, behind switch `mind_autostart`):
1. If a mind is already running, do nothing. Check its heartbeat or lock in `%USERPROFILE%\Zomboid\Lua`; Jamal's HKCU "SolMindService" must keep working, and there must never be two minds.
2. Otherwise start `<modDir>\python\pythonw.exe <modDir>\mind\sol_mind.py --lua-dir <Zomboid\Lua> --game-pid <pid>` hidden. Its working dir and secrets stay per-user.
3. Stop it with a JVM shutdown hook plus the `--game-pid` self-stop.
4. Then run linkcheck and patch_access_check. ZombieBuddy approval is needed once.

**3. A default model with no key** (research only):
- **Option A:** a keyless public endpoint. Check its terms and limits; the README must say where chats are sent.
- **Option B:** ship with "Manual" (no AI) and the Groq key as optional (console.groq.com/keys, free tier).
- Never send chats anywhere without saying so in the README.

**4. Package:** a zip holding only the `Sol` folder for `Zomboid\mods`, plus a README in Arabic and English. The user's steps:
1. Subscribe to ZombieBuddy on the Steam Workshop.
2. Unzip into `mods`.
3. Enable ZombieBuddy and Sol, and approve the Java file once.

**5. Test** in game (needs Jamal's OK to launch) and on a second PC.

### Interim (works today)
`Desktop\Sol-0.28.3-for-friend.zip` contains the mod, the mind and `START_SOL_MIND.bat`. The friend installs Python, double-clicks the bat, and keeps its window open.

The installer and Run-entry approach was dropped by Jamal's new goal.

---
## One-click friend package (2026-11-11 morning)

- **Build:** `powershell -ExecutionPolicy Bypass -File 05_TOOLS\packaging\build_friend_package.ps1`. It builds from the installed release, the Mind and `05_TOOLS\packaging\friend_files`. It downloads and verifies the embeddable Python 3.12.10 (sha256 4acbed6d…, from python.org's SPDX), scrubs personal data, and writes `08_PUBLIC\Sol-<ver>.zip` plus `Desktop\Sol-<ver>-for-friend.zip`.
- **Player steps:**
  1. Double-click `PLAY SOL.bat`. It installs and enables the mod, starts the hidden mind service with the bundled pythonw, and launches the game.
  2. Approve ZombieBuddy's prompt the first time.
  3. Put in a Groq key.
- **Robustness:**
  - it unblocks Mark-of-the-Web files;
  - it warns when run from inside the zip;
  - it warns when pythonw is missing;
  - logs: `sol_launcher_log.txt`, `SolMind\sol_mind_service.log`, `SolMind\sol_mind_log.txt`, `SolMind\sol_mind.log`;
  - `FIX - اصلاح.bat` runs the mind in a visible window.
- **Friend's report:** "Groq connected, Sol never replies".
  - The chat path is reproduced as working with a mocked provider.
  - Likely cause (UNCONFIRMED): the model route timeout of 4 s / 80 tokens was tuned for the LAN phone.
  - Fix (6fbfb3a): provider-aware, 4 s / 80 tokens for `custom` (LAN), 15 s / 200 tokens for cloud providers.
  - If it still fails, ask for `SolMind\sol_mind.log`.
- **Not done yet** (no death popup): the jar auto-start (no bat at all), a keyless default model, and the clean public build without the appearance assets.
