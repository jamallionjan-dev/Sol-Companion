-- SolDialogueLines.lua - v0.1.2
-- Arabic for the lines Living Fellows speaks: the English line (exactly as the game builds it) -> Sol's Arabic, in the
-- same Levantine voice as SolDialogueArabic. ASCII-only source: Arabic is stored as \\uXXXX, which SolText decodes.
-- SolDialogueArabic.localize() reads this table (merge) and reports every line it could not translate (miss), so the
-- next batch is built from what the player really heard. %1 %2 are the game's own placeholders and are filled in.
-- Also: the display name ("Sol Survivor" -> Sol in Arabic) for the Sol window, and the state words LF has no key for.
require "SolLF_AR"
SolDialogueLines = SolDialogueLines or {}
local D = SolDialogueLines
D.VERSION = "0.1.2"
D.NAME_AR = "\\u0633\\u0648\\u0644"
D.lines = {
    ["I am not all right yet. %1 is gone, and I need time."] = "\\u0644\\u0633\\u0627 \\u0645\\u0648 \\u0645\\u0646\\u064A\\u062D\\u0629. %1 \\u0631\\u0627\\u062D\\u060C \\u0648\\u0623\\u0646\\u0627 \\u0628\\u062F\\u064A \\u0648\\u0642\\u062A.",
    ["I am managing, but I keep thinking about %1."] = "\\u0639\\u0645 \\u062F\\u0628\\u0631 \\u062D\\u0627\\u0644\\u064A\\u060C \\u0628\\u0633 \\u0645\\u0627 \\u0628\\u0637\\u0644\\u062A \\u0641\\u0643\\u0631 \\u0628\\u0640%1.",
    ["Some moments are easier than others. I still miss %1."] = "\\u0641\\u064A \\u0644\\u062D\\u0638\\u0627\\u062A \\u0623\\u0633\\u0647\\u0644 \\u0645\\u0646 \\u063A\\u064A\\u0631\\u0647\\u0627. \\u0644\\u0633\\u0627 \\u0645\\u0634\\u062A\\u0627\\u0642\\u0629 \\u0644\\u0640%1.",
    ["I can do my job. I just haven't made peace with losing %1."] = "\\u0641\\u064A\\u0646\\u064A \\u0623\\u0634\\u062A\\u063A\\u0644 \\u0634\\u063A\\u0644\\u064A. \\u0628\\u0633 \\u0645\\u0627 \\u062A\\u0635\\u0627\\u0644\\u062D\\u062A \\u0645\\u0639 \\u062E\\u0633\\u0627\\u0631\\u0629 %1.",
    ["Honestly? I am still grieving %1."] = "\\u0628\\u0635\\u0631\\u0627\\u062D\\u0629\\u061F \\u0644\\u0633\\u0627 \\u062D\\u0632\\u064A\\u0646\\u0629 \\u0639\\u0644\\u0649 %1.",
    ["I keep expecting %1 to answer when someone calls out."] = "\\u0636\\u0644\\u0646\\u064A \\u0645\\u062A\\u0648\\u0642\\u0639\\u0629 \\u0625\\u0646\\u0648 %1 \\u064A\\u0631\\u062F \\u0644\\u0645\\u0627 \\u062D\\u062F\\u0627 \\u064A\\u0646\\u0627\\u062F\\u064A.",
    ["I need you to know something is wrong. It feels like Knox symptoms."] = "\\u0644\\u0627\\u0632\\u0645 \\u062A\\u0639\\u0631\\u0641 \\u0625\\u0646\\u0648 \\u0641\\u064A \\u0634\\u064A \\u063A\\u0644\\u0637. \\u062D\\u0627\\u0633\\u0629 \\u0628\\u0623\\u0639\\u0631\\u0627\\u0636 \\u0646\\u0648\\u0643\\u0633.",
    ["Something is wrong with me. It could be the Knox infection."] = "\\u0641\\u064A \\u0634\\u064A \\u0645\\u0648 \\u0637\\u0628\\u064A\\u0639\\u064A \\u0641\\u064A. \\u064A\\u0645\\u0643\\u0646 \\u062A\\u0643\\u0648\\u0646 \\u0639\\u062F\\u0648\\u0649 \\u0646\\u0648\\u0643\\u0633.",
    ["I am showing symptoms, and I don't think this is ordinary sickness."] = "\\u0638\\u0647\\u0631\\u062A \\u0639\\u0646\\u062F\\u064A \\u0623\\u0639\\u0631\\u0627\\u0636\\u060C \\u0648\\u0645\\u0648 \\u0634\\u0627\\u064A\\u0641\\u062A\\u0647\\u0627 \\u0645\\u0631\\u0636 \\u0639\\u0627\\u062F\\u064A.",
    ["We need to talk somewhere private. I may be infected."] = "\\u0644\\u0627\\u0632\\u0645 \\u0646\\u062D\\u0643\\u064A \\u0628\\u0645\\u0643\\u0627\\u0646 \\u0644\\u062D\\u0627\\u0644\\u0646\\u0627. \\u064A\\u0645\\u0643\\u0646 \\u0623\\u0643\\u0648\\u0646 \\u0645\\u0635\\u0627\\u0628\\u0629.",
    ["I need treatment and a clean bandage."] = "\\u0628\\u062F\\u064A \\u0639\\u0644\\u0627\\u062C \\u0648\\u0636\\u0645\\u0627\\u062F \\u0646\\u0636\\u064A\\u0641.",
    ["I am hurt. I need someone to look at this."] = "\\u0623\\u0646\\u0627 \\u0645\\u062C\\u0631\\u0648\\u062D\\u0629. \\u0628\\u062F\\u064A \\u062D\\u062F\\u0627 \\u064A\\u0634\\u0648\\u0641 \\u0647\\u0627\\u0644\\u0625\\u0635\\u0627\\u0628\\u0629.",
    ["My wounds need attention before they get worse."] = "\\u062C\\u0631\\u0648\\u062D\\u064A \\u0628\\u062F\\u0647\\u0627 \\u0639\\u0646\\u0627\\u064A\\u0629 \\u0642\\u0628\\u0644 \\u0645\\u0627 \\u062A\\u0633\\u0648\\u0621.",
    ["I could use medical help and fresh bandages."] = "\\u0628\\u062D\\u0627\\u062C\\u0629 \\u0644\\u0645\\u0633\\u0627\\u0639\\u062F\\u0629 \\u0637\\u0628\\u064A\\u0629 \\u0648\\u0636\\u0645\\u0627\\u062F\\u0627\\u062A \\u062C\\u062F\\u064A\\u062F\\u0629.",
    ["I am still functional, but I need treatment."] = "\\u0644\\u0633\\u0627 \\u0642\\u0627\\u062F\\u0631\\u0629 \\u0623\\u0634\\u062A\\u063A\\u0644\\u060C \\u0628\\u0633 \\u0628\\u062F\\u064A \\u0639\\u0644\\u0627\\u062C.",
    ["I can keep moving, but patch me up when we get a chance."] = "\\u0641\\u064A\\u0646\\u064A \\u0643\\u0645\\u0644\\u060C \\u0628\\u0633 \\u0636\\u0645\\u062F\\u0646\\u064A \\u0623\\u0648\\u0644 \\u0641\\u0631\\u0635\\u0629.",
    ["This wound is a liability. We should treat it now."] = "\\u0647\\u0627\\u0644\\u062C\\u0631\\u062D \\u0639\\u0628\\u0621 \\u0639\\u0644\\u064A\\u0646\\u0627. \\u0644\\u0627\\u0632\\u0645 \\u0646\\u0639\\u0627\\u0644\\u062C\\u0647 \\u0647\\u0644\\u0623.",
    ["Water, if we can spare it. I am getting very thirsty."] = "\\u0645\\u064A\\u060C \\u0625\\u0630\\u0627 \\u0641\\u064A\\u0646\\u0627 \\u0646\\u0648\\u0641\\u0631\\u0647\\u0627. \\u0639\\u0637\\u0634\\u0627\\u0646\\u0629 \\u0643\\u062A\\u064A\\u0631.",
    ["I need a drink soon."] = "\\u0628\\u062F\\u064A \\u0623\\u0634\\u0631\\u0628 \\u0642\\u0631\\u064A\\u0628.",
    ["My canteen is empty and I am running dry."] = "\\u0642\\u0646\\u064A\\u0646\\u062A\\u064A \\u0641\\u0627\\u0636\\u064A\\u0629 \\u0648\\u0639\\u0645 \\u0623\\u0646\\u0634\\u0641.",
    ["Water is my first priority right now."] = "\\u0627\\u0644\\u0645\\u064A \\u0623\\u0648\\u0644\\u0648\\u064A\\u062A\\u064A \\u0627\\u0644\\u0623\\u0648\\u0644\\u0649 \\u0647\\u0644\\u0623.",
    ["I can keep going, but not long without water."] = "\\u0641\\u064A\\u0646\\u064A \\u0643\\u0645\\u0644\\u060C \\u0628\\u0633 \\u0645\\u0648 \\u0643\\u062A\\u064A\\u0631 \\u0645\\u0646 \\u063A\\u064A\\u0631 \\u0645\\u064A.",
    ["Food would help. I am running on empty."] = "\\u0627\\u0644\\u0623\\u0643\\u0644 \\u0628\\u064A\\u0633\\u0627\\u0639\\u062F. \\u0623\\u0646\\u0627 \\u0634\\u0628\\u0647 \\u0641\\u0627\\u0636\\u064A\\u0629.",
    ["I need something to eat soon."] = "\\u0628\\u062F\\u064A \\u0634\\u064A \\u0622\\u0643\\u0644\\u0647 \\u0642\\u0631\\u064A\\u0628.",
    ["I have not eaten enough. It is starting to slow me down."] = "\\u0645\\u0627 \\u0623\\u0643\\u0644\\u062A \\u0643\\u0641\\u0627\\u064A\\u0629. \\u0635\\u0631\\u062A \\u0623\\u0628\\u0637\\u0623.",
    ["My first need is food."] = "\\u0623\\u0648\\u0644 \\u062D\\u0627\\u062C\\u062A\\u064A \\u0623\\u0643\\u0644.",
    ["I am hungry enough that it is getting hard to focus."] = "\\u062C\\u0639\\u0627\\u0646\\u0629 \\u0644\\u062F\\u0631\\u062C\\u0629 \\u0635\\u0627\\u0631 \\u0635\\u0639\\u0628 \\u0623\\u0631\\u0643\\u0632.",
    ["I need a quiet minute somewhere safe."] = "\\u0628\\u062F\\u064A \\u062F\\u0642\\u064A\\u0642\\u0629 \\u0647\\u062F\\u0648\\u0621 \\u0628\\u0645\\u0643\\u0627\\u0646 \\u0622\\u0645\\u0646.",
    ["I am too wound up. I need somewhere secure to breathe."] = "\\u0623\\u0639\\u0635\\u0627\\u0628\\u064A \\u0645\\u0634\\u062F\\u0648\\u062F\\u0629 \\u0643\\u062A\\u064A\\u0631. \\u0628\\u062F\\u064A \\u0645\\u0643\\u0627\\u0646 \\u0622\\u0645\\u0646 \\u0623\\u062A\\u0646\\u0641\\u0633 \\u0641\\u064A\\u0647.",
    ["Get me behind a locked door for a minute and I will be fine."] = "\\u062E\\u0644\\u064A\\u0646\\u064A \\u0648\\u0631\\u0627 \\u0628\\u0627\\u0628 \\u0645\\u0642\\u0641\\u0644 \\u062F\\u0642\\u064A\\u0642\\u0629 \\u0648\\u0628\\u0635\\u064A\\u0631 \\u062A\\u0645\\u0627\\u0645.",
    ["I need the pressure to stop for a moment."] = "\\u0628\\u062F\\u064A \\u0627\\u0644\\u0636\\u063A\\u0637 \\u064A\\u0648\\u0642\\u0641 \\u0644\\u062D\\u0638\\u0629.",
    ["Somewhere safe and quiet. That is what I need."] = "\\u0645\\u0643\\u0627\\u0646 \\u0622\\u0645\\u0646 \\u0648\\u0647\\u0627\\u062F\\u064A. \\u0647\\u0627\\u062F \\u0627\\u0644\\u0644\\u064A \\u0628\\u062F\\u064A \\u0625\\u064A\\u0627\\u0647.",
    ["We should find clean bandages before someone needs one."] = "\\u0644\\u0627\\u0632\\u0645 \\u0646\\u062F\\u0628\\u0631 \\u0636\\u0645\\u0627\\u062F\\u0627\\u062A \\u0646\\u0636\\u064A\\u0641\\u0629 \\u0642\\u0628\\u0644 \\u0645\\u0627 \\u062D\\u062F\\u0627 \\u064A\\u062D\\u062A\\u0627\\u062C\\u0647\\u0627.",
    ["Our medical supplies are too low."] = "\\u0645\\u062E\\u0632\\u0648\\u0646\\u0646\\u0627 \\u0627\\u0644\\u0637\\u0628\\u064A \\u0642\\u0644\\u064A\\u0644 \\u0643\\u062A\\u064A\\u0631.",
    ["We need more clean bandages in reserve."] = "\\u0628\\u062F\\u0646\\u0627 \\u0636\\u0645\\u0627\\u062F\\u0627\\u062A \\u0646\\u0636\\u064A\\u0641\\u0629 \\u0623\\u0643\\u062A\\u0631 \\u0628\\u0627\\u0644\\u0627\\u062D\\u062A\\u064A\\u0627\\u0637.",
    ["First-aid stock is thin. We should fix that."] = "\\u0645\\u062E\\u0632\\u0648\\u0646 \\u0627\\u0644\\u0625\\u0633\\u0639\\u0627\\u0641 \\u0634\\u062D\\u064A\\u062D. \\u0644\\u0627\\u0632\\u0645 \\u0646\\u0635\\u0644\\u062D \\u0647\\u0627\\u0644\\u0634\\u064A.",
    ["Nobody is bleeding yet, but we are out of clean bandages."] = "\\u0645\\u0627 \\u062D\\u062F\\u0627 \\u0639\\u0645 \\u064A\\u0646\\u0632\\u0641 \\u0644\\u0633\\u0627\\u060C \\u0628\\u0633 \\u062E\\u0644\\u0635\\u062A \\u0627\\u0644\\u0636\\u0645\\u0627\\u062F\\u0627\\u062A \\u0627\\u0644\\u0646\\u0636\\u064A\\u0641\\u0629.",
    ["I am short on ammunition. I will save what I have."] = "\\u0630\\u062E\\u064A\\u0631\\u062A\\u064A \\u0642\\u0644\\u064A\\u0644\\u0629. \\u0631\\u062D \\u0648\\u0641\\u0631 \\u0627\\u0644\\u0644\\u064A \\u0645\\u0639\\u064A.",
    ["My ammunition is nearly gone."] = "\\u0630\\u062E\\u064A\\u0631\\u062A\\u064A \\u0643\\u0627\\u062F\\u062A \\u062A\\u062E\\u0644\\u0635.",
    ["I need more rounds before the next serious fight."] = "\\u0628\\u062F\\u064A \\u0637\\u0644\\u0642\\u0627\\u062A \\u0623\\u0643\\u062A\\u0631 \\u0642\\u0628\\u0644 \\u0627\\u0644\\u0645\\u0639\\u0631\\u0643\\u0629 \\u0627\\u0644\\u062C\\u062F\\u064A\\u0629 \\u0627\\u0644\\u062C\\u0627\\u064A\\u0629.",
    ["I am conserving ammunition until we restock."] = "\\u0639\\u0645 \\u0648\\u0641\\u0631 \\u0627\\u0644\\u0630\\u062E\\u064A\\u0631\\u0629 \\u0644\\u062D\\u062F \\u0645\\u0627 \\u0646\\u0639\\u0628\\u064A.",
    ["This firearm will not help much without more ammunition."] = "\\u0647\\u0627\\u0644\\u0633\\u0644\\u0627\\u062D \\u0645\\u0627 \\u0631\\u062D \\u064A\\u0641\\u064A\\u062F \\u0643\\u062A\\u064A\\u0631 \\u0628\\u062F\\u0648\\u0646 \\u0630\\u062E\\u064A\\u0631\\u0629 \\u0623\\u0643\\u062A\\u0631.",
    ["I am all right for now. Ready when you are."] = "\\u0623\\u0646\\u0627 \\u062A\\u0645\\u0627\\u0645 \\u0647\\u0644\\u0623. \\u062C\\u0627\\u0647\\u0632\\u0629 \\u0648\\u0642\\u062A \\u0645\\u0627 \\u0628\\u062F\\u0643.",
    ["Doing fine. Tell me what comes next."] = "\\u062A\\u0645\\u0627\\u0645. \\u0642\\u0644\\u064A \\u0634\\u0648 \\u0627\\u0644\\u062E\\u0637\\u0648\\u0629 \\u0627\\u0644\\u062C\\u0627\\u064A\\u0629.",
    ["No urgent problems. I am ready to move."] = "\\u0645\\u0627 \\u0641\\u064A \\u0645\\u0634\\u0627\\u0643\\u0644 \\u0645\\u0644\\u062D\\u0629. \\u062C\\u0627\\u0647\\u0632\\u0629 \\u0646\\u062A\\u062D\\u0631\\u0643.",
    ["I have what I need for now."] = "\\u0645\\u0639\\u064A \\u0627\\u0644\\u0644\\u064A \\u0628\\u062D\\u062A\\u0627\\u062C\\u0647 \\u0647\\u0644\\u0623.",
    ["I am holding up. Point me where you need me."] = "\\u0635\\u0627\\u0645\\u062F\\u0629. \\u062F\\u0644\\u0646\\u064A \\u0648\\u064A\\u0646 \\u0628\\u062F\\u0643 \\u0625\\u064A\\u0627\\u0646\\u064A.",
    ["Ready. Let's not waste the daylight."] = "\\u062C\\u0627\\u0647\\u0632\\u0629. \\u0645\\u0627 \\u0646\\u0636\\u064A\\u0639 \\u0627\\u0644\\u0636\\u0648.",
    ["I am holding up. I am still watching our exits."] = "\\u0635\\u0627\\u0645\\u062F\\u0629. \\u0648\\u0639\\u064A\\u0646\\u064A \\u0639 \\u0645\\u062E\\u0627\\u0631\\u062C\\u0646\\u0627.",
    ["Fine for now. I would like to keep it that way."] = "\\u062A\\u0645\\u0627\\u0645 \\u0647\\u0644\\u0623. \\u0628\\u062A\\u0645\\u0646\\u0649 \\u064A\\u0636\\u0644 \\u0647\\u064A\\u0643.",
    ["I am all right. How are you holding up?"] = "\\u0623\\u0646\\u0627 \\u062A\\u0645\\u0627\\u0645. \\u0625\\u0646\\u062A \\u0643\\u064A\\u0641\\u0643\\u061F",
    ["I am okay. Let me know if anyone else needs help."] = "\\u0623\\u0646\\u0627 \\u0645\\u0646\\u064A\\u062D\\u0629. \\u062E\\u0628\\u0631\\u0646\\u064A \\u0625\\u0630\\u0627 \\u062D\\u062F\\u0627 \\u062A\\u0627\\u0646\\u064A \\u0628\\u062F\\u0648 \\u0645\\u0633\\u0627\\u0639\\u062F\\u0629.",
    ["I am holding up. Our supplies and gear are in order for now."] = "\\u0635\\u0627\\u0645\\u062F\\u0629. \\u0645\\u0624\\u0646\\u0646\\u0627 \\u0648\\u0639\\u062A\\u0627\\u062F\\u0646\\u0627 \\u0645\\u0631\\u062A\\u0628\\u064A\\u0646 \\u0647\\u0644\\u0623.",
    ["Everything important is accounted for. I am ready."] = "\\u0643\\u0644 \\u0634\\u064A \\u0645\\u0647\\u0645 \\u0645\\u062D\\u0633\\u0648\\u0628. \\u062C\\u0627\\u0647\\u0632\\u0629.",
    ["Better than yesterday. I will take that."] = "\\u0623\\u062D\\u0633\\u0646 \\u0645\\u0646 \\u0645\\u0628\\u0627\\u0631\\u062D. \\u0628\\u0643\\u0641\\u064A.",
    ["Honestly? I feel pretty good today."] = "\\u0628\\u0635\\u0631\\u0627\\u062D\\u0629\\u061F \\u062D\\u0627\\u0633\\u0629 \\u062D\\u0627\\u0644\\u064A \\u0645\\u0646\\u064A\\u062D\\u0629 \\u0627\\u0644\\u064A\\u0648\\u0645.",
    ["Physically I am okay. I am still trying to settle my nerves."] = "\\u062C\\u0633\\u062F\\u064A\\u0627 \\u062A\\u0645\\u0627\\u0645. \\u0644\\u0633\\u0627 \\u0639\\u0645 \\u062D\\u0627\\u0648\\u0644 \\u0623\\u0647\\u062F\\u064A \\u0623\\u0639\\u0635\\u0627\\u0628\\u064A.",
    ["Nothing is broken. My hands just need to stop shaking."] = "\\u0645\\u0627 \\u0641\\u064A \\u0634\\u064A \\u0645\\u0643\\u0633\\u0648\\u0631. \\u0628\\u0633 \\u0625\\u064A\\u062F\\u064A\\u064A \\u0644\\u0627\\u0632\\u0645 \\u062A\\u0628\\u0637\\u0644 \\u062A\\u0631\\u062C\\u0641.",
    ["I am alive. Give me a little time to come down from that."] = "\\u0623\\u0646\\u0627 \\u0639\\u0627\\u064A\\u0634\\u0629. \\u0639\\u0637\\u064A\\u0646\\u064A \\u0634\\u0648\\u064A \\u0648\\u0642\\u062A \\u0644\\u0623\\u0647\\u062F\\u0627.",
    ["I can keep going, but I am not calm yet."] = "\\u0641\\u064A\\u0646\\u064A \\u0643\\u0645\\u0644\\u060C \\u0628\\u0633 \\u0644\\u0633\\u0627 \\u0645\\u0648 \\u0647\\u0627\\u062F\\u064A\\u0629.",
    ["Ask me again when my heart stops trying to climb out of my chest."] = "\\u0627\\u0633\\u0623\\u0644\\u0646\\u064A \\u0645\\u0631\\u0629 \\u062A\\u0627\\u0646\\u064A\\u0629 \\u0644\\u0645\\u0627 \\u0642\\u0644\\u0628\\u064A \\u064A\\u0628\\u0637\\u0644 \\u064A\\u0637\\u0644\\u0639 \\u0645\\u0646 \\u0635\\u062F\\u0631\\u064A.",
    ["I'm starting to get hungry."] = "\\u0628\\u0644\\u0634\\u062A \\u0623\\u062C\\u0648\\u0639.",
    ["I could eat when we get a safe minute."] = "\\u0641\\u064A\\u0646\\u064A \\u0622\\u0643\\u0644 \\u0644\\u0645\\u0627 \\u064A\\u0635\\u064A\\u0631 \\u0639\\u0646\\u0627 \\u062F\\u0642\\u064A\\u0642\\u0629 \\u0622\\u0645\\u0646\\u0629.",
    ["My stomach is reminding me it exists."] = "\\u0645\\u0639\\u062F\\u062A\\u064A \\u0639\\u0645 \\u062A\\u0630\\u0643\\u0631\\u0646\\u064A \\u0625\\u0646\\u0647\\u0627 \\u0645\\u0648\\u062C\\u0648\\u062F\\u0629.",
    ["Food should be on the next short list."] = "\\u0627\\u0644\\u0623\\u0643\\u0644 \\u0644\\u0627\\u0632\\u0645 \\u064A\\u0643\\u0648\\u0646 \\u0639\\u0627\\u0644\\u0642\\u0627\\u0626\\u0645\\u0629 \\u0627\\u0644\\u062C\\u0627\\u064A\\u0629.",
    ["I haven't eaten in a while."] = "\\u0645\\u0646 \\u0641\\u062A\\u0631\\u0629 \\u0645\\u0627 \\u0623\\u0643\\u0644\\u062A.",
    ["Not urgent yet, but I am getting hungry."] = "\\u0645\\u0648 \\u0645\\u0644\\u062D \\u0644\\u0633\\u0627\\u060C \\u0628\\u0633 \\u0639\\u0645 \\u0623\\u062C\\u0648\\u0639.",
    ["I can keep moving. Just remember food when we stop."] = "\\u0641\\u064A\\u0646\\u064A \\u0643\\u0645\\u0644. \\u0628\\u0633 \\u062A\\u0630\\u0643\\u0631 \\u0627\\u0644\\u0623\\u0643\\u0644 \\u0644\\u0645\\u0627 \\u0646\\u0648\\u0642\\u0641.",
    ["Hunger can wait a little. Not forever."] = "\\u0627\\u0644\\u062C\\u0648\\u0639 \\u0628\\u064A\\u062A\\u062D\\u0645\\u0644 \\u0634\\u0648\\u064A. \\u0645\\u0648 \\u0644\\u0644\\u0623\\u0628\\u062F.",
    ["I am getting hungry. We should not let that become weakness."] = "\\u0639\\u0645 \\u0623\\u062C\\u0648\\u0639. \\u0645\\u0627 \\u0644\\u0627\\u0632\\u0645 \\u0646\\u062E\\u0644\\u064A\\u0647 \\u064A\\u0635\\u064A\\u0631 \\u0636\\u0639\\u0641.",
    ["Food soon, before it starts costing us attention."] = "\\u0623\\u0643\\u0644 \\u0642\\u0631\\u064A\\u0628\\u060C \\u0642\\u0628\\u0644 \\u0645\\u0627 \\u064A\\u0643\\u0644\\u0641\\u0646\\u0627 \\u062A\\u0631\\u0643\\u064A\\u0632\\u0646\\u0627.",
    ["I'm getting hungry. Check whether anyone else is too."] = "\\u0639\\u0645 \\u0623\\u062C\\u0648\\u0639. \\u0634\\u0648\\u0641 \\u0625\\u0630\\u0627 \\u062D\\u062F\\u0627 \\u062A\\u0627\\u0646\\u064A \\u062C\\u0648\\u0639\\u0627\\u0646 \\u0643\\u0645\\u0627\\u0646.",
    ["Food soon would be good, if there is enough for everyone."] = "\\u0645\\u0646\\u064A\\u062D \\u0644\\u0648 \\u0646\\u0627\\u0643\\u0644 \\u0642\\u0631\\u064A\\u0628\\u060C \\u0625\\u0630\\u0627 \\u0641\\u064A \\u0643\\u0641\\u0627\\u064A\\u0629 \\u0644\\u0644\\u0643\\u0644.",
    ["Hunger is becoming noticeable."] = "\\u0627\\u0644\\u062C\\u0648\\u0639 \\u0635\\u0627\\u0631 \\u0645\\u0644\\u062D\\u0648\\u0638.",
    ["Food need is rising, but not critical yet."] = "\\u0627\\u0644\\u062D\\u0627\\u062C\\u0629 \\u0644\\u0644\\u0623\\u0643\\u0644 \\u0639\\u0645 \\u062A\\u0632\\u064A\\u062F\\u060C \\u0628\\u0633 \\u0645\\u0648 \\u062D\\u0631\\u062C\\u0629 \\u0644\\u0633\\u0627.",
    ["I need food soon."] = "\\u0628\\u062F\\u064A \\u0623\\u0643\\u0644 \\u0642\\u0631\\u064A\\u0628.",
    ["Hunger is making it hard to concentrate."] = "\\u0627\\u0644\\u062C\\u0648\\u0639 \\u0639\\u0645 \\u064A\\u0635\\u0639\\u0628 \\u0627\\u0644\\u062A\\u0631\\u0643\\u064A\\u0632.",
    ["We need to find something I can eat."] = "\\u0644\\u0627\\u0632\\u0645 \\u0646\\u0644\\u0627\\u0642\\u064A \\u0634\\u064A \\u0622\\u0643\\u0644\\u0647.",
    ["I'm running low. Really low."] = "\\u0637\\u0627\\u0642\\u062A\\u064A \\u0642\\u0644\\u064A\\u0644\\u0629. \\u0642\\u0644\\u064A\\u0644\\u0629 \\u0643\\u062A\\u064A\\u0631.",
    ["I cannot keep putting off a meal."] = "\\u0645\\u0627 \\u0641\\u064A\\u0646\\u064A \\u0623\\u0623\\u062C\\u0644 \\u0627\\u0644\\u0648\\u062C\\u0628\\u0629 \\u0623\\u0643\\u062A\\u0631.",
    ["Food needs to become a priority."] = "\\u0627\\u0644\\u0623\\u0643\\u0644 \\u0644\\u0627\\u0632\\u0645 \\u064A\\u0635\\u064A\\u0631 \\u0623\\u0648\\u0644\\u0648\\u064A\\u0629.",
    ["I can fight hungry, but not well. Find me food."] = "\\u0641\\u064A\\u0646\\u064A \\u0642\\u0627\\u062A\\u0644 \\u062C\\u0648\\u0639\\u0627\\u0646\\u0629\\u060C \\u0628\\u0633 \\u0645\\u0648 \\u0645\\u0646\\u064A\\u062D. \\u062F\\u0628\\u0631\\u0644\\u064A \\u0623\\u0643\\u0644.",
    ["This is past an empty stomach. I need a meal."] = "\\u0647\\u0627\\u062F \\u0623\\u0643\\u062A\\u0631 \\u0645\\u0646 \\u0645\\u0639\\u062F\\u0629 \\u0641\\u0627\\u0636\\u064A\\u0629. \\u0628\\u062F\\u064A \\u0648\\u062C\\u0628\\u0629.",
    ["My attention is slipping. I need food before we take another risk."] = "\\u062A\\u0631\\u0643\\u064A\\u0632\\u064A \\u0639\\u0645 \\u064A\\u0636\\u0639\\u0641. \\u0628\\u062F\\u064A \\u0623\\u0643\\u0644 \\u0642\\u0628\\u0644 \\u0645\\u0627 \\u0646\\u062E\\u0627\\u0637\\u0631 \\u062A\\u0627\\u0646\\u064A.",
    ["We should stop and eat before I make a bad mistake."] = "\\u0644\\u0627\\u0632\\u0645 \\u0646\\u0648\\u0642\\u0641 \\u0648\\u0646\\u0623\\u0643\\u0644 \\u0642\\u0628\\u0644 \\u0645\\u0627 \\u0623\\u063A\\u0644\\u0637 \\u063A\\u0644\\u0637\\u0629 \\u0633\\u064A\\u0626\\u0629.",
    ["I need food. I don't want anyone giving up their last meal for me."] = "\\u0628\\u062F\\u064A \\u0623\\u0643\\u0644. \\u0645\\u0627 \\u0628\\u062F\\u064A \\u062D\\u062F\\u0627 \\u064A\\u062A\\u062E\\u0644\\u0649 \\u0639\\u0646 \\u0622\\u062E\\u0631 \\u0648\\u062C\\u0628\\u062A\\u0647 \\u0625\\u0644\\u064A.",
    ["Please tell me we have enough for a meal."] = "\\u0631\\u062C\\u0627\\u0621 \\u0642\\u0644\\u064A \\u0625\\u0646\\u0648 \\u0639\\u0646\\u0627 \\u0648\\u062C\\u0628\\u0629 \\u062A\\u0643\\u0641\\u064A.",
    ["Hunger is impairing me. Food is now a priority."] = "\\u0627\\u0644\\u062C\\u0648\\u0639 \\u0639\\u0645 \\u064A\\u0623\\u062B\\u0631 \\u0639\\u0644\\u064A. \\u0627\\u0644\\u0623\\u0643\\u0644 \\u0635\\u0627\\u0631 \\u0623\\u0648\\u0644\\u0648\\u064A\\u0629.",
    ["I need calories before the next demanding job."] = "\\u0628\\u062F\\u064A \\u0633\\u0639\\u0631\\u0627\\u062A \\u0642\\u0628\\u0644 \\u0627\\u0644\\u0634\\u063A\\u0644\\u0629 \\u0627\\u0644\\u0635\\u0639\\u0628\\u0629 \\u0627\\u0644\\u062C\\u0627\\u064A\\u0629.",
    ["I can't think past how hungry I am."] = "\\u0645\\u0627 \\u0639\\u0645 \\u0642\\u062F\\u0631 \\u0623\\u0641\\u0643\\u0631 \\u0628\\u063A\\u064A\\u0631 \\u062C\\u0648\\u0639\\u064A.",
    ["Please. I need something to eat."] = "\\u0631\\u062C\\u0627\\u0621. \\u0628\\u062F\\u064A \\u0634\\u064A \\u0622\\u0643\\u0644\\u0647.",
    ["I need food now."] = "\\u0628\\u062F\\u064A \\u0623\\u0643\\u0644 \\u0647\\u0644\\u0623.",
    ["I'm starving. I cannot keep going like this."] = "\\u0639\\u0645 \\u0645\\u0648\\u062A \\u0645\\u0646 \\u0627\\u0644\\u062C\\u0648\\u0639. \\u0645\\u0627 \\u0641\\u064A\\u0646\\u064A \\u0643\\u0645\\u0644 \\u0647\\u064A\\u0643.",
    ["Find me something edible before I drop."] = "\\u062F\\u0628\\u0631\\u0644\\u064A \\u0634\\u064A \\u0628\\u064A\\u062A\\u0627\\u0643\\u0644 \\u0642\\u0628\\u0644 \\u0645\\u0627 \\u0623\\u0642\\u0639.",
    ["This is bad. I need to eat."] = "\\u0627\\u0644\\u0648\\u0636\\u0639 \\u0633\\u064A\\u0626. \\u0644\\u0627\\u0632\\u0645 \\u0622\\u0643\\u0644.",
    ["I have nothing left to run on."] = "\\u0645\\u0627 \\u0636\\u0644 \\u0639\\u0646\\u062F\\u064A \\u0634\\u064A \\u0623\\u0645\\u0634\\u064A \\u0639\\u0644\\u064A\\u0647.",
    ["Food. Now, please."] = "\\u0623\\u0643\\u0644. \\u0647\\u0644\\u0623\\u060C \\u0631\\u062C\\u0627\\u0621.",
    ["I am still on my feet, but I need food now."] = "\\u0644\\u0633\\u0627 \\u0648\\u0627\\u0642\\u0641\\u0629\\u060C \\u0628\\u0633 \\u0628\\u062F\\u064A \\u0623\\u0643\\u0644 \\u0647\\u0644\\u0623.",
    ["No heroics until I eat. I mean it."] = "\\u0644\\u0627 \\u0628\\u0637\\u0648\\u0644\\u0627\\u062A \\u0642\\u0628\\u0644 \\u0645\\u0627 \\u0622\\u0643\\u0644. \\u062C\\u062F\\u064A\\u0629.",
    ["Stop. I am too hungry to be safe out here."] = "\\u0648\\u0642\\u0641. \\u062C\\u0648\\u0639\\u0627\\u0646\\u0629 \\u0643\\u062A\\u064A\\u0631 \\u0648\\u0645\\u0648 \\u0622\\u0645\\u0646\\u0629 \\u0628\\u0631\\u0627.",
    ["I need food before we move into any more danger."] = "\\u0628\\u062F\\u064A \\u0623\\u0643\\u0644 \\u0642\\u0628\\u0644 \\u0645\\u0627 \\u0646\\u062F\\u062E\\u0644 \\u0628\\u0623\\u064A \\u062E\\u0637\\u0631 \\u062A\\u0627\\u0646\\u064A.",
    ["I hate asking, but I need someone to help me find food."] = "\\u0628\\u0643\\u0631\\u0647 \\u0623\\u0637\\u0644\\u0628\\u060C \\u0628\\u0633 \\u0628\\u062F\\u064A \\u062D\\u062F\\u0627 \\u064A\\u0633\\u0627\\u0639\\u062F\\u0646\\u064A \\u0623\\u0644\\u0627\\u0642\\u064A \\u0623\\u0643\\u0644.",
    ["Please help me eat before I become another person to carry."] = "\\u0633\\u0627\\u0639\\u062F\\u0646\\u064A \\u0622\\u0643\\u0644 \\u0642\\u0628\\u0644 \\u0645\\u0627 \\u0623\\u0635\\u064A\\u0631 \\u0634\\u062E\\u0635 \\u062A\\u0627\\u0646\\u064A \\u0644\\u0627\\u0632\\u0645 \\u062A\\u0634\\u064A\\u0644\\u0647.",
    ["Critical food deficit. I need a meal immediately."] = "\\u0646\\u0642\\u0635 \\u0623\\u0643\\u0644 \\u062D\\u0631\\u062C. \\u0628\\u062F\\u064A \\u0648\\u062C\\u0628\\u0629 \\u062D\\u0627\\u0644\\u0627.",
    ["I am no longer fit for work without food."] = "\\u0645\\u0627 \\u0639\\u062F\\u062A \\u0635\\u0627\\u0644\\u062D\\u0629 \\u0644\\u0644\\u0634\\u063A\\u0644 \\u0628\\u062F\\u0648\\u0646 \\u0623\\u0643\\u0644.",
    ["I feel sick with hunger. Please find something."] = "\\u062D\\u0627\\u0633\\u0629 \\u062D\\u0627\\u0644\\u064A \\u0645\\u0631\\u064A\\u0636\\u0629 \\u0645\\u0646 \\u0627\\u0644\\u062C\\u0648\\u0639. \\u062F\\u0628\\u0631 \\u0634\\u064A \\u0631\\u062C\\u0627\\u0621.",
    ["I can't do this on an empty body anymore."] = "\\u0645\\u0627 \\u0639\\u0627\\u062F \\u0641\\u064A\\u0646\\u064A \\u0643\\u0645\\u0644 \\u0628\\u062C\\u0633\\u0645 \\u0641\\u0627\\u0636\\u064A.",
    ["I'm starting to get thirsty."] = "\\u0628\\u0644\\u0634\\u062A \\u0623\\u0639\\u0637\\u0634.",
    ["I could use water at the next stop."] = "\\u0628\\u062D\\u062A\\u0627\\u062C \\u0645\\u064A \\u0628\\u0627\\u0644\\u0648\\u0642\\u0641\\u0629 \\u0627\\u0644\\u062C\\u0627\\u064A\\u0629.",
    ["My mouth is getting dry."] = "\\u062A\\u0645\\u064A \\u0639\\u0645 \\u064A\\u0646\\u0634\\u0641.",
    ["We should keep an eye out for clean water."] = "\\u0644\\u0627\\u0632\\u0645 \\u0646\\u0631\\u0627\\u0642\\u0628 \\u0625\\u0630\\u0627 \\u0641\\u064A \\u0645\\u064A \\u0646\\u0636\\u064A\\u0641\\u0629.",
    ["I need a drink before too long."] = "\\u0628\\u062F\\u064A \\u0623\\u0634\\u0631\\u0628 \\u0642\\u0628\\u0644 \\u0645\\u0627 \\u064A\\u0637\\u0648\\u0644.",
    ["Not urgent yet, but I am getting thirsty."] = "\\u0645\\u0648 \\u0645\\u0644\\u062D \\u0644\\u0633\\u0627\\u060C \\u0628\\u0633 \\u0639\\u0645 \\u0623\\u0639\\u0637\\u0634.",
    ["I can wait a little. Water at the next safe stop."] = "\\u0641\\u064A\\u0646\\u064A \\u0627\\u0633\\u062A\\u0646\\u0649 \\u0634\\u0648\\u064A. \\u0645\\u064A \\u0628\\u0623\\u0648\\u0644 \\u0648\\u0642\\u0641\\u0629 \\u0622\\u0645\\u0646\\u0629.",
    ["Dry mouth, steady feet. For now."] = "\\u062A\\u0645 \\u0646\\u0627\\u0634\\u0641\\u060C \\u0648\\u0631\\u062C\\u0644\\u064A\\u0646 \\u062B\\u0627\\u0628\\u062A\\u0629. \\u0647\\u0644\\u0623.",
    ["I am getting thirsty. Let's not let it slow my judgement."] = "\\u0639\\u0645 \\u0623\\u0639\\u0637\\u0634. \\u0645\\u0627 \\u0646\\u062E\\u0644\\u064A\\u0647 \\u064A\\u0628\\u0637\\u0626 \\u062D\\u0643\\u0645\\u064A.",
    ["Clean water soon, before this becomes a problem."] = "\\u0645\\u064A \\u0646\\u0636\\u064A\\u0641\\u0629 \\u0642\\u0631\\u064A\\u0628\\u060C \\u0642\\u0628\\u0644 \\u0645\\u0627 \\u062A\\u0635\\u064A\\u0631 \\u0645\\u0634\\u0643\\u0644\\u0629.",
    ["I need a drink soon. Does everyone else have water?"] = "\\u0628\\u062F\\u064A \\u0623\\u0634\\u0631\\u0628 \\u0642\\u0631\\u064A\\u0628. \\u0639\\u0646\\u062F \\u0627\\u0644\\u0628\\u0627\\u0642\\u064A \\u0645\\u064A\\u061F",
    ["Water at the next stop, for all of us if we can."] = "\\u0645\\u064A \\u0628\\u0627\\u0644\\u0648\\u0642\\u0641\\u0629 \\u0627\\u0644\\u062C\\u0627\\u064A\\u0629\\u060C \\u0644\\u0644\\u0643\\u0644 \\u0625\\u0630\\u0627 \\u0628\\u0646\\u0642\\u062F\\u0631.",
    ["Thirst is becoming noticeable."] = "\\u0627\\u0644\\u0639\\u0637\\u0634 \\u0635\\u0627\\u0631 \\u0645\\u0644\\u062D\\u0648\\u0638.",
    ["Water need is rising, not critical yet."] = "\\u0627\\u0644\\u062D\\u0627\\u062C\\u0629 \\u0644\\u0644\\u0645\\u064A \\u0639\\u0645 \\u062A\\u0632\\u064A\\u062F\\u060C \\u0645\\u0648 \\u062D\\u0631\\u062C\\u0629 \\u0644\\u0633\\u0627.",
    ["I need water soon."] = "\\u0628\\u062F\\u064A \\u0645\\u064A \\u0642\\u0631\\u064A\\u0628.",
    ["I'm too thirsty to ignore it now."] = "\\u0639\\u0637\\u0634\\u0627\\u0646\\u0629 \\u0644\\u062F\\u0631\\u062C\\u0629 \\u0645\\u0627 \\u0641\\u064A\\u0646\\u064A \\u062A\\u062C\\u0627\\u0647\\u0644\\u0647.",
    ["We need to find clean water."] = "\\u0644\\u0627\\u0632\\u0645 \\u0646\\u0644\\u0627\\u0642\\u064A \\u0645\\u064A \\u0646\\u0636\\u064A\\u0641\\u0629.",
    ["My head is starting to ache. I need a drink."] = "\\u0631\\u0627\\u0633\\u064A \\u0628\\u0644\\u0634 \\u064A\\u0648\\u062C\\u0639\\u0646\\u064A. \\u0628\\u062F\\u064A \\u0623\\u0634\\u0631\\u0628.",
    ["Water has to become a priority."] = "\\u0627\\u0644\\u0645\\u064A \\u0644\\u0627\\u0632\\u0645 \\u062A\\u0635\\u064A\\u0631 \\u0623\\u0648\\u0644\\u0648\\u064A\\u0629.",
    ["I cannot keep moving without a drink much longer."] = "\\u0645\\u0627 \\u0641\\u064A\\u0646\\u064A \\u0643\\u0645\\u0644 \\u0628\\u062F\\u0648\\u0646 \\u0634\\u0631\\u0628 \\u0643\\u062A\\u064A\\u0631.",
    ["I can push through a lot. Thirst is winning."] = "\\u0641\\u064A\\u0646\\u064A \\u062A\\u062D\\u0645\\u0644 \\u0643\\u062A\\u064A\\u0631. \\u0628\\u0633 \\u0627\\u0644\\u0639\\u0637\\u0634 \\u0639\\u0645 \\u064A\\u063A\\u0644\\u0628\\u0646\\u064A.",
    ["Find me water before the next fight."] = "\\u062F\\u0628\\u0631\\u0644\\u064A \\u0645\\u064A \\u0642\\u0628\\u0644 \\u0627\\u0644\\u0645\\u0639\\u0631\\u0643\\u0629 \\u0627\\u0644\\u062C\\u0627\\u064A\\u0629.",
    ["Dehydration is slowing me down. We need water before another risk."] = "\\u0627\\u0644\\u062C\\u0641\\u0627\\u0641 \\u0639\\u0645 \\u064A\\u0628\\u0637\\u0626\\u0646\\u064A. \\u0628\\u062F\\u0646\\u0627 \\u0645\\u064A \\u0642\\u0628\\u0644 \\u0623\\u064A \\u0645\\u062E\\u0627\\u0637\\u0631\\u0629.",
    ["I need a drink while I can still think clearly."] = "\\u0628\\u062F\\u064A \\u0623\\u0634\\u0631\\u0628 \\u0648\\u0623\\u0646\\u0627 \\u0644\\u0633\\u0627 \\u0642\\u0627\\u062F\\u0631\\u0629 \\u0623\\u0641\\u0643\\u0631 \\u0628\\u0648\\u0636\\u0648\\u062D.",
    ["I need water. Please don't give me someone else's last bottle."] = "\\u0628\\u062F\\u064A \\u0645\\u064A. \\u0628\\u0633 \\u0644\\u0627 \\u062A\\u0639\\u0637\\u064A\\u0646\\u064A \\u0622\\u062E\\u0631 \\u0642\\u0646\\u064A\\u0646\\u0629 \\u062D\\u062F\\u0627 \\u062A\\u0627\\u0646\\u064A.",
    ["Can we find enough water without leaving anyone short?"] = "\\u0641\\u064A\\u0646\\u0627 \\u0646\\u0644\\u0627\\u0642\\u064A \\u0645\\u064A \\u062A\\u0643\\u0641\\u064A \\u0628\\u062F\\u0648\\u0646 \\u0645\\u0627 \\u064A\\u0646\\u0642\\u0635 \\u0639\\u0646\\u062F \\u062D\\u062F\\u0627\\u061F",
    ["Thirst is impairing me. Water is now a priority."] = "\\u0627\\u0644\\u0639\\u0637\\u0634 \\u0639\\u0645 \\u064A\\u0623\\u062B\\u0631 \\u0639\\u0644\\u064A. \\u0627\\u0644\\u0645\\u064A \\u0635\\u0627\\u0631\\u062A \\u0623\\u0648\\u0644\\u0648\\u064A\\u0629.",
    ["I need safe fluid before the next demanding job."] = "\\u0628\\u062F\\u064A \\u0633\\u0648\\u0627\\u0626\\u0644 \\u0622\\u0645\\u0646\\u0629 \\u0642\\u0628\\u0644 \\u0627\\u0644\\u0634\\u063A\\u0644\\u0629 \\u0627\\u0644\\u0635\\u0639\\u0628\\u0629 \\u0627\\u0644\\u062C\\u0627\\u064A\\u0629.",
    ["My mouth is so dry I can barely talk."] = "\\u062A\\u0645\\u064A \\u0646\\u0627\\u0634\\u0641 \\u0644\\u062F\\u0631\\u062C\\u0629 \\u0628\\u0627\\u0644\\u0643\\u0627\\u062F \\u0628\\u062D\\u0643\\u064A.",
    ["Please find water. I can't focus."] = "\\u062F\\u0628\\u0631 \\u0645\\u064A \\u0631\\u062C\\u0627\\u0621. \\u0645\\u0627 \\u0639\\u0645 \\u0642\\u062F\\u0631 \\u0623\\u0631\\u0643\\u0632.",
    ["I need water now."] = "\\u0628\\u062F\\u064A \\u0645\\u064A \\u0647\\u0644\\u0623.",
    ["I'm dangerously thirsty."] = "\\u0639\\u0637\\u0634\\u0627\\u0646\\u0629 \\u0644\\u062F\\u0631\\u062C\\u0629 \\u0627\\u0644\\u062E\\u0637\\u0631.",
    ["Stop. I need something safe to drink."] = "\\u0648\\u0642\\u0641. \\u0628\\u062F\\u064A \\u0634\\u064A \\u0622\\u0645\\u0646 \\u0623\\u0634\\u0631\\u0628\\u0647.",
    ["I cannot keep going without water."] = "\\u0645\\u0627 \\u0641\\u064A\\u0646\\u064A \\u0643\\u0645\\u0644 \\u0628\\u062F\\u0648\\u0646 \\u0645\\u064A.",
    ["Water, please. Anything clean."] = "\\u0645\\u064A\\u060C \\u0631\\u062C\\u0627\\u0621. \\u0623\\u064A \\u0634\\u064A \\u0646\\u0636\\u064A\\u0641.",
    ["I'm drying out. We have to find water."] = "\\u0639\\u0645 \\u0623\\u0646\\u0634\\u0641. \\u0644\\u0627\\u0632\\u0645 \\u0646\\u0644\\u0627\\u0642\\u064A \\u0645\\u064A.",
    ["I am done pretending I can push through this. Water now."] = "\\u062E\\u0644\\u0635 \\u0645\\u0627 \\u0639\\u062F\\u062A \\u0623\\u062F\\u0639\\u064A \\u0625\\u0646\\u064A \\u0628\\u062A\\u062D\\u0645\\u0644. \\u0645\\u064A \\u0647\\u0644\\u0623.",
    ["No more ground until I get a drink."] = "\\u0648\\u0644\\u0627 \\u062E\\u0637\\u0648\\u0629 \\u062A\\u0627\\u0646\\u064A\\u0629 \\u0642\\u0628\\u0644 \\u0645\\u0627 \\u0623\\u0634\\u0631\\u0628.",
    ["This is unsafe. I need water before we move."] = "\\u0647\\u0627\\u062F \\u0645\\u0648 \\u0622\\u0645\\u0646. \\u0628\\u062F\\u064A \\u0645\\u064A \\u0642\\u0628\\u0644 \\u0645\\u0627 \\u0646\\u062A\\u062D\\u0631\\u0643.",
    ["I am too dehydrated for another run."] = "\\u062C\\u0641\\u0627\\u0641\\u064A \\u0643\\u062A\\u064A\\u0631 \\u0644\\u062C\\u0648\\u0644\\u0629 \\u062A\\u0627\\u0646\\u064A\\u0629.",
    ["Please help me find water. I really need it."] = "\\u0633\\u0627\\u0639\\u062F\\u0646\\u064A \\u0623\\u0644\\u0627\\u0642\\u064A \\u0645\\u064A \\u0631\\u062C\\u0627\\u0621. \\u0641\\u0639\\u0644\\u0627 \\u0645\\u062D\\u062A\\u0627\\u062C\\u062A\\u0647\\u0627.",
    ["I don't want to become a burden. I need a drink now."] = "\\u0645\\u0627 \\u0628\\u062F\\u064A \\u0635\\u064A\\u0631 \\u0639\\u0628\\u0621. \\u0628\\u062F\\u064A \\u0623\\u0634\\u0631\\u0628 \\u0647\\u0644\\u0623.",
    ["Critical dehydration. I need water immediately."] = "\\u062C\\u0641\\u0627\\u0641 \\u062D\\u0631\\u062C. \\u0628\\u062F\\u064A \\u0645\\u064A \\u062D\\u0627\\u0644\\u0627.",
    ["I am no longer fit for work without fluids."] = "\\u0645\\u0627 \\u0639\\u062F\\u062A \\u0635\\u0627\\u0644\\u062D\\u0629 \\u0644\\u0644\\u0634\\u063A\\u0644 \\u0628\\u062F\\u0648\\u0646 \\u0633\\u0648\\u0627\\u0626\\u0644.",
    ["I can't swallow. Please, water."] = "\\u0645\\u0627 \\u0639\\u0645 \\u0642\\u062F\\u0631 \\u0627\\u0628\\u0644\\u0639. \\u0631\\u062C\\u0627\\u0621\\u060C \\u0645\\u064A.",
    ["Everything hurts and I need a drink now."] = "\\u0643\\u0644 \\u0634\\u064A \\u0628\\u064A\\u0648\\u062C\\u0639 \\u0648\\u0628\\u062F\\u064A \\u0623\\u0634\\u0631\\u0628 \\u0647\\u0644\\u0623.",
    ["I'm starting to feel tired."] = "\\u0628\\u0644\\u0634\\u062A \\u0623\\u062A\\u0639\\u0628.",
    ["I could use rest when we get a safe chance."] = "\\u0628\\u062D\\u062A\\u0627\\u062C \\u0631\\u0627\\u062D\\u0629 \\u0644\\u0645\\u0627 \\u062A\\u0635\\u064A\\u0631 \\u0641\\u0631\\u0635\\u0629 \\u0622\\u0645\\u0646\\u0629.",
    ["My legs are getting heavy."] = "\\u0631\\u062C\\u0644\\u064A\\u064A \\u0639\\u0645 \\u064A\\u062A\\u0642\\u0644\\u0648\\u0627.",
    ["A short rest should go on the plan."] = "\\u0644\\u0627\\u0632\\u0645 \\u0646\\u062D\\u0637 \\u0627\\u0633\\u062A\\u0631\\u0627\\u062D\\u0629 \\u0642\\u0635\\u064A\\u0631\\u0629 \\u0628\\u0627\\u0644\\u062E\\u0637\\u0629.",
    ["I have been awake too long."] = "\\u0635\\u0627\\u0631 \\u0644\\u064A \\u0635\\u0627\\u062D\\u064A\\u0629 \\u0643\\u062A\\u064A\\u0631.",
    ["Not done yet, but I am getting tired."] = "\\u0644\\u0633\\u0627 \\u0645\\u0627 \\u062E\\u0644\\u0635\\u062A\\u060C \\u0628\\u0633 \\u0639\\u0645 \\u0623\\u062A\\u0639\\u0628.",
    ["Still moving. I will need rest later."] = "\\u0644\\u0633\\u0627 \\u0645\\u0627\\u0634\\u064A\\u0629. \\u0631\\u062D \\u0623\\u062D\\u062A\\u0627\\u062C \\u0631\\u0627\\u062D\\u0629 \\u0628\\u0639\\u062F\\u064A\\u0646.",
    ["Tired, not beaten. Put sleep on the list."] = "\\u062A\\u0639\\u0628\\u0627\\u0646\\u0629\\u060C \\u0645\\u0648 \\u0645\\u0647\\u0632\\u0648\\u0645\\u0629. \\u062D\\u0637 \\u0627\\u0644\\u0646\\u0648\\u0645 \\u0639\\u0627\\u0644\\u0642\\u0627\\u0626\\u0645\\u0629.",
    ["Fatigue causes mistakes. I should rest soon."] = "\\u0627\\u0644\\u062A\\u0639\\u0628 \\u0628\\u064A\\u0633\\u0628\\u0628 \\u0623\\u062E\\u0637\\u0627\\u0621. \\u0644\\u0627\\u0632\\u0645 \\u0623\\u0631\\u062A\\u0627\\u062D \\u0642\\u0631\\u064A\\u0628.",
    ["I am getting tired enough to watch my footing."] = "\\u062A\\u0639\\u0628\\u062A \\u0644\\u062F\\u0631\\u062C\\u0629 \\u0644\\u0627\\u0632\\u0645 \\u0623\\u0646\\u062A\\u0628\\u0647 \\u0644\\u062E\\u0637\\u0648\\u0627\\u062A\\u064A.",
    ["I'm getting tired. We should make sure everyone gets a turn to rest."] = "\\u0639\\u0645 \\u0623\\u062A\\u0639\\u0628. \\u0644\\u0627\\u0632\\u0645 \\u0646\\u062A\\u0623\\u0643\\u062F \\u0625\\u0646\\u0648 \\u0627\\u0644\\u0643\\u0644 \\u064A\\u0627\\u062E\\u062F \\u062F\\u0648\\u0631 \\u0628\\u0627\\u0644\\u0631\\u0627\\u062D\\u0629.",
    ["I need sleep soon, but check the others too."] = "\\u0628\\u062F\\u064A \\u0646\\u0648\\u0645 \\u0642\\u0631\\u064A\\u0628\\u060C \\u0628\\u0633 \\u0634\\u0648\\u0641 \\u0627\\u0644\\u0628\\u0627\\u0642\\u064A \\u0643\\u0645\\u0627\\u0646.",
    ["Fatigue is becoming noticeable."] = "\\u0627\\u0644\\u062A\\u0639\\u0628 \\u0635\\u0627\\u0631 \\u0645\\u0644\\u062D\\u0648\\u0638.",
    ["Rest need is rising, but I remain functional."] = "\\u062D\\u0627\\u062C\\u062A\\u064A \\u0644\\u0644\\u0631\\u0627\\u062D\\u0629 \\u0639\\u0645 \\u062A\\u0632\\u064A\\u062F\\u060C \\u0628\\u0633 \\u0644\\u0633\\u0627 \\u0639\\u0645 \\u0627\\u0634\\u062A\\u063A\\u0644.",
    ["I need to rest soon."] = "\\u0644\\u0627\\u0632\\u0645 \\u0623\\u0631\\u062A\\u0627\\u062D \\u0642\\u0631\\u064A\\u0628.",
    ["I'm too tired to stay sharp."] = "\\u062A\\u0639\\u0628\\u0627\\u0646\\u0629 \\u0644\\u062F\\u0631\\u062C\\u0629 \\u0645\\u0627 \\u0641\\u064A\\u0646\\u064A \\u0636\\u0644 \\u0645\\u062A\\u064A\\u0642\\u0638\\u0629.",
    ["We need somewhere safe enough to sleep."] = "\\u0628\\u062F\\u0646\\u0627 \\u0645\\u0643\\u0627\\u0646 \\u0622\\u0645\\u0646 \\u0643\\u0641\\u0627\\u064A\\u0629 \\u0644\\u0646\\u0646\\u0627\\u0645.",
    ["My eyes keep losing focus."] = "\\u0639\\u064A\\u0648\\u0646\\u064A \\u0639\\u0645 \\u062A\\u0641\\u0642\\u062F \\u0627\\u0644\\u062A\\u0631\\u0643\\u064A\\u0632.",
    ["Rest has to become a priority."] = "\\u0627\\u0644\\u0631\\u0627\\u062D\\u0629 \\u0644\\u0627\\u0632\\u0645 \\u062A\\u0635\\u064A\\u0631 \\u0623\\u0648\\u0644\\u0648\\u064A\\u0629.",
    ["I cannot keep this pace much longer."] = "\\u0645\\u0627 \\u0641\\u064A\\u0646\\u064A \\u0643\\u0645\\u0644 \\u0628\\u0647\\u0627\\u0644\\u0648\\u062A\\u064A\\u0631\\u0629 \\u0643\\u062A\\u064A\\u0631.",
    ["I can force another mile. I should not have to."] = "\\u0641\\u064A\\u0646\\u064A \\u0623\\u062C\\u0628\\u0631 \\u062D\\u0627\\u0644\\u064A \\u0645\\u064A\\u0644 \\u0643\\u0645\\u0627\\u0646. \\u0628\\u0633 \\u0645\\u0627 \\u0644\\u0627\\u0632\\u0645.",
    ["Tired fighters make dead fighters. I need rest."] = "\\u0627\\u0644\\u0645\\u0642\\u0627\\u062A\\u0644 \\u0627\\u0644\\u062A\\u0639\\u0628\\u0627\\u0646 \\u0628\\u064A\\u0645\\u0648\\u062A. \\u0628\\u062F\\u064A \\u0631\\u0627\\u062D\\u0629.",
    ["My reactions are slowing. We need shelter before another risk."] = "\\u0631\\u062F\\u0648\\u062F \\u0641\\u0639\\u0644\\u064A \\u0639\\u0645 \\u062A\\u0628\\u0637\\u0623. \\u0628\\u062F\\u0646\\u0627 \\u0645\\u0623\\u0648\\u0649 \\u0642\\u0628\\u0644 \\u0623\\u064A \\u0645\\u062E\\u0627\\u0637\\u0631\\u0629.",
    ["I need sleep before I miss something important."] = "\\u0628\\u062F\\u064A \\u0646\\u0648\\u0645 \\u0642\\u0628\\u0644 \\u0645\\u0627 \\u064A\\u0641\\u0648\\u062A\\u0646\\u064A \\u0634\\u064A \\u0645\\u0647\\u0645.",
    ["I need rest. Someone else may have to take my watch."] = "\\u0628\\u062F\\u064A \\u0631\\u0627\\u062D\\u0629. \\u0645\\u0645\\u0643\\u0646 \\u062D\\u062F\\u0627 \\u062A\\u0627\\u0646\\u064A \\u064A\\u0627\\u062E\\u062F \\u0646\\u0648\\u0628\\u062A\\u064A.",
    ["Please find us somewhere safe enough to stop."] = "\\u062F\\u0628\\u0631\\u0644\\u0646\\u0627 \\u0645\\u0643\\u0627\\u0646 \\u0622\\u0645\\u0646 \\u0643\\u0641\\u0627\\u064A\\u0629 \\u0644\\u0646\\u0648\\u0642\\u0641.",
    ["Fatigue is impairing me. Rest is now a priority."] = "\\u0627\\u0644\\u062A\\u0639\\u0628 \\u0639\\u0645 \\u064A\\u0623\\u062B\\u0631 \\u0639\\u0644\\u064A. \\u0627\\u0644\\u0631\\u0627\\u062D\\u0629 \\u0635\\u0627\\u0631\\u062A \\u0623\\u0648\\u0644\\u0648\\u064A\\u0629.",
    ["I need a sleep cycle before the next demanding job."] = "\\u0628\\u062F\\u064A \\u062F\\u0648\\u0631\\u0629 \\u0646\\u0648\\u0645 \\u0642\\u0628\\u0644 \\u0627\\u0644\\u0634\\u063A\\u0644\\u0629 \\u0627\\u0644\\u0635\\u0639\\u0628\\u0629 \\u0627\\u0644\\u062C\\u0627\\u064A\\u0629.",
    ["I can't keep my thoughts in order. I need sleep."] = "\\u0645\\u0627 \\u0639\\u0645 \\u0642\\u062F\\u0631 \\u0631\\u062A\\u0628 \\u0623\\u0641\\u0643\\u0627\\u0631\\u064A. \\u0628\\u062F\\u064A \\u0646\\u0648\\u0645.",
    ["I'm so tired everything feels dangerous."] = "\\u062A\\u0639\\u0628\\u0627\\u0646\\u0629 \\u0644\\u062F\\u0631\\u062C\\u0629 \\u0643\\u0644 \\u0634\\u064A \\u0635\\u0627\\u0631 \\u062D\\u0627\\u0633\\u0633\\u062A\\u0647 \\u062E\\u0637\\u0631.",
    ["I need to sleep now."] = "\\u0644\\u0627\\u0632\\u0645 \\u0623\\u0646\\u0627\\u0645 \\u0647\\u0644\\u0623.",
    ["I can barely stay awake."] = "\\u0628\\u0627\\u0644\\u0643\\u0627\\u062F \\u0635\\u0627\\u062D\\u064A\\u0629.",
    ["Stop. I am going to collapse if I keep moving."] = "\\u0648\\u0642\\u0641. \\u0631\\u062D \\u0623\\u0646\\u0647\\u0627\\u0631 \\u0625\\u0630\\u0627 \\u0643\\u0645\\u0644\\u062A.",
    ["I cannot keep watch like this."] = "\\u0645\\u0627 \\u0641\\u064A\\u0646\\u064A \\u0623\\u062D\\u0631\\u0633 \\u0647\\u064A\\u0643.",
    ["Find me somewhere safe to lie down."] = "\\u062F\\u0628\\u0631\\u0644\\u064A \\u0645\\u0643\\u0627\\u0646 \\u0622\\u0645\\u0646 \\u0623\\u0633\\u062A\\u0644\\u0642\\u064A \\u0641\\u064A\\u0647.",
    ["I am past tired. I need sleep."] = "\\u062A\\u0639\\u062F\\u064A\\u062A \\u0627\\u0644\\u062A\\u0639\\u0628. \\u0628\\u062F\\u064A \\u0646\\u0648\\u0645.",
    ["I have hit my limit. I need sleep now."] = "\\u0648\\u0635\\u0644\\u062A \\u0644\\u062D\\u062F\\u064A. \\u0628\\u062F\\u064A \\u0646\\u0648\\u0645 \\u0647\\u0644\\u0623.",
    ["No more pushing. I can barely stand."] = "\\u062E\\u0644\\u0635 \\u0645\\u0627 \\u0639\\u0627\\u062F \\u0641\\u064A\\u0646\\u064A \\u0623\\u062F\\u0641\\u0639. \\u0628\\u0627\\u0644\\u0643\\u0627\\u062F \\u0648\\u0627\\u0642\\u0641\\u0629.",
    ["I am too tired to be safe. We stop here."] = "\\u062A\\u0639\\u0628\\u0627\\u0646\\u0629 \\u0644\\u062F\\u0631\\u062C\\u0629 \\u0645\\u0627 \\u0628\\u0642\\u062F\\u0631 \\u0622\\u0645\\u0646 \\u062D\\u0627\\u0644\\u064A. \\u0645\\u0646\\u0648\\u0642\\u0641 \\u0647\\u0648\\u0646.",
    ["My reactions are gone. I need shelter and sleep."] = "\\u0631\\u0627\\u062D\\u062A \\u0631\\u062F\\u0648\\u062F \\u0641\\u0639\\u0644\\u064A. \\u0628\\u062F\\u064A \\u0645\\u0623\\u0648\\u0649 \\u0648\\u0646\\u0648\\u0645.",
    ["Please take over for me. I cannot stay awake."] = "\\u0631\\u062C\\u0627\\u0621 \\u062E\\u0648\\u062F \\u0645\\u0643\\u0627\\u0646\\u064A. \\u0645\\u0627 \\u0641\\u064A\\u0646\\u064A \\u0636\\u0644 \\u0635\\u0627\\u062D\\u064A\\u0629.",
    ["I need help finding somewhere safe to sleep."] = "\\u0628\\u062F\\u064A \\u0645\\u0633\\u0627\\u0639\\u062F\\u0629 \\u0623\\u0644\\u0627\\u0642\\u064A \\u0645\\u0643\\u0627\\u0646 \\u0622\\u0645\\u0646 \\u0644\\u0623\\u0646\\u0627\\u0645.",
    ["Critical fatigue. I am no longer operational."] = "\\u062A\\u0639\\u0628 \\u062D\\u0631\\u062C. \\u0645\\u0627 \\u0639\\u062F\\u062A \\u0642\\u0627\\u062F\\u0631\\u0629 \\u0639\\u0644\\u0649 \\u0627\\u0644\\u0639\\u0645\\u0644.",
    ["I need immediate rest before I become a liability."] = "\\u0628\\u062F\\u064A \\u0631\\u0627\\u062D\\u0629 \\u0641\\u0648\\u0631\\u064A\\u0629 \\u0642\\u0628\\u0644 \\u0645\\u0627 \\u0623\\u0635\\u064A\\u0631 \\u0639\\u0628\\u0621.",
    ["I can't keep my eyes open. Please stop."] = "\\u0645\\u0627 \\u0641\\u064A\\u0646\\u064A \\u0641\\u062A\\u062D \\u0639\\u064A\\u0648\\u0646\\u064A. \\u0631\\u062C\\u0627\\u0621 \\u0648\\u0642\\u0641.",
    ["I am falling apart. I need sleep now."] = "\\u0639\\u0645 \\u0623\\u062A\\u0641\\u0643\\u0643. \\u0628\\u062F\\u064A \\u0646\\u0648\\u0645 \\u0647\\u0644\\u0623.",
    ["It's getting dark. Let's make sure everyone's back."] = "\\u0639\\u0645 \\u064A\\u0639\\u062A\\u0645. \\u062E\\u0644\\u064A\\u0646\\u0627 \\u0646\\u062A\\u0623\\u0643\\u062F \\u0625\\u0646\\u0648 \\u0627\\u0644\\u0643\\u0644 \\u0631\\u062C\\u0639.",
    ["If you're waiting for a sign, this is it. It says 'beans'."] = "\\u0625\\u0630\\u0627 \\u0643\\u0646\\u062A \\u0645\\u0633\\u062A\\u0646\\u064A \\u0639\\u0644\\u0627\\u0645\\u0629\\u060C \\u0647\\u0627\\u064A \\u0647\\u064A. \\u0645\\u0643\\u062A\\u0648\\u0628 \\u0639\\u0644\\u064A\\u0647\\u0627 '\\u0641\\u0627\\u0635\\u0648\\u0644\\u064A\\u0627'.",
    ["Mamaw could shell a bushel of beans in the time you've been standing there."] = "\\u0633\\u062A\\u064A \\u0643\\u0627\\u0646\\u062A \\u0628\\u062A\\u0642\\u0634\\u0631 \\u0643\\u064A\\u0633 \\u0641\\u0627\\u0635\\u0648\\u0644\\u064A\\u0627 \\u0628\\u0627\\u0644\\u0648\\u0642\\u062A \\u0627\\u0644\\u0644\\u064A \\u0625\\u0646\\u062A \\u0648\\u0627\\u0642\\u0641\\u0647 \\u0647\\u0648\\u0646.",
    ["Take your time. The zombies sure are."] = "\\u062E\\u062F \\u0631\\u0627\\u062D\\u062A\\u0643. \\u0627\\u0644\\u0632\\u0648\\u0645\\u0628\\u064A \\u0623\\u0643\\u064A\\u062F \\u0639\\u0645 \\u064A\\u0627\\u062E\\u062F\\u0648\\u0627 \\u0631\\u0627\\u062D\\u062A\\u0647\\u0645.",
    ["Waiting's a skill too. You're maxing it out."] = "\\u0627\\u0644\\u0627\\u0646\\u062A\\u0638\\u0627\\u0631 \\u0645\\u0647\\u0627\\u0631\\u0629 \\u0643\\u0645\\u0627\\u0646. \\u0648\\u0625\\u0646\\u062A \\u0639\\u0645 \\u062A\\u0648\\u0635\\u0644\\u0647\\u0627 \\u0644\\u0644\\u062D\\u062F \\u0627\\u0644\\u0623\\u0642\\u0635\\u0649.",
    ["Nothing urgent. I'm holding this position."] = "\\u0648\\u0644\\u0627 \\u0634\\u064A \\u0645\\u0644\\u062D. \\u062B\\u0627\\u0628\\u062A\\u0629 \\u0628\\u0645\\u0643\\u0627\\u0646\\u064A.",
    ["I have something in mind, but I don't know you well enough yet."] = "\\u0639\\u0646\\u062F\\u064A \\u0634\\u064A \\u0628\\u0628\\u0627\\u0644\\u064A\\u060C \\u0628\\u0633 \\u0644\\u0633\\u0627 \\u0645\\u0627 \\u0628\\u0639\\u0631\\u0641\\u0643 \\u0643\\u0641\\u0627\\u064A\\u0629.",
    ["We still know how to do something besides lose things."] = "\\u0644\\u0633\\u0627 \\u0645\\u0646\\u0639\\u0631\\u0641 \\u0646\\u0639\\u0645\\u0644 \\u0634\\u064A \\u063A\\u064A\\u0631 \\u0625\\u0646\\u0648 \\u0646\\u062E\\u0633\\u0631 \\u0627\\u0644\\u0623\\u0634\\u064A\\u0627\\u0621.",
    ["You have been fair with me so far."] = "\\u0643\\u0646\\u062A \\u0645\\u0646\\u0635\\u0641 \\u0645\\u0639\\u064A \\u0644\\u0647\\u0644\\u0623.",
    ["We are still learning each other, but I trust you more than I did."] = "\\u0644\\u0633\\u0627 \\u0639\\u0645 \\u0646\\u062A\\u0639\\u0631\\u0641 \\u0639\\u0644\\u0649 \\u0628\\u0639\\u0636\\u060C \\u0628\\u0633 \\u0635\\u0631\\u062A \\u0623\\u0648\\u062B\\u0642 \\u0641\\u064A\\u0643 \\u0623\\u0643\\u062A\\u0631 \\u0645\\u0646 \\u0642\\u0628\\u0644.",
    ["I traced faults for a living. I still look for the broken link before I start replacing everything."] = "\\u0643\\u0646\\u062A \\u0623\\u062F\\u0648\\u0631 \\u0639\\u0644\\u0649 \\u0627\\u0644\\u0623\\u0639\\u0637\\u0627\\u0644 \\u0643\\u0634\\u063A\\u0644\\u062A\\u064A. \\u0648\\u0628\\u0639\\u062F\\u0646\\u064A \\u0628\\u062F\\u0648\\u0631 \\u0639\\u0644\\u0649 \\u0627\\u0644\\u062D\\u0644\\u0642\\u0629 \\u0627\\u0644\\u0645\\u0643\\u0633\\u0648\\u0631\\u0629 \\u0642\\u0628\\u0644 \\u0645\\u0627 \\u0623\\u0628\\u062F\\u0623 \\u0623\\u0628\\u062F\\u0644 \\u0643\\u0644 \\u0634\\u064A.",
    ["I can scavenge this route. I will avoid containers you already searched."] = "\\u0641\\u064A\\u0646\\u064A \\u0641\\u062A\\u0634 \\u0647\\u0627\\u0644\\u0637\\u0631\\u064A\\u0642. \\u0631\\u062D \\u0623\\u062A\\u062C\\u0646\\u0628 \\u0627\\u0644\\u062D\\u0627\\u0648\\u064A\\u0627\\u062A \\u0627\\u0644\\u0644\\u064A \\u0641\\u062A\\u0634\\u062A\\u0647\\u0627 \\u0625\\u0646\\u062A.",
    ["Brandenburg roads could lead you to a church or a liquor store."] = "\\u0637\\u0631\\u0642\\u0627\\u062A \\u0628\\u0631\\u0627\\u0646\\u062F\\u0646\\u0628\\u0648\\u0631\\u063A \\u0645\\u0645\\u0643\\u0646 \\u062A\\u0648\\u0635\\u0644\\u0643 \\u0644\\u0643\\u0646\\u064A\\u0633\\u0629 \\u0623\\u0648 \\u0644\\u0645\\u062D\\u0644 \\u0645\\u0634\\u0631\\u0648\\u0628\\u0627\\u062A.",
    ["Watch the corners. They don't announce themselves."] = "\\u0627\\u0646\\u062A\\u0628\\u0647 \\u0639\\u0627\\u0644\\u0632\\u0648\\u0627\\u064A\\u0627. \\u0645\\u0627 \\u0628\\u064A\\u0639\\u0644\\u0646\\u0648\\u0627 \\u0639\\u0646 \\u062D\\u0627\\u0644\\u0647\\u0645.",
    ["Walking together beats walking alone. Even now."] = "\\u0627\\u0644\\u0645\\u0634\\u064A \\u0633\\u0648\\u0627 \\u0623\\u062D\\u0633\\u0646 \\u0645\\u0646 \\u0627\\u0644\\u0645\\u0634\\u064A \\u0644\\u062D\\u0627\\u0644\\u0643. \\u062D\\u062A\\u0649 \\u0647\\u0644\\u0623.",
    ["Right behind you."] = "\\u0648\\u0631\\u0627\\u064A\\u0643 \\u0645\\u0628\\u0627\\u0634\\u0631\\u0629.",
    ["Roadside ditches never used to worry me. Funny how that changed."] = "\\u062E\\u0646\\u0627\\u062F\\u0642 \\u062C\\u0646\\u0628 \\u0627\\u0644\\u0637\\u0631\\u064A\\u0642 \\u0645\\u0627 \\u0643\\u0627\\u0646\\u062A \\u062A\\u0642\\u0644\\u0642\\u0646\\u064A. \\u063A\\u0631\\u064A\\u0628 \\u0643\\u064A\\u0641 \\u062A\\u063A\\u064A\\u0631 \\u0647\\u0627\\u062F.",
    ["Lone zombie ahead."] = "\\u0632\\u0648\\u0645\\u0628\\u064A \\u0644\\u062D\\u0627\\u0644\\u0647 \\u0642\\u062F\\u0627\\u0645\\u0646\\u0627.",
    ["Single contact. Check the corners too."] = "\\u0627\\u062D\\u062A\\u0643\\u0627\\u0643 \\u0648\\u0627\\u062D\\u062F. \\u0634\\u064A\\u0643 \\u0639\\u0627\\u0644\\u0632\\u0648\\u0627\\u064A\\u0627 \\u0643\\u0645\\u0627\\u0646.",
    ["I've got one moving out there."] = "\\u0641\\u064A \\u0648\\u0627\\u062D\\u062F \\u0639\\u0645 \\u064A\\u062A\\u062D\\u0631\\u0643 \\u0628\\u0631\\u0627.",
    ["One walker crossing our path."] = "\\u0645\\u0627\\u0634\\u064A \\u0648\\u0627\\u062D\\u062F \\u0639\\u0645 \\u064A\\u0642\\u0637\\u0639 \\u0637\\u0631\\u064A\\u0642\\u0646\\u0627.",
    ["One zombie. There may be more behind it."] = "\\u0632\\u0648\\u0645\\u0628\\u064A \\u0648\\u0627\\u062D\\u062F. \\u0645\\u0645\\u0643\\u0646 \\u0641\\u064A \\u063A\\u064A\\u0631\\u0647 \\u0648\\u0631\\u0627\\u0647.",
    ["I heard shuffling. Stay alert."] = "\\u0633\\u0645\\u0639\\u062A \\u0635\\u0648\\u062A \\u062C\\u0631\\u062C\\u0631\\u0629. \\u062E\\u0644\\u064A\\u0643 \\u0645\\u0646\\u062A\\u0628\\u0647.",
    ["Remember, folks: idle hands get eaten."] = "\\u062A\\u0630\\u0643\\u0631\\u0648\\u0627 \\u064A\\u0627 \\u062C\\u0645\\u0627\\u0639\\u0629: \\u0627\\u0644\\u0623\\u064A\\u062F\\u064A \\u0627\\u0644\\u0641\\u0627\\u0636\\u064A\\u0629 \\u0628\\u062A\\u0646\\u0623\\u0643\\u0644.",
    ["Another productive day in scenic Knox County."] = "\\u064A\\u0648\\u0645 \\u0645\\u062B\\u0645\\u0631 \\u062A\\u0627\\u0646\\u064A \\u0628\\u0645\\u0642\\u0627\\u0637\\u0639\\u0629 \\u0646\\u0648\\u0643\\u0633 \\u0627\\u0644\\u062C\\u0645\\u064A\\u0644\\u0629.",
    ["Daylight helps. We should use it."] = "\\u0636\\u0648\\u0621 \\u0627\\u0644\\u0646\\u0647\\u0627\\u0631 \\u0628\\u064A\\u0633\\u0627\\u0639\\u062F. \\u0644\\u0627\\u0632\\u0645 \\u0646\\u0633\\u062A\\u063A\\u0644\\u0647.",
    ["Morning. We made it through another night."] = "\\u0635\\u0628\\u0627\\u062D \\u0627\\u0644\\u062E\\u064A\\u0631. \\u0639\\u062F\\u064A\\u0646\\u0627 \\u0644\\u064A\\u0644\\u0629 \\u062A\\u0627\\u0646\\u064A\\u0629.",
}
local STATES = {
    UI_SC_State_conversation = "\\u0645\\u062D\\u0627\\u062F\\u062B\\u0629",
}
-- these replace the existing Arabic text (a plain wording fix, not a missing key)
local OVERRIDES = {
    UI_SC_Context_NamedAction = "%1: %2",
}

function D.merge(exact, patterns, templatePattern)
    local n = 0
    for en, ar in pairs(D.lines) do
        if type(en) == "string" and type(ar) == "string" then
            if string.find(en, "%%[1-9]") then
                local p, slots = templatePattern(en)
                patterns[#patterns + 1] = { pattern = p, slots = slots, ar = ar }
            else
                exact[en] = ar
            end
            n = n + 1
        end
    end
    return n
end

local seen, count = {}, 0
function D.miss(topic, line)
    if type(line) ~= "string" or line == "" or seen[line] or count >= 400 then return end
    seen[line] = true
    count = count + 1
    if type(getFileWriter) ~= "function" then return end
    local ok, w = pcall(getFileWriter, "SolDialogue_Missing.txt", true, true)
    if ok and w then
        pcall(w.write, w, tostring(topic) .. "\t" .. line .. "\n")
        pcall(w.close, w)
    end
end

function D.display(s)
    if type(s) ~= "string" or s == "" then return s end
    if s == "Sol" or s == "Sol Survivor" then return D.NAME_AR end
    if string.find(s, "Sol Survivor", 1, true) then return (string.gsub(s, "Sol Survivor", D.NAME_AR)) end
    return s
end

if type(SolLF_AR) == "table" then
    for k, v in pairs(STATES) do if SolLF_AR[k] == nil then SolLF_AR[k] = v end end
    for k, v in pairs(OVERRIDES) do SolLF_AR[k] = v end
end
local total = 0
for _ in pairs(D.lines) do total = total + 1 end
print("[SolDialogueLines] ready v" .. D.VERSION .. " lines=" .. total)
