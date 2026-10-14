"""Proposed multilingual review phrases, not a validated clinical instrument.

Categories are informed by NIMH warning-sign guidance. Translations and Sheng
phrases need local counsellor/native-language review before live use.
Tier 1 requests immediate human review; Tier 2 supplies one supporting layer.
"""
GROUPS = [
    ("Immediate safety", 1, {
        "English": ["want to kill myself", "want to end my life", "thinking about suicide",
            "want to hurt myself", "want to die", "plan to kill myself", "might hurt myself",
            "might harm myself", "cannot keep myself safe", "don't want to live",
            "do not want to live", "no reason to live", "have hurt myself", "have taken too many tablets"],
        "Kiswahili": ["nataka kujiua", "nafikiria kujiua", "nataka kujidhuru", "nataka kufa",
            "sitaki kuishi", "nataka kujiumiza", "nitajiumiza", "nitajiua", "nitajinyonga",
            "nimejiumiza", "sina sababu ya kuishi", "nataka kumaliza maisha yangu", "nimechoka kuishi"],
        "Sheng / code-switched": ["nataka kujimaliza", "nitajimaliza", "nataka kuend life yangu",
            "nafeel nijiumize", "siwezi keep myself safe"],
    }),
    ("Hopelessness / feeling trapped", 2, {
        "English": ["feel hopeless", "feel trapped", "nothing will ever get better"],
        "Kiswahili": ["sina matumaini", "najihisi nimekwama", "sioni njia ya kutoka"],
        "Sheng / code-switched": ["life imenishinda", "sioni hope", "nimekwama na sina way out"],
    }),
    ("Self-worth / shame", 2, {
        "English": ["feel worthless", "feel like a burden", "hate myself"],
        "Kiswahili": ["najiona sina thamani", "najiona mzigo", "najichukia"],
        "Sheng / code-switched": ["nafeel sina value", "nafeel niko burden", "najihate"],
    }),
    ("Isolation / withdrawal", 2, {
        "English": ["feel completely alone", "nobody cares about me", "avoiding all my friends"],
        "Kiswahili": ["najihisi mpweke", "hakuna anayenijali", "nimejitenga na marafiki"],
        "Sheng / code-switched": ["nafeel niko solo kabisa", "hakuna mtu ananijali", "nimecut off mabeshte"],
    }),
    ("Bullying / harassment", 2, {
        "English": ["being bullied", "being humiliated", "being threatened"],
        "Kiswahili": ["wananinyanyasa shuleni", "wananidhalilisha", "wananitishia"],
        "Sheng / code-switched": ["nabullyiwa shule", "wananidiss kila siku", "wasee wananitishia"],
    }),
    ("Safety at home", 2, {
        "English": ["being hurt at home", "afraid to go home"],
        "Kiswahili": ["ninaumizwa nyumbani", "naogopa kurudi nyumbani"],
        "Sheng / code-switched": ["naogopa kurudi home", "wananiumiza home"],
    }),
    ("Sleep / daily functioning", 2, {
        "English": ["cannot sleep at night", "lost my appetite", "cannot get out of bed"],
        "Kiswahili": ["siwezi kulala usiku", "nimepoteza hamu ya kula", "siwezi kuamka kitandani"],
        "Sheng / code-switched": ["silali usiku", "sina appetite", "siwezi kutoka bed"],
    }),
    ("School / financial pressure", 2, {
        "English": ["cannot cope with school", "cannot afford food", "pressure is too much"],
        "Kiswahili": ["masomo yamenilemea", "sina pesa za chakula", "mawazo yamenilemea"],
        "Sheng / code-switched": ["school imenilemea", "sina pesa ya food", "niko down sana"],
    }),
    ("Substance concerns", 2, {
        "English": ["using drugs to cope", "drinking more to cope"],
        "Kiswahili": ["natumia dawa za kulevya kupunguza mawazo", "nakunywa pombe kupunguza mawazo"],
        "Sheng / code-switched": ["natumia drugs juu ya pressure", "nakunywa pombe juu ya stress"],
    }),
    ("Loss / emotional distress", 2, {
        "English": ["cannot cope with the loss", "emotional pain is unbearable"],
        "Kiswahili": ["nimeshindwa kukabiliana na msiba", "maumivu ya hisia yamenizidi"],
        "Sheng / code-switched": ["hii loss imenilemea", "pain ya feelings imenizidi"],
    }),
]
STARTER_KEYWORDS = [(term, language, tier, category)
                    for category, tier, languages in GROUPS
                    for language, terms in languages.items() for term in terms]
