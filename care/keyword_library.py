"""Proposed multilingual review phrases, not a validated clinical instrument.

Categories are informed by NIMH warning-sign guidance and refined with authentic
Nairobi informal settlement youth idioms (Sheng / code-switched).
Tier 1 requests immediate human review; Tier 2 supplies one supporting layer.
"""
GROUPS = [
    ("Immediate safety", 1, {
        "English": [
            "want to kill myself", "want to end my life", "thinking about suicide",
            "want to hurt myself", "want to die", "plan to kill myself", "might hurt myself",
            "might harm myself", "cannot keep myself safe", "don't want to live",
            "do not want to live", "no reason to live", "have hurt myself", "have taken too many tablets"
        ],
        "Kiswahili": [
            "nataka kujiua", "nafikiria kujiua", "nataka kujidhuru", "nataka kufa",
            "sitaki kuishi", "nataka kujiumiza", "nitajiumiza", "nitajiua", "nitajinyonga",
            "nimejiumiza", "sina sababu ya kuishi", "nataka kumaliza maisha yangu", "nimechoka kuishi"
        ],
        "Sheng / code-switched": [
            "nataka kujimaliza", "nitajimaliza", "nataka kuend life yangu",
            "nafeel nijiumize", "siwezi keep myself safe", "nataka kujitoa",
            "kufunga hii chapter", "bora kukuwa dead", "kujirusha", "kudedi",
            "kujihepa", "bora nikafie mbali", "heri ningededi", "nataka kudedi"
        ],
    }),
    ("Hopelessness / feeling trapped", 2, {
        "English": [
            "feel hopeless", "feel trapped", "nothing will ever get better",
            "have no future", "see no way out"
        ],
        "Kiswahili": [
            "sina matumaini", "najihisi nimekwama", "sioni njia ya kutoka",
            "maisha yamenishinda", "nimekata tamaa"
        ],
        "Sheng / code-switched": [
            "life imenishinda", "sioni hope", "nimekwama na sina way out",
            "nimeparara mbaya", "niko kwa corner mbaya", "life imeniweza",
            "roho inazama", "sioni mbele", "nimefika mwisho", "kichwa inalipuka",
            "hapa sina say", "sina matumaini tena"
        ],
    }),
    ("Self-worth / shame", 2, {
        "English": [
            "feel worthless", "feel like a burden", "hate myself"
        ],
        "Kiswahili": [
            "najiona sina thamani", "najiona mzigo", "najichukia"
        ],
        "Sheng / code-switched": [
            "nafeel sina value", "nafeel niko burden", "najihate",
            "najiona useless", "mimi ni mzigo tu", "hakuna kitu ninaweza", "najiona bure kabisa"
        ],
    }),
    ("Isolation / withdrawal", 2, {
        "English": [
            "feel completely alone", "nobody cares about me", "avoiding all my friends",
            "have no one to talk to", "cut off everyone"
        ],
        "Kiswahili": [
            "najihisi mpweke", "hakuna anayenijali", "nimejitenga na marafiki",
            "sina wa kuongea naye", "nimebaki peke yangu"
        ],
        "Sheng / code-switched": [
            "nafeel niko solo kabisa", "hakuna mtu ananijali", "nimecut off mabeshte",
            "wasee wamenikatia", "wasee wananihepa", "sinanga mtu wa kubonga naye",
            "nimejifungia tu kwa hao", "nimebaki solo"
        ],
    }),
    ("Bullying / harassment", 2, {
        "English": [
            "being bullied", "being humiliated", "being threatened",
            "getting beaten up", "being blackmailed"
        ],
        "Kiswahili": [
            "wananinyanyasa shuleni", "wananidhalilisha", "wananitishia",
            "wananionea", "wananipiga shuleni"
        ],
        "Sheng / code-switched": [
            "nabullyiwa shule", "wananidiss kila siku", "wasee wananitishia",
            "wananionea kwa mtaa", "wananiletea fujo", "wasee wananiandama"
        ],
    }),
    ("Safety at home", 2, {
        "English": [
            "being hurt at home", "afraid to go home", "violence at home",
            "kicked out of the house", "nowhere to sleep tonight"
        ],
        "Kiswahili": [
            "ninaumizwa nyumbani", "naogopa kurudi nyumbani", "kufukuzwa nyumbani",
            "kuna vurugu nyumbani", "sina mahali pa kulala leo"
        ],
        "Sheng / code-switched": [
            "naogopa kurudi home", "wananiumiza home", "nimetupwa nje ya hao",
            "kuna vita mob kwa hao", "mbuyu ananichapa bila reason", "sina place ya kusleep"
        ],
    }),
    ("Sleep / daily functioning", 2, {
        "English": [
            "cannot sleep at night", "lost my appetite", "cannot get out of bed",
            "exhausted all the time", "have no energy for anything"
        ],
        "Kiswahili": [
            "siwezi kulala usiku", "nimepoteza hamu ya kula", "siwezi kuamka kitandani",
            "nachoka kila wakati", "sina nguvu ya kufanya chochote"
        ],
        "Sheng / code-switched": [
            "silali usiku", "sina appetite", "siwezi kutoka bed",
            "usingizi imekataa kabisa", "nimeishiwa na energy", "sina moro ya kuamka"
        ],
    }),
    ("School / financial pressure", 2, {
        "English": [
            "cannot cope with school", "cannot afford food", "pressure is too much",
            "chased home for fees", "failing in school"
        ],
        "Kiswahili": [
            "masomo yamenilemea", "sina pesa za chakula", "mawazo yamenilemea",
            "nimefukuzwa karo", "sina pesa hata kidogo"
        ],
        "Sheng / code-switched": [
            "school imenilemea", "sina pesa ya food", "niko down sana",
            "nimekosa doh kabisa", "mfuko imekauka", "stress za pesa zimenimaliza", "njaa inaniua",
            "nimerudishwa home juu ya fees", "hustle imekwama kabisa"
        ],
    }),
    ("Substance concerns", 2, {
        "English": [
            "using drugs to cope", "drinking more to cope", "smoking weed to forget",
            "drinking to feel numb"
        ],
        "Kiswahili": [
            "natumia dawa za kulevya kupunguza mawazo", "nakunywa pombe kupunguza mawazo",
            "nakunywa nilewe nisifikirie"
        ],
        "Sheng / code-switched": [
            "natumia drugs juu ya pressure", "nakunywa pombe juu ya stress",
            "nachoma tu nisaulike", "napiga puff ndio nikalm down",
            "nachana muguka nisisikie mawazo", "bangi ndio inanisaidia kuhepa stress"
        ],
    }),
    ("Loss / emotional distress", 2, {
        "English": [
            "cannot cope with the loss", "emotional pain is unbearable", "grieving and broken",
            "feel numb inside", "heart is heavy"
        ],
        "Kiswahili": [
            "nimeshindwa kukabiliana na msiba", "maumivu ya hisia yamenizidi",
            "nina huzuni kubwa", "roho inaniuma sana", "nimevunjika moyo"
        ],
        "Sheng / code-switched": [
            "hii loss imenilemea", "pain ya feelings imenizidi",
            "nimechizi", "kuchizi na mawazo", "manze niko tight", "nimededi ndani",
            "pressure inanikill", "roho inachoma mbaya", "kichwa inanigonga mbaya"
        ],
    }),
]
STARTER_KEYWORDS = [(term, language, tier, category)
                    for category, tier, languages in GROUPS
                    for language, terms in languages.items() for term in terms]
