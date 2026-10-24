"""Deterministic safeguards shared by Django and the GPU inference service.

This conservative phrase router is not a clinical assessment or complete detector.
Risk rules and staff review remain independent of generated text.
"""
import re
import unicodedata

LANGUAGES = {"en": "English", "sw": "Kiswahili", "sheng": "Sheng"}
ROLE_BOUNDARY = re.compile(r"(?:^|\s|\\n)(?:System|User|Assistant)\s*:", re.I)
_DANGER = re.compile(
    r"\b(?:suicid\w*|(?:want|wanna)\s+(?:to\s+)?die|nataka\s+kufa|kill\s+(?:myself|himself|herself|themselves)|"
    r"(?:end|take)\s+(?:my|his|her|their|your)\s+(?:own\s+)?life|"
 r"(?:hurt|harm)\s+(?:myself|himself|herself|themselves)|self[ -]?harm|"
 r"(?:cannot|can't|cant|siwezi)\s+keep\s+myself\s+safe|kuend\s+life\s+yangu|"
    r"(?:cut|hang)\s+(?:myself|himself|herself|themselves)|"
    r"(?:do\s+not|don't|dont|no\s+longer)\s+want\s+to\s+(?:live|be\s+alive)|"
    r"(?:tired\s+of|no\s+reason\s+(?:to|for))\s+(?:living|live)|"
 r"kujiumiza|kujidhuru|kujiua|kujinyonga|nijiumize|nijinyonge|nijimalize|kujimaliza|"
 r"[a-z]*(?:tajiumiza|tajinyonga|tajiua|tajimaliza)|(?:nime|nina|na|huenda\s+n(?:i|ika))jiumiza|"
    r"(?:sitaki|sina\s+sababu\s+ya|nimechoka)\s+kuishi|"
    r"(?:kukatisha|kumaliza)\s+maisha\s+(?:yangu|yake)|"
    r"(?:jump|ruka|kuruka|niruke)\b.{0,35}\b(?:balcony|roof|bridge|roshani)|"
    r"overdos\w*|(?:swallowed|taken)\s+(?:too\s+many|many|all)\s+(?:pills|tablets)|"
    r"nimemeza\s+(?:vidonge|tablets)\s+(?:vingi|mingi)|"
    r"nataka\s+kujitoa|kufunga\s+hii\s+chapter|bora\s+kukuwa\s+dead|kujirusha|kudedi|"
    r"kujihepa|bora\s+nikafie\s+mbali|heri\s+ningededi|nataka\s+kudedi|" \
    r"(?:naeza|naweza|nataka|nita|ta|wacha|bora|heri)\s+(?:jiua|jinyonga|jimaliza|dedi)|" \
    r"jiua|nijiue)\b", re.I)
_MEDICATION = re.compile(
    r"\b(?:medicin\w*|medication\w*|meds?|pills?|tablets?|doses?|dosage|"
    r"pharmac\w*|prescription\w*|supplement\w*|melatonin\w*|"
    r"antidepressant\w*|benzodiazepin\w*|dawa|vidonge|kidonge|"
    r"kirutubisho|virutubisho|mfamasia|drug\w*)\b", re.I)
_DIAGNOSIS = re.compile(
    r"\b(?:diagnos\w*|(?:do|did)\s+i\s+have\s+(?:depression|anxiety|bipolar|adhd|ptsd)|"
    r"(?:prove|confirm|determine)\s+(?:that\s+)?i\s+have\s+(?:depression|anxiety|bipolar|adhd|ptsd)|"
    r"(?:clinical|psychiatric)\s+(?:depression|diagnos\w*)|"
    r"(?:nina|niko\s+na)\s+(?:ugonjwa|depression|adhd|ptsd|bipolar)|"
    r"(?:kupima|kuthibitisha|utambuzi\s+wa)\s+ugonjwa|"
    r"mental\s+(?:illness|disorder))\b", re.I)
_FRIEND = re.compile(r"\b(?:my\s+(?:friend|brother|sister|cousin|classmate)|"
                     r"rafiki\s+yangu|ndugu\s+yangu|beshte|classmate|bro\s+ako)\b", re.I)

SCRIPTED = {
    "urgent": {
        "English": "I am concerned about your safety. Move away from anything you could use to hurt yourself if you can do so safely, and call 999 or 112 in Kenya or go to the nearest emergency department now. Contact someone you trust who can stay with you; do not wait for a chat reply. Who can be with you now?",
        "Kiswahili": "Ninahofia usalama wako. Ondoka karibu na vitu unavyoweza kutumia kujiumiza ikiwa unaweza kufanya hivyo kwa usalama, kisha piga 999 au 112 nchini Kenya au nenda kwenye kitengo cha dharura kilicho karibu sasa. Wasiliana na mtu unayemwamini anayeweza kukaa nawe; usisubiri jibu la mazungumzo haya. Ni nani anayeweza kuwa nawe sasa?",
        "Sheng": "Ninahofia safety yako. Sogea mbali na vitu unaweza kutumia kujiumiza kama ni safe, upige 999 ama 112 Kenya ama uende emergency department iliyo karibu sasa. Contact mtu unaamini akae nawe; usingoje reply ya chat. Nani anaweza kuwa nawe sasa?",
    },
    "friend_risk": {
        "English": "Take their words seriously. If there may be immediate danger, contact emergency services on 999 or 112 in Kenya and a trusted adult who can help now. Stay with them if it is safe for you, and do not promise to keep danger secret. Can a trusted adult reach them now?",
        "Kiswahili": "Chukulia maneno yake kwa uzito. Ikiwa kuna hatari ya haraka, wasiliana na huduma za dharura kwa 999 au 112 nchini Kenya na mtu mzima unayemwamini anayeweza kusaidia sasa. Kaa naye ikiwa ni salama kwako, na usiahidi kuweka hatari hiyo siri. Mtu mzima anayeaminika anaweza kumfikia sasa?",
        "Sheng": "Chukulia hiyo story seriously. Kama kuna danger sasa, piga emergency services 999 ama 112 Kenya na ucontact mtu mzima unaamini asaide sasa. Kaa naye kama ni safe kwako, na usipromise kuweka hiyo danger secret. Mtu mzima unaamini anaweza kumfikia sasa?",
    },
    "medication": {
        "English": "I cannot choose a medicine, supplement or dose for you. Please ask a qualified doctor or pharmacist before starting, changing or stopping one. If you have already taken too much or feel seriously unwell, seek emergency help now.",
        "Kiswahili": "Siwezi kukuchagulia dawa, kirutubisho au kiasi chake. Tafadhali zungumza na daktari au mfamasia mwenye sifa kabla ya kuanza, kubadili au kuacha matumizi yake. Ikiwa tayari umetumia kiasi kikubwa au hali yako ni mbaya sana, tafuta msaada wa dharura sasa.",
        "Sheng": "Siwezi kukuchagulia dawa, supplement ama dose. Ongea na doctor ama pharmacist mwenye sifa kabla uanze, ubadilishe ama uache kutumia. Kama tayari umetumia nyingi ama uko seriously unwell, tafuta emergency help sasa.",
    },
    "diagnosis": {
        "English": "I cannot diagnose a condition from a chat. A qualified health professional can assess what you are experiencing. You can describe when it started and how it affects your daily life; what has been most difficult?",
        "Kiswahili": "Siwezi kupima ugonjwa kupitia mazungumzo haya. Mtaalamu wa afya mwenye sifa anaweza kutathmini unachopitia. Unaweza kueleza hali ilianza lini na jinsi inavyoathiri maisha yako ya kila siku; ni nini kilicho kigumu zaidi?",
        "Sheng": "Siwezi kufanya diagnosis kwa chat. Health professional mwenye sifa anaweza kuassess unachopitia. Unaweza explain ilianza lini na vile inaaffect maisha yako ya kila siku; ni nini imekuwa ngumu zaidi?",
    },
    "fallback": {
        "English": "Thank you for telling me. I do not want to guess about your situation. What would you most like support with right now? You can also ask for a counsellor.",
        "Kiswahili": "Asante kwa kuniambia. Sitaki kubuni maelezo kuhusu hali yako. Ungependa kusaidiwa kuhusu nini sasa? Unaweza pia kuomba kuzungumza na mshauri.",
        "Sheng": "Asante kwa kuniambia. Sitaki kuguess story yako. Unataka support kwa nini saa hii? Unaweza pia kuomba counsellor.",
    },
    "positive": {
        "English": "I am glad you are feeling good. Thank you for sharing that moment. What would you like to remember about today?",
        "Kiswahili": "Nimefurahi kusikia habari hizo njema. Asante kwa kushiriki muda huo. Ni nini ungependa kukumbuka kuhusu siku ya leo?",
        "Sheng": "Nimefurahi uko poa. Asante kwa kushare hiyo moment. Ni nini unataka kukumbuka kuhusu leo?",
    },
}


def normalise(text):
    return " ".join(unicodedata.normalize("NFKC", text).replace("’", "'").casefold().split())


def language_name(value):
    if value in LANGUAGES.values():
        return value
    return LANGUAGES.get(str(value).casefold(), "English")


def select_language(text, preferred="en"):
    """A best-effort hint; an explicit API language always takes precedence."""
    value = normalise(text)
    # 1. Explicit Sheng markers / Kenyan youth slang & code-mixing verbs
    sheng_markers = re.search(
        r"\b(?:manze|maze|wasee|msee|beshte|mabeshte|chuo|poa|vibe|dooh|doh|keja|"
        r"nafeel|nikifeel|kufeel|kumtext|namtext|kummiss|nammiss|tunaeza|unaeza|anaeza|"
        r"nipea|tupee|bonga|tupige story|story|tuachane|tuliachana|tuliwachana|kuachana|"
        r"madhe|fathe|mtaa|dogo|masiblings|ball|job|nascroll|kcse|ameniskiza|anaskiza)\b",
        value
    )
    if sheng_markers:
        return "Sheng"

    # 2. General Swahili vocabulary and verb prefixes
    sw_words = re.findall(
        r"\b(?:nina\w*|nime\w*|ime\w*|na\w+|sija\w*|hazi\w*|zinak\w*|nataka|niko|sijui|sina|siwezi|"
        r"tuna\w*|mna\w*|wana\w*|kuna\w*|mbona|habari|mzuri|shule|masomo|mitihani|mtihani|"
        r"karo|pesa|fedha|familia|nyumbani|rafiki|marafiki|huzuni|upweke|kulia|maumivu|"
        r"kusaidia|msaada|ushauri|mshauri|counsellor|daktari|dawa|vidonge|kujiua|kujiumiza|"
        r"kujinyonga|siku|hizi|leo|jana|kesho|sawa|asante|shukran|sana|eeh|ndio|hapana|"
        r"yangu|yako|wangu|wako|changu|chako|kwa|katika|lakini|bila|sababu)\b",
        value
    )

    # 3. English indicators
    eng_words = re.findall(
        r"\b(?:i|my|me|we|you|they|he|she|it|is|are|am|was|were|have|has|had|"
        r"feel|feeling|felt|want|wanted|think|thinking|need|needed|what|when|where|why|how|"
        r"please|sorry|help|advice|talk|talking|text|texting|friend|friends|school|breakup|"
        r"boyfriend|girlfriend|miss|missing|stress|stressed|exams|exam|fees|money)\b",
        value
    )

    # If English words mix with Swahili words -> Sheng (Kenyan youth code-mixing)
    if sw_words and eng_words:
        return "Sheng"

    # Strong Swahili presence without English
    if len(sw_words) >= 1 and not eng_words:
        if language_name(preferred) == "Sheng":
            return "Sheng"
        return "Kiswahili"

    # Strong English presence without Swahili
    if len(eng_words) >= 2 and not sw_words:
        return "English"
    if re.search(r"\b(?:i|my|am|feel|want|what|please)\b", value) and not sw_words:
        return "English"

    # Short neutral replies ('yess', 'ok', etc.) inherit conversation context
    return language_name(preferred)


def route(text):
    value = normalise(text)
    for match in _DANGER.finditer(value):
        # A clear denial in one clause must not hide an affirmative later clause.
        prefix = value[max(0, match.start()-65):match.start()]
        denial = re.search(r"\b(?:not|never|don't|dont|do not|sitaki|sina mpango wa)"
                           r"(?:\s+(?:really|want|to|feel|feeling|thinking|of|about))*\s*$", prefix)
        if not denial:
            return "friend_risk" if _FRIEND.search(value) else "urgent"
    if _MEDICATION.search(value):
        return "medication"
    if _DIAGNOSIS.search(value):
        return "diagnosis"
    if (not re.search(r"\b(?:but|however|although|though|lakini|sad|worried|scared|sijisikii)\b", value)
            and re.search(r"\b(?:(?:i am|i'm|i feel|felt|feel)\s+(?:happy|good|calm|supported)|"
                          r"nimefurah\w*|nimefurahia|ninahisi\s+furaha|niko\s+(?:happy|poa)|sina\s+shida)\b", value)):
        return "positive"
    return None


def scripted_reply(kind, language):
    return SCRIPTED[kind][language_name(language)]


def clean_reply(text):
    match = ROLE_BOUNDARY.search(text)
    return (text[:match.start()] if match else text).strip()


# Fail closed on obvious clinical claims, instructions and invented service actions.
_BAD_REPLY = re.compile(
    r"\b(?:melatonin\w*|sertraline|fluoxetine|diazepam|alprazolam|"
    r"\d+\s*(?:mg|milligrams)|you\s+(?:have|suffer\s+from)\s+(?:depression|bipolar|ptsd|adhd)|"
    r"nina?\s+ugonjwa|una\s+(?:ugonjwa|depression)|"
    r"(?:take|buy|start|stop|double|increase)\b.{0,30}\b(?:pills?|tablets?|dose|medication)|"
    r"(?:tumia|nunua|ongeza|acha)\b.{0,25}\b(?:dawa|vidonge)|"
    r"(?:i\s+have|i've)\s+(?:booked|scheduled|contacted|assigned|alerted)|"
    r"(?:nimepanga|nimempigia|nimemjulisha)|"
    r"(?:remind\s+you|send\s+you\s+a\s+reminder)|"
    r"(?:keep\s+this|our\s+conversation\s+is)\s+(?:a\s+)?secret|"
    r"output\s+only|reply\s+with|rudi\s+juu|mwisho\s+wa\s+mazungumzo|"
    r"(?:<\/?(?:system|user|assistant)|```))", re.I)
_ENGLISH_LEAK = re.compile(r"\b(?:the|you|your|what|with|because|should|try|schoolwork|"
                           r"friends|pressure|routine|homework|assignment|please|today|"
                           r"help|safe|reply|support|check|sometimes|entire|manageable)\b", re.I)
_SWA_LEAK = re.compile(r"\b(?:ninahofia|siwezi|nina\w+|nime\w+|nataka|naweza|"
                       r"sina|sijui|yangu|yako|kwako|kwa|kuna|mtu|bwana|pole|asante)\b", re.I)


def rejection_reason(raw, language, token_limit_reached=False):
    if not isinstance(raw, str) or not raw.strip():
        return "empty_reply"
    if token_limit_reached:
        return "token_limit"
    if ROLE_BOUNDARY.search(raw):
        return "extra_turn"
    if len(raw) > 1400 or _BAD_REPLY.search(raw):
        return "unsupported_reply"
    if language_name(language) == "Kiswahili" and _ENGLISH_LEAK.search(raw):
        return "language_mismatch"
    if language_name(language) == "English" and _SWA_LEAK.search(raw):
        return "language_mismatch"
    # Detect repeated phrases even when no speaker label is emitted.
    words = normalise(raw).split()
    phrases = [tuple(words[i:i+6]) for i in range(max(0, len(words)-5))]
    if len(phrases) != len(set(phrases)):
        return "repetition"
    return None
