# -*- coding: utf-8 -*-
"""Generates SolSpeechAR.lua (pure ASCII, Arabic as backslash-uXXXX escapes) next to this script.
Sol speaks as a woman and addresses the player as a man. Levantine, short, no technical words.
LINES: the English line exactly as the game builds it -> Arabic. POOLS: dialogue topic -> short Arabic lines used when a line has no
translation of its own (several per topic so she does not repeat one sentence). usage: gen_speech_ar.py"""
import glob, json, os, re
BS = chr(92)
HERE = os.path.dirname(os.path.abspath(__file__))

LINES_TEXT = u"""
Evening already. Keep an eye on the shadows. ||| صار المسا. دير بالك عالضلال.
It is getting dark. I'd rather have everyone inside. ||| عم تعتم. بفضّل الكل يكون جوّا.
It will be dark soon. Time to think about shelter. ||| قرّبت تعتم. لازم نفكر وين بدنا نلتجي.
Let's count heads before we settle in for the night. ||| خلينا نعدّ حالنا قبل ما نرتاح هالليلة.
Good morning. It is almost strange how normal that sounds. ||| صباح الخير. غريب كيف لسا بتطلع عادية.
Good morning. Let's see what today gives us. ||| صباح الخير. خلينا نشوف شو مخبى لنا اليوم.
New day. Same rules: stay sharp and stay alive. ||| نهار جديد ونفس القصة: صحصح وضل عايش.
New day. We should review our supplies. ||| نهار جديد. لازم نشوف شو ضايل عنا.
Here comes the rain. Watch the corners; hearing will be worse. ||| إجت الشتا. دير بالك عالزوايا، ما رح نسمع منيح.
I don't like what this does to our hearing. ||| مو عاجبني شو عم تعمل بسمعنا.
Rain's setting in. The noise will hide more than our footsteps. ||| الشتا نازلة. صوتها رح يغطي أكتر من صوت خطواتنا.
We're getting wet. Let's keep an eye out for somewhere dry. ||| عم نتبلل. خلينا نلمح محل ناشف.
You're getting soaked. Let's find cover when we can. ||| تبللت كتير. أول ما نقدر، خلينا نلاقي سقف.
Attention! Free brains at the Muldraugh water tower! ||| يا جماعة! في مخاخ ببلاش عند خزان المي!
Behind you! It's the tax man! ||| وراك! إجا تبع الضرايب!
HEY! Is that a Spiffo's coupon on the ground?! ||| هيه! هاد كوبون خصم عالأرض؟!
Hey! Somebody out there misses you! Go find them! ||| هيه! في حدا مشتقلك هونيك! روح دوّر عليه!
Look over there! A mule in a hospital gown! ||| شوف هونيك! بغل لابس روب مستشفى!
Look, a way out! For you! Over there! Please! ||| شوف، في طريق! إلك إنت! هونيك! الله يخليك!
Worth a try. Wasn't worth much. ||| جرّبناها. ما طلعت بشي.
A Kentucky mile always was longer than it looks. ||| المشوار هون دايماً أطول مما بيبيّن.
I'm counting the turns, in case we need to come back fast. ||| عم عدّ المفارق، بلكي احتجنا نرجع بسرعة.
If the army's holding the county line, they're doing it real quiet. ||| إذا الجيش لسا عالحدود، فهو ساكت كتير.
If we stop, I'll take the side you're not watching. ||| إذا وقفنا، باخد الجهة يلي ما عم تشوفها.
Keep going. I've got your back. ||| كمّل، أنا حامية ضهرك.
Knox County never looked this empty on a weekday. ||| عمرها البلد ما كانت فاضية هيك بنص الجمعة.
Mind the cars. Something always hides behind one. ||| دير بالك عالسيارات، دايماً في شي مخبى وراها.
Nobody's paying bills anymore. Silver lining, I reckon. ||| ما حدا عم يدفع فواتير هلأ. على الأقل هاي منيحة.
Scenic route again? You spoil me. ||| كمان الطريق الحلوة؟ دلعتني.
Slow is fine. Slow is alive. ||| شوي شوي منيح. شوي شوي يعني عايشين.
Walking the county like a census taker. Head count's way down. ||| عم نمشي البلد متل موظف الإحصاء، والعدد نازل كتير.
I'll just stand here and age, then. ||| تمام، بوقف هون وبختير.
Is this a strategy, or are we lost? ||| هاي خطة ولا ضعنا؟
Quiet is good. Quiet is fine. I'll keep an eye out. ||| الهدوء منيح. أنا عم ضل منتبهة.
At this rate, the tires will retire before we do. ||| هيك الدواليب بتتقاعد قبلنا.
Dashboard clock's wrong. Still making better progress than us. ||| ساعة السيارة غلط، ومع هيك ماشية أحسن منا.
Do we need gas, or a written invitation? ||| بدنا بنزين ولا دعوة مكتوبة؟
Engine's not gonna fix itself. Neither is my mood. ||| المحرك ما رح يصلح حاله، ولا مزاجي.
I could walk faster than this. Sitting down. ||| بمشي أسرع من هيك وأنا قاعدة.
I've counted every crack in the windshield. Want the report? ||| عدّيت كل شق بالزجاج. بدك التقرير؟
Parked this long, I'd like to know which way we're leaving. ||| وقفنا كتير، بدي أعرف من وين بدنا نطلع.
Picture the mailman showing up. I'd hug him. Then check for bites. ||| تخيل يطلع علينا موزع البريد. بحضنه، وبعدين بفحصه من العض.
Every tree we pass, my brain asks what if. ||| كل شجرة منمر حدها، راسي بيسأل: طيب وإذا؟
One side's all teeth. I'm taking the quieter direction. ||| هالجهة كلها سنان. أنا باخد الجهة الأهدى.
Pressure's building too fast. I'm giving ground. ||| الوضع عم يضيق بسرعة. أنا عم ارجع لورا.
That side's pouring dead people. I'm moving across the flow. ||| هالجهة نازل منها الموتى نزول. بقطع من بينهم.
Dry county jokes hit different when clean water's scarce. ||| نكتة العطش بتصير موجعة لما المي بتقل.
Feels almost like an ordinary day. Don't tell anybody. ||| حاسة إنه نهار عادي تقريباً. لا تقول لحدا.
Funny how a room can feel crowded with nobody in it. ||| غريب كيف الغرفة بتحسها مليانة وما فيها حدا.
Funny thing, the end of the world. Still got chores. ||| غريبة نهاية الدنيا. والشغل لسا ما خلص.
Give it a year, maybe we'll have the only porch light in Kentucky. ||| يمكن بعد سنة يكون عنا آخر ضو ببلكونة بالبلد كلها.
Good news, no commute. Bad news, the reason why. ||| الخبر الحلو ما في مواصلات. الخبر الوحش ليش ما في.
Hard to picture a Derby with nobody in the stands. ||| صعب أتخيل المدرجات فاضية هيك.
I'd trade every dollar in this county for cold sweet tea. ||| بدفع كل مصاري البلد مقابل كاسة شاي بارد.
I'll keep looking. You keep watch. ||| أنا بكمل تدوير، وإنت خليك منتبه.
If anybody asks, I'm on break. Have been since July. ||| إذا حدا سأل، أنا بإجازة من تموز.
If we split up, keep your voice low and close. ||| إذا تفرقنا، خلي صوتك واطي وقريب.
If you see trouble first, say it plain. ||| إذا شفت شي قبلي، قوله بصراحة.
Keep an ear on the doors. I'll mind this side. ||| خلي سمعك عالبواب، وأنا باخد هالجهة.
Keeping busy at the end of the world. Mama would be proud. ||| مشغولين بآخر الدنيا. أمي كانت رح تفتخر.
Kentucky weather never cared who was left to complain about it. ||| الطقس هون عمره ما سأل مين ضايل ليشكي.
Maybe a radio's still promising help. Bless its heart. ||| يمكن في راديو لسا عم يوعد بالمساعدة. الله يعينه.
Mind the mess. Civilization left in a hurry. ||| ما تدقق عالفوضى. الحضارة راحت بعجلة.
Nothing like routine to keep the screaming on the inside. ||| ما في متل الروتين ليضل الصراخ جواتي.
Remember to drink some water when you can. ||| ما تنسى تشرب مي لما تقدر.
Somebody used to have a normal day here. ||| حدا كان عنده يوم عادي هون.
Take a breath if you need one. I'll keep going. ||| خدلك نفس إذا بدك، وأنا بكمل.
The road outside looks calm. I don't trust it yet. ||| الطريق برا هادية. بس لسا ما بوثق فيها.
This used to count as a work party. Minus the potluck. ||| هاد كان يعتبر شغل جماعة، بس من غير عزيمة.
Tobacco farmers knew the secret: keep your hands busy. ||| الفلاحين كانوا عارفين السر: خلي إيديك مشغولة.
We have time. Let's use it carefully. ||| معنا وقت. خلينا نستفيد منه.
Work quiet when we can. Noise draws them like hogs to a bucket. ||| اشتغل بهدوء لما تقدر. الصوت بيجيبهم متل الدود عالعسل.
You holding up? You don't have to answer right away. ||| ماشي الحال معك؟ ما بدي جواب هلأ.
I'm engaging. Don't get surrounded! ||| أنا داخلة عليهم. ما تخليهم يطوقوك!
Several walkers. Focus the nearest! ||| في كم واحد. شوف الأقرب!
I'll handle this one! ||| هاد عليي!
One contact. I'm taking it! ||| واحد قدامي، عليي!
Out of my county! ||| برا من بلدي!
Two contacts. Keep them from flanking us. ||| تنين. ما تخليهم يدوروا حوالينا.
Two contacts. Take them one at a time! ||| تنين. واحد واحد!
Big pack! Stop fighting and move! ||| كتير! خلص قتال ويلا!
Six-plus on us. Withdraw! ||| أكتر من ستة علينا. لورا!
Break contact with the group! ||| ابعدوا عن هالجماعة!
Back away from it! ||| لورا عنه!
Back up! This one's too close! ||| لورا! هاد قريب كتير!
Move back and make it follow! ||| ارجع لورا وخليه يلحقك!
Two on us! Pull back! ||| تنين علينا! لورا!
Go down! ||| موت!
Don't worry about me. Okay. Worry a little. ||| ما تقلق عليي. طيب، اقلق شوي.
%1, am I going to die? Just say it straight. ||| قول لي بصراحة، رح موت؟
How long do you think I've got? No. Don't answer that. ||| قديش برأيك ضايل لي؟ لأ، ما تجاوب.
I can still feel my fingers. That's good, right? That's good. ||| لسا حاسة بأصابعي. منيح، مو؟ منيح.
I don't want to die out here. Not like this. ||| ما بدي موت هون. مو هيك.
I keep looking at it. Like if I stare long enough, it'll go away. ||| ضلني اتطلع فيها، كأن إذا طولت بتروح.
I keep thinking about my mom's kitchen. Isn't that stupid? ||| عم فكر بمطبخ أمي. مو سخيفة هالشغلة؟
I'm not ready. I had plans. Stupid little plans, but they were mine. ||| أنا مو جاهزة. كان عندي خطط صغيرة، بس كانت إلي.
I'm scared. I'm really, really scared. ||| أنا خايفة. خايفة كتير.
If I start acting strange, you tell me. Promise me. ||| إذا صرت غريبة، خبرني. وعدني.
It's just a bite. People survive bites. Right? Somebody tell me people survive bites. ||| عضة وبس. الناس بتعيش بعد العض، مو؟ حدا يقلي مو هيك.
Maybe it didn't break the skin. Maybe. Maybe. ||| يمكن ما اخترقت الجلد. يمكن.
Who's going to look after all of you when I'm gone? ||| مين رح يهتم فيكن لما أروح؟
Don't cry. Hey. Don't cry. You'll make me cry, and I don't have time. ||| لا تبكي. هيه، لا تبكي. بتبكيني، وما معي وقت.
%1, I was somebody before all this. Please remember I was somebody. ||| كنت إنسانة قبل كل هاد. الله يخليك تذكر هالشي.
Hold my hand. I can't feel it anymore, but hold it anyway. ||| مسكني إيدي. ما عم حسها، بس امسكها.
I can't remember my mother's face. I had it this morning. ||| ما عم اتذكر وجه أمي. الصبح كنت متذكرته.
I don't wanna lose myself. Please. I don't want to forget who I am. ||| ما بدي اضيع حالي. الله يخليك، ما بدي انسى مين أنا.
I don't want to hurt anybody. Promise me I won't hurt anybody. ||| ما بدي أذي حدا. وعدني إني ما رح أذي حدا.
I'm so tired. I'm so tired, and I'm so scared. ||| تعبانة كتير. تعبانة وخايفة.
I'm sorry. I'm sorry for all of it. ||| سامحني. سامحني على كل شي.
Is it cold in here, or is it just me? It's just me, isn't it. ||| في برد هون ولا أنا بس؟ أنا بس، مو هيك؟
It's getting dark in my head. Like lights going out, room by room. ||| عم تعتم براسي. متل الضو يلي عم ينطفي غرفة غرفة.
Say my name. Keep saying it, so I don't forget it. ||| ناديني باسمي، خلي تعيده، حتى ما انساه.
When it happens, it won't be me. Remember that. It won't be me. ||| لما يصير، ما رح كون أنا. تذكر هالشي. ما رح كون أنا.
You were good to me. All of you. Tell them I said so. ||| كنتوا منيحين معي، كلكن. قوللهم أنا قلت هيك.
Can somebody get me a blanket? I can't get warm. ||| حدا يجبلي حرام؟ ما عم ادفى.
Don't leave me alone tonight. Please. ||| ما تتركني لحالي الليلة. الله يخليك.
Don't sit so close. I don't want it to be you next. ||| ما تقعد قريب كتير. ما بدي تكون إنت الجاي.
%1, my head's full of fog. Say something so I know where I am. ||| راسي مليان ضباب. احكي شي حتى أعرف وين أنا.
I can taste metal. Nothing tastes right anymore. ||| طعمة حديد بتمي. ولا شي طعمته متل قبل.
I feel cold. Why am I so cold? It's the middle of summer. ||| بردانة. ليش بردانة هيك والدنيا صيف؟
I had a dog once. His name was... I can't remember his name. ||| كان عندي كلب مرة. اسمه كان... نسيت اسمه.
I keep losing minutes. Did I already say that? ||| عم ضيع دقايق. قلت هالحكي قبل؟
I'm burning up and freezing at the same time. ||| عم ولع وبرد بنفس الوقت.
If you ever find my family, tell them I tried. Tell them I tried so hard. ||| إذا شفت أهلي يوماً، قولهم حاولت. حاولت كتير.
My hands won't stop shaking. ||| إيدي ما عم تهدا من الرجفة.
Talk to me. Keep talking. If you talk, I'm still here. ||| احكي معي. ضل احكي. طول ما عم تحكي، أنا هون.
Crowd of deadheads. Watch the sides. ||| جماعة كبيرة من الموتى. انتبه عالجوانب.
Crowd of zombies ahead. ||| جماعة كبيرة منهم قدامنا.
I count at least six. ||| عدّيت ستة عالأقل.
I've got at least half a dozen. ||| عندي ستة عالأقل.
Four walkers, give or take one. ||| أربعة تقريباً، زايد ناقص واحد.
Four walkers. Nobody goes in alone. ||| أربعة. ما حدا يفوت لحاله.
Several ahead. Stay together and don't rush. ||| في كم واحد قدامنا. خلينا سوا وما تستعجل.
Three or four zombies ahead. ||| تلاتة أو أربعة قدامنا.
We've got a cluster of them ahead. ||| في جماعة منهم قدامنا.
*goes quiet* Something dead is moving nearby. ||| *بتسكت* في شي ميت عم يتحرك قريب.
*listens* I heard a walker. ||| *بتتسمع* سمعت واحد منهم.
Horde ahead! ||| موجة قدامنا!
Horde! Stay together and follow me out. ||| موجة! خلينا سوا وتعال وراي.
Huge horde in front of us. ||| موجة كبيرة قدامنا.
Mass of dead ahead. Do not go that way. ||| في ناس ميتين كتير قدام. ما نروح من هون.
Nobody gets left behind. Move away from them. ||| ما حدا بينترك. ابعدوا عنهم.
That road is lost. Horde. ||| هالطريق انتهت. في موجة.
The dead own that whole block. ||| الموتى ماخدين هالحارة كلها.
The whole street is moving. ||| الشارع كله عم يتحرك.
They're everywhere up there. ||| هني بكل مكان هونيك.
Wall of walkers ahead. ||| في حيط منهم قدامنا.
Contact. One zombie. ||| في واحد.
I see one. Keep your eyes on it. ||| شايفة واحد. خلي عينك عليه.
Just one in sight. Watch yourself. ||| بس واحد مبين. دير بالك.
Just one zombie in sight. ||| بس واحد مبين.
One body moving. Not alive. ||| في جسم عم يتحرك. مو عايش.
One deadhead, out ahead. ||| في واحد قدامنا.
One of them, straight ahead. ||| في واحد منهم دغري قدامنا.
One walker. I've got it. ||| واحد. عليي.
One zombie ahead. ||| في واحد قدامنا.
One zombie ahead. Stay close to me. ||| في واحد قدامنا. خليك حدي.
Single contact ahead - nothing we can't handle. ||| واحد قدامنا. بنقدر عليه.
Single walker, up ahead. ||| في واحد لحاله قدامنا.
We've got a single contact. ||| عنا واحد.
I count two. ||| عدّيت تنين.
I've got two moving together. ||| في تنين ماشيين سوا.
Not one. Two of them. ||| مو واحد. تنين.
Pair of walkers, front. ||| تنين قدام.
There's a pair up ahead. ||| في تنين قدامنا.
Two ahead. Stay where I can see you. ||| تنين قدامنا. خليك وين شايفتك.
Two bodies moving our way. ||| تنين جايين لعنا.
Two contacts in sight. ||| في تنين مبينين.
Two zombies ahead. ||| تنين قدامنا.
Two zombies. Don't let them come side by side. ||| تنين. ما تخليهم يجوا مع بعض.
Watch it. Two zombies. ||| انتبه، تنين.
Seated walker. Waiting doesn't make it harmless. ||| في واحد قاعد. ولو قاعد، ما بيأمن.
Sitting walker. I'll deal with it. ||| في واحد قاعد. عليي.
Waiting is just resting, but boring. Let's move. ||| الانتظار راحة بس مملة. يلا نتحرك.
I appreciate it. I'll keep it ready. ||| يسلمو. رح خليها جاهزة.
I'll take care of it. And I'll use it when it counts. ||| رح ديرها بالي. وبستعملها لما تلزم.
Got loose! ||| فلتت!
%1, I don't want our last moment to be this! ||| ما بدي تكون آخر لحظة بيناتنا هيك!
Easy there. I bruise same as you. ||| شوي شوي، أنا كمان بتوجع.
*holds up four fingers: small group ahead* ||| *بترفع أربع أصابع: جماعة صغيرة قدام*
*shows four, then pairs two fingers: team up* ||| *بتأشر بأربعة وبعدين بإصبعين: مع بعض*
*draws a line across their throat and points away from the horde* ||| *بتمرر إيدها عرقبتها وبتأشر بعيد عن الموجة*
*makes a wide crowd signal, then urgently motions everyone back* ||| *بتأشر بإيدها إشارة موجة كبيرة وبتطلب الكل يرجع*
*points low, then shows one finger* ||| *بتأشر لتحت وبعدين بإصبع واحد*
*holds two fingers low, then points forward* ||| *بتأشر بإصبعين وبعدين لقدام*
*raises two fingers: two walkers ahead* ||| *بترفع إصبعين: تنين قدام*
*shows two fingers, then motions to split them apart* ||| *بتأشر بإصبعين وبتفرق بينهم*
*signals two contacts near each other* ||| *بتأشر: تنين قراب من بعض*
*two fingers, then a chopping motion: split them* ||| *إصبعين وبعدين بتشق الهوا: فرقوهم*
Too high, bad grip. Pick another route. ||| عالية وما في مسكة. شوف طريق تانية.
That fence collected its toll in dignity. ||| هالحيط خد مني كرامتي.
Zombie! Watch out! ||| في واحد! انتبه!
I was bitten. We need to decide what happens next. ||| عضوني. لازم نقرر شو بدنا نعمل.
No. Wasn't them. I don't think. ||| لأ. مو هني. على ما بظن.
All right. I will come with you. ||| ماشي، جاية معك.
I understand. Take care. ||| فهمت. دير بالك على حالك.
Contact - one infected. ||| في واحد قريب.
Multiple contacts. ||| في كتير.
Room clear. ||| الغرفة فاضية.
Can't verify the whole room. ||| ما شفت الغرفة كلها.
Nothing in this one. Next lid. ||| ما في شي هون. عالتاني.
"""

POOLS = {
 "danger.one": [u"في واحد قدامنا. خليك حدي.", u"واحد منهم. عيني عليه.", u"في واحد قريب. دير بالك."],
 "danger.pair": [u"تنين قدامنا. دير بالك.", u"في تنين. ما تخليهم يجوا سوا."],
 "danger.group": [u"في كم واحد قدامنا. خلينا سوا.", u"جماعة منهم قدام. ما تستعجل."],
 "danger.crowd": [u"في كتير منهم. دير بالك عالجوانب.", u"كتير قدامنا. انتبه."],
 "danger.horde": [u"موجة كبيرة قدامنا. لورا!", u"الدنيا مليانة قدام. ما نروح من هون.", u"كتير كتير. خلينا نبعد."],
 "danger.heard": [u"*بتسكت* سمعت شي قريب.", u"في شي عم يتحرك قريب."],
 "danger.sitting": [u"في واحد قاعد. ما تأمن له."],
 "danger": [u"انتبه، في خطر قريب.", u"دير بالك، في شي مو طبيعي."],
 "combat.engage.one": [u"هاد عليي!", u"خليه عليي."],
 "combat.engage.pair": [u"تنين! واحد واحد.", u"ما تخليهم يدوروا حوالينا."],
 "combat.engage.group": [u"عليهم! ما تخليهم يطوقوك.", u"شوف الأقرب!"],
 "combat.engage.crowd": [u"كتير علينا! خليك حدي.", u"ما توقف بنصهم!"],
 "combat.engage.horde": [u"كتير كتير! يلا نبعد.", u"ما فينا عليهم هون!"],
 "combat.engage": [u"أنا داخلة!", u"خليك حدي!"],
 "combat.retreat": [u"لورا! لورا!", u"ارجع هلأ!", u"خلينا نبعد من هون!"],
 "combat.struggle": [u"موت!", u"ابعد عني!"],
 "combat.kill": [u"واحد ناقص.", u"خلص أمره."],
 "combat": [u"أنا معك، خلينا نخلص.", u"دير بالك!"],
 "banter.routine": [u"أنا هون إذا احتجت شي.", u"ضلينا ماشيين، هيك أحسن.", u"ما تنسى تشرب مي.", u"شغل ودردشة، متل زمان.", u"خلينا هادين ومركزين.", u"لسا ما زهقت منك.", u"يوم كمان وعايشين.", u"اسمع، الوضع منيح هلأ."],
 "banter.follow": [u"أنا وراك.", u"كمل، أنا حامية ضهرك.", u"وين ما بدك، أنا معك.", u"عيني عالطريق."],
 "banter.idle.vehicle": [u"وقفنا كتير، وين رايحين؟", u"بدنا بنزين ولا شو؟"],
 "banter.idle": [u"لسا مطولين؟", u"شو خطتنا؟", u"وقفنا كتير هون."],
 "banter.distraction": [u"هيه! من هون!", u"لهون! لهون!"],
 "banter.refusal": [u"لأ، هالطريق مو منيحة.", u"خليني آخد الجهة الأهدى."],
 "banter.interior": [u"راسي تعبان شوي.", u"خليني اتنفس شوي."],
 "banter.intrusive": [u"الأفكار ما عم توقف براسي."],
 "banter": [u"أنا معك.", u"كله تمام؟", u"خلينا نكمل."],
 "ambient.morning": [u"صباح الخير.", u"نهار جديد، يلا."],
 "ambient.dusk": [u"عم تعتم، خلينا ندير بالنا.", u"المسا جاي."],
 "ambient.rain": [u"الدنيا عم تشتي.", u"الشتا نازلة، خلينا نلاقي سقف."],
 "ambient": [u"الجو هادي هلأ.", u"كله هادي."],
 "signal.one": [u"*بتأشر بإصبع واحد*"],
 "signal.pair": [u"*بتأشر بإصبعين*"],
 "signal.group": [u"*بتأشر بأصابعها: كم واحد قدام*"],
 "signal.crowd": [u"*بتأشر: كتير قدام*"],
 "signal.horde": [u"*بتأشر: موجة كبيرة، ارجعوا*"],
 "signal": [u"*بتأشر بإيدها: انتبه*"],
 "crisis.fear.early": [u"أنا خايفة.", u"خليك حدي شوي."],
 "crisis.fear.mid": [u"ما عم حس حالي منيحة.", u"ما تتركني لحالي."],
 "crisis.fear.late": [u"ما تتركني.", u"تعبانة كتير."],
 "crisis": [u"خليك معي.", u"أنا مو منيحة."],
 "crisis_self": [u"أنا مو منيحة.", u"خليك حدي."],
 "crisis_other": [u"لازم نساعد.", u"خلينا نشوف شو فينا نعمل."],
 "lastwords": [u"ما تنساني.", u"خليك عايش."],
 "death": [u"الله يرحمه."],
 "grief": [u"لسا موجوعة.", u"بدي شوي وقت."],
 "loss": [u"صعبة كتير.", u"لسا موجوعة."],
 "joy": [u"أخيراً شي منيح.", u"الحمد لله."],
 "stress": [u"أعصابي مو ثابتة.", u"بدي دقيقة، وبرجع."],
 "breakdown": [u"ما عم بقدر.", u"خليني شوي."],
 "recognition": [u"شبّهت عليه حدا بعرفه.", u"ضيعان، كان شكله متل حدا بعرفه."],
 "scavenge": [u"لقيت شي بيفيدنا.", u"مو بطال هاد."],
 "gift": [u"يسلمو.", u"تسلم إيدك."],
 "player_hit": [u"شو عم تعمل؟ أنا معك!", u"انتبه، أنا مو عدوة."],
 "grab": [u"فلتت!", u"ابعد عني!"],
 "bite": [u"عضوني.", u"مو منيح هاد."],
 "wound": [u"مجروحة، بس بكمل.", u"بدي ضماد."],
 "burn": [u"حرقتني.", u"موجوعة."],
 "symptoms": [u"مو حاسة حالي منيحة."],
 "infection": [u"مو حاسة حالي منيحة."],
 "medical": [u"خلينا نهتم بالإصابة.", u"بدي ضماد نضيف."],
 "healed": [u"صرت أحسن، يسلمو."],
 "care": [u"يسلمو.", u"خليك منيح إنت كمان."],
 "care_self": [u"خليني اهتم بحالي شوي."],
 "care_other": [u"خلينا نشوف شو بيلزمه."],
 "care_player": [u"إنت منيح؟", u"دير بالك على حالك."],
 "care_companion": [u"خلينا نشوف شو بيلزم."],
 "need.hunger": [u"جعانة.", u"بدي آكل شي."],
 "need.thirst": [u"عطشانة.", u"بدي شوية مي."],
 "need.fatigue": [u"تعبانة، بدي نام شوي.", u"ما عم فيني كمل هيك."],
 "need": [u"في شي ناقصني.", u"خلينا نأمن يلي بيلزمنا."],
 "status.water": [u"بدي مي."],
 "status.food": [u"بدي آكل."],
 "status.medical": [u"بدي علاج."],
 "status.bandages": [u"بدنا ضمادات."],
 "status.ammunition": [u"ذخيرتي قليلة."],
 "status.knox": [u"مو منيحة أبداً."],
 "status.grief": [u"لسا موجوعة."],
 "status.shaken": [u"أعصابي مو ثابتة."],
 "status.safety": [u"بدي مكان آمن."],
 "status.ready": [u"جاهزة.", u"أنا تمام."],
 "status": [u"أنا تمام.", u"ماشي الحال."],
 "doing": [u"عم كمل.", u"شوي وبخلص."],
 "work.missing.axe": [u"ناقصني فاس."],
 "work.missing.bait": [u"ما في طعم."],
 "work.missing.blowtorch": [u"ناقصني بخاخ لحام."],
 "work.missing.bowl": [u"ما في زبادي."],
 "work.missing.hammer": [u"ناقصني مطرقة."],
 "work.missing.heat_source": [u"بدي نار لأطبخ."],
 "work.missing.knife": [u"ناقصني سكين."],
 "work.missing.pan": [u"ناقصني مقلاة."],
 "work.missing.pot": [u"ناقصني طنجرة."],
 "work.missing.pry": [u"ناقصني عتلة."],
 "work.missing.rod": [u"ناقصني سنارة."],
 "work.missing.saw": [u"ناقصني منشار."],
 "work.missing.screwdriver": [u"ناقصني مفك."],
 "work.missing.shovel": [u"ناقصني مجرفة."],
 "work.missing": [u"ناقصني شي لهالشغلة."],
 "work.busy": [u"مشغولة هلأ."],
 "work.cannot": [u"ما بقدر هيك."],
 "work": [u"عم اشتغل.", u"خليني خلص هالشغلة."],
 "farm": [u"عم اشتغل بالأرض.", u"الزرع بدو شغل."],
 "fishing": [u"خليني اجرب مرة تانية."],
 "reading": [u"الكتاب عم يخليني افكر."],
 "repair": [u"عم صلح.", u"شوي وبخلص."],
 "workout": [u"عم حرك جسمي شوي."],
 "gestures": [u"يلا نتحرك."],
 "hygiene": [u"بدي انضف شوي."],
 "washed": [u"هلأ أحسن."],
 "downtime": [u"منيح ناخد لحظة هدوء.", u"خلينا نرتاح شوي."],
 "quiet": [u"خلينا نرتاح شوي."],
 "tactical": [u"انتبه."],
 "traversal": [u"خليني شوف طريق تانية."],
 "vehicle": [u"خلينا نمشي.", u"السيارة جاهزة."],
 "expedition": [u"خلينا نكمل الطريق."],
 "supply": [u"خلينا نشوف شو ناقصنا."],
 "inventory": [u"خلينا نرتب أغراضنا."],
 "team": [u"أنا معك."],
 "group": [u"أنا مع الجماعة."],
 "recruit": [u"ماشي، جاية معك."],
 "recruitment": [u"ماشي."],
 "join": [u"جاية معك."],
 "encourage": [u"عم تعمل منيح.", u"كفو."],
 "praise": [u"كفو عليك."],
 "trust": [u"بوثق فيك."],
 "promise": [u"وعد."],
 "promise_broken": [u"وعدتني."],
 "milestone": [u"وصلنا لهون سوا."],
 "relationship": [u"منيح إنك معي."],
 "nickname": [u"الاسم مو مهم، المهم مين واقف معك."],
 "witness": [u"شفت شو صار."],
 "witnessed_hurt": [u"إنت منيح؟"],
 "conflict": [u"خلينا نهدى."],
 "fight": [u"خلينا نخلص."],
 "fight_story": [u"بعدين بحكيلك."],
 "tale": [u"بعدين بحكيلك."],
 "tale_told": [u"هيك صارت."],
 "tales": [u"بعدين بحكيلك."],
 "talk": [u"خلينا نحكي بعدين."],
 "opinion": [u"بعدين منحكي."],
 "background": [u"بعدين بحكيلك."],
 "plans": [u"خلينا نشوف."],
 "stance": [u"خليها علي."],
 "decision": [u"خلينا نقرر."],
 "weather": [u"الجو عم يتغير."],
 "season": [u"الدنيا عم تتغير."],
 "time": [u"الوقت ماشي."],
 "noise": [u"شششش، خليك هادي."],
 "anchor": [u"خليك هون."],
 "escape": [u"يلا نبعد."],
 "mercy": [u"الله يرحم."],
 "respects": [u"الله يرحمه."],
 "burial": [u"الله يرحمه."],
 "ritual": [u"هيك أحسن."],
 "study": [u"عم اتعلم شي جديد."],
 "writer": [u"بدي اكتب شي."],
 "conversation": [u"ماشي.", u"تمام."],
 "faction": [u"خلينا ندير بالنا."],
 "player": [u"إنت منيح؟"],
 "zombie": [u"دير بالك منهم."],
 "interior": [u"خليني اتنفس شوي."],
}
DEFAULT = [u"تمام.", u"ماشي.", u"خلينا نكمل."]


def esc(s):
    return "".join(c if ord(c) < 128 else BS + BS + "u%04X" % ord(c) for c in s)


def lua_key(s):
    out = s.replace(BS, BS + BS).replace('"', BS + '"')
    return '"' + out + '"'


def parse_lines():
    out = {}
    for raw in LINES_TEXT.strip().splitlines():
        en, _, ar = raw.partition("|||")
        en, ar = en.strip(), ar.strip()
        assert en and ar, raw
        assert en not in out or out[en] == ar, en
        out[en] = ar
    return out


CODE = r"""
-- ---------------------------------------------------------------- merge into the existing line table
-- SolDialogueArabic.localize reads SolDialogueLines.lines (exact lines and %1 templates) on its first use.
if type(SolDialogueLines) == "table" and type(SolDialogueLines.lines) == "table" then
    for en, ar in pairs(S.lines) do
        if SolDialogueLines.lines[en] == nil then SolDialogueLines.lines[en] = ar end
    end
end
if type(SolDialogueArabic) == "table" and type(SolDialogueArabic.reset) == "function" then SolDialogueArabic.reset() end

-- ---------------------------------------------------------------- text
local BS_U = "<BS>u"
local function isHex4(hex) return string.find(hex, "^[0-9A-Fa-f][0-9A-Fa-f][0-9A-Fa-f][0-9A-Fa-f]$") ~= nil end

-- A line is a run of \uXXXX escapes and plain ASCII. Letters outside the escapes are Latin (English).
-- returns hasArabic, hasLatin, the line with Latin words removed
local function scan(s)
    local out, pos, arabic, latin = {}, 1, false, false
    while true do
        local a = string.find(s, BS_U, pos, true)
        if a == nil then break end
        local before = string.sub(s, pos, a - 1)
        if string.find(before, "[A-Za-z]") then latin = true; before = string.gsub(before, "[A-Za-z]+", "") end
        out[#out + 1] = before
        local hex = string.sub(s, a + 2, a + 5)
        if isHex4(hex) then
            local page = string.upper(string.sub(hex, 1, 2))
            if page == "06" or page == "FB" or page == "FE" then arabic = true end
            out[#out + 1] = string.sub(s, a, a + 5)
            pos = a + 6
        else
            latin = true
            pos = a + 2
        end
    end
    local tail = string.sub(s, pos)
    if string.find(tail, "[A-Za-z]") then latin = true; tail = string.gsub(tail, "[A-Za-z]+", "") end
    out[#out + 1] = tail
    return arabic, latin, table.concat(out)
end
S.scan = scan

local function tidy(s)
    s = string.gsub(s, "%s+", " ")
    s = string.gsub(s, "^ ", "")
    s = string.gsub(s, " $", "")
    return s
end

-- Arabic ready for the bubble: no unfilled %1 and no Latin
local function clean(v)
    if type(v) ~= "string" or v == "" then return nil end
    local arabic, latin = scan(v)
    if not arabic or latin or string.find(v, "%%%d") then return nil end
    return v
end

-- the English line's translation: SolDialogueArabic (this table merged into it; it also reports misses)
local function translate(topic, line)
    if type(SolDialogueArabic) == "table" and type(SolDialogueArabic.localize) == "function" then
        local localized = SolDialogueArabic.localize(topic, line)
        local ar = clean(localized)
        if ar then return ar end
    end
    return clean(S.lines[line])
end

-- ---------------------------------------------------------------- topic lines
local function now() return (type(getTimestampMs) == "function" and getTimestampMs()) or 0 end
local URGENT = { danger = true, combat = true, player_hit = true, signal = true, grab = true, bite = true }

function S.poolFor(topic)
    if type(topic) ~= "string" or topic == "" then return nil, nil end
    local key = topic
    while key do
        local p = S.pools[key]
        if p then return p, key end
        key = string.match(key, "^(.*)%.[^%.]+$")
    end
    return S.default, "_default"
end

local lastUsed, counters = {}, {}
local function poolLine(topic)
    local pool, key = S.poolFor(topic)
    if not pool then return nil end
    local t = now()
    local first = string.match(topic, "^[^%.]+") or topic
    local wait = URGENT[first] and S.URGENT_GAP_MS or S.GAP_MS
    local last = lastUsed[key]
    if t > 0 and last ~= nil and t - last < wait then return nil end
    lastUsed[key] = t
    local i = ((counters[key] or 0) % #pool) + 1
    counters[key] = i
    return pool[i]
end

-- ---------------------------------------------------------------- what goes above her head
-- line: already Arabic -> it stays (a stray English word is dropped); English -> its translation, else a short line for this topic, else nil (silence).
function S.resolve(actor, topic, line)
    if type(line) ~= "string" or line == "" then return nil end
    local arabic, latin, stripped = scan(line)
    if arabic then
        if string.find(line, "%%%d") then return nil end
        if not latin then return line end
        local t = tidy(stripped)
        return clean(t)
    end
    local ar = translate(topic, line)
    if ar then return ar end
    if topic == nil then topic = S.topicOf[line] end
    return poolLine(topic)
end

function S.isSol(actor)
    if actor == nil then return false end
    if type(SolUI) == "table" and type(SolUI.solActor) == "function" then
        local sol = SolUI.solActor()
        if sol ~= nil then return sol == actor end
    end
    -- more than one companion alive: by her name
    local SC = SurvivorCompanion
    local g = type(SC) == "table" and SC.GameplayUtil or nil
    if type(g) == "table" and type(g.nameOf) == "function" then
        local name = g.nameOf(actor)
        return name == "Sol" or name == "Sol Survivor"
    end
    return false
end

-- speaks the line above Sol's head through SolBubble; never the game's font. false when she says nothing.
function S.overhead(actor, line, displayMillis)
    local ar = S.resolve(actor, nil, line)
    if not ar then return false end
    if type(SolBubble) ~= "table" or type(SolBubble.speak) ~= "function" then return false end
    local ms = nil
    if type(displayMillis) == "function" then
        local plain = string.gsub(ar, "<BS>u....", "x")   -- \uXXXX counts as one letter
        ms = displayMillis(plain)
    end
    return SolBubble.speak(actor, ar, ms) == true
end

-- ---------------------------------------------------------------- the topic of a line chosen by LF, for callers that say it without one
S.topicOf = {}
local topicCount = 0
local function note(line, topic)
    if type(line) ~= "string" or type(topic) ~= "string" then return end
    if S.topicOf[line] == nil then topicCount = topicCount + 1 end
    S.topicOf[line] = topic
    if topicCount > 512 then S.topicOf, topicCount = {}, 0 end
end

local function hookChoose()
    local SC = SurvivorCompanion
    local D = type(SC) == "table" and SC.Dialogue or nil
    if type(D) ~= "table" or type(D.choose) ~= "function" or S._chooseHooked then return end
    S._chooseHooked = true
    local orig = D.choose
    D.choose = function(actor, topic, specification, arguments, options)
        local line, detail = orig(actor, topic, specification, arguments, options)
        note(line, topic)
        return line, detail
    end
end
hookChoose()
if Events and Events.OnGameStart then Events.OnGameStart.Add(hookChoose) end
"""


CHUNK = 800
META = ("الذكاء", "النظام", "المود", "اللعبة", "برنامج", "نموذج")
LIMIT = 100


def load_translated():
    """speech_tr/*.out.json, checked line by line. Anything that fails stays out and is listed."""
    good, bad = {}, []
    for f in sorted(glob.glob(os.path.join(HERE, "speech_tr", "*.out.json"))):
        for en, ar in json.load(open(f, encoding="utf-8")).items():
            why = None
            if not ar.strip(): why = "blank"
            elif re.search(r"[A-Za-z]", ar): why = "latin"
            elif sorted(re.findall(r"%\d", en)) != sorted(re.findall(r"%\d", ar)): why = "placeholders"
            elif len(ar) > LIMIT: why = "long"
            elif any(m in ar for m in META): why = "meta"
            elif not re.search(r"[\u0600-\u06FF]", ar): why = "no_arabic"
            if why: bad.append((why, en, ar))
            else: good[en] = ar
    return good, bad


def write_chunks(lines):
    for old in glob.glob(os.path.join(HERE, "SolSpeechAR_L*.lua")): os.remove(old)
    items = sorted(lines.items())
    names = []
    for i in range(0, len(items), CHUNK):
        name = "SolSpeechAR_L%02d" % (len(names) + 1)
        out = ["-- %s - GENERATED by gen_speech_ar.py: do not edit by hand." % name, "SolSpeechARLines = SolSpeechARLines or {}", "local t = SolSpeechARLines"]
        for en, ar in items[i:i + CHUNK]: out.append("t[%s] = \"%s\"" % (lua_key(en), esc(ar)))
        src = "\n".join(out) + "\n"
        src.encode("ascii")
        open(os.path.join(HERE, name + ".lua"), "w", encoding="ascii", newline="\n").write(src)
        names.append(name)
    return names


def main():
    lines = parse_lines()
    translated, rejected = load_translated()
    for en in lines: translated.pop(en, None)                                    # the hand-written ones stay
    chunks = write_chunks(translated)
    open(os.path.join(HERE, "speech_rejected.txt"), "w", encoding="utf-8").write("".join("%s ||| %s ||| %s\n" % r for r in rejected))
    print("translated", len(translated), "rejected", len(rejected), "chunks", len(chunks))
    out = []
    out.append("-- SolSpeechAR.lua - everything Sol says above her head is Arabic, or she says nothing. GENERATED by gen_speech_ar.py: do not edit by hand.")
    out.append("-- ASCII-only source: Arabic is stored as " + BS + BS + "uXXXX escapes, which SolText decodes.")
    out.append("-- lines: English line (or %1 template) -> Arabic. pools: dialogue topic -> short Arabic lines when a line has no translation of its own.")
    out.append('require "SolDialogueLines"')
    out.append('require "SolDialogueArabic"')
    for name in chunks: out.append('require "%s"' % name)
    out.append("SolSpeechAR = SolSpeechAR or {}")
    out.append("local S = SolSpeechAR")
    out.append('S.VERSION = "0.1.0"')
    out.append("S.GAP_MS, S.URGENT_GAP_MS = 25000, 6000")
    out.append("S.lines = {")
    for en, ar in sorted(lines.items()):
        out.append("    [%s] = \"%s\"," % (lua_key(en), esc(ar)))
    out.append("}")
    out.append("for en, ar in pairs(SolSpeechARLines or {}) do if S.lines[en] == nil then S.lines[en] = ar end end")
    out.append("S.pools = {")
    for key, vals in sorted(POOLS.items()):
        out.append("    [%s] = { %s }," % (lua_key(key), ", ".join('"%s"' % esc(v) for v in vals)))
    out.append("}")
    out.append("S.default = { %s }" % ", ".join('"%s"' % esc(v) for v in DEFAULT))
    code = CODE.replace("<BS>", BS + BS)
    src = "\n".join(out) + "\n" + code
    src += 'print("[SolSpeechAR] ready v" .. S.VERSION)\n'
    path = os.path.join(HERE, "SolSpeechAR.lua")
    src.encode("ascii")
    open(path, "w", encoding="ascii", newline="\n").write(src)
    print("wrote", path, len(src), "bytes;", len(lines), "lines;", len(POOLS), "pools")


if __name__ == "__main__":
    main()
