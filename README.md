# Sol 0.28.8: a smart companion for Project Zomboid (Build 42.22)

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
- An AI model (Python is bundled in the package). Either a local server compatible with Ollama/OpenAI, such as Ollama or LM Studio, or an API key.

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
- موديل ذكاء اصطناعي (Python موجود جوّا الملف): يا سيرفر محلي متوافق مع Ollama أو OpenAI (متل Ollama أو LM Studio)، يا مفتاح API.

**التركيب**
1. انسخ `Zomboid\mods\Sol` لـ `C:\Users\<اسمك>\Zomboid\mods\`.
2. انسخ `Zomboid\Lua\SolFixes_MAIN.txt` لـ `C:\Users\<اسمك>\Zomboid\Lua\`. هاد الملف بيشغّل وبيطفي الميزات.
3. فعّل ZombieBuddy وبعدين Sol من قائمة المودات.
4. شغّل العقل: `python SolMind\sol_mind.py`. وباللعبة، من إعدادات سول، حط عنوان الموديل (مثلاً `http://localhost:11434/v1`) واسمو.

**الترخيص:** سول مبنية على Living Fellows (رخصة MIT). شوف `Zomboid/mods/Sol/LICENSE.txt` و`THIRD_PARTY_ASSETS.md`.
