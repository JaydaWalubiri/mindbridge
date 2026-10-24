"""Narrow factual support intents; these replies are scripted, not model output.

Only explicit first-person arrival states and completed schedule changes qualify.
Risk routing takes precedence at both callers. This is not a general parser.
"""
import re
from dataclasses import dataclass
from .response_policy import language_name, normalise


@dataclass(frozen=True)
class ContextSupport:
    intent: str
    reply: str


_ARRIVED = re.compile(r"\b(?:nime(?:sha)?(?:fika|wasili|ingia)|nilifika|niliwasili|niliingia|"
    r"nimechelewa\s+kufika|i\s+(?:(?:have|have already|already)\s+)?arrived|i(?:'ve| have)\s+(?:already\s+)?arrived)\b")
_LATE = re.compile(r"\b(?:late|kuchelewa|nimechelewa|nilichelewa|chelewa)\b")
_FUTURE = re.compile(r"\b(?:nita(?:fika|chelewa|wasili|ingia)|nitakuwa\s+late|"
    r"i(?:'ll| will)\s+(?:arrive\s+late|be\s+late)|i\s+expect\s+to\s+(?:arrive\s+late|be\s+late)|"
    r"i\s+am\b.{0,65}\band\s+will\s+(?:arrive\s+late|be\s+late))\b")
_NOT_LATE = re.compile(r"\b(?:sijachelewa(?:\s+bado)?|sijafika\s+late|"
    r"i\s+(?:am\s+not|have\s+not|haven't)\s+(?:been\s+)?late(?:\s+yet)?)\b")
_ON_TIME = re.compile(r"\b(?:on\s+time|kwa\s+(?:time|wakati)|mapema|early)\b")
_FORGOT = re.compile(r"\b(?:n(?:ika|ili|ime)(?:sahau)|i\s+(?:forgot|have\s+forgotten)|i\s+left\b.{0,35}\bat\s+home)\b")
_RESCHEDULED = re.compile(r"\b(?:ime(?:ahirishwa|hamishwa|hamisha|push)|"
    r"(?:was|has\s+been|is)\s+(?:postponed|rescheduled)|(?:organiser|organizer|club)\s+(?:has\s+)?(?:postponed|rescheduled))\b")
_SCHEDULE = re.compile(r"\b(?:practice|training|rehearsal|meeting|screening|film\s+club|event|lesson|"
    r"workshop|warsha|mazoezi|mkutano|tukio|somo|choir)\b")
_REPRIMAND = re.compile(r"\b(?:amenifokea|alinifokea|amenikemea|alinikemea|ameniblast|aliniblast|"
    r"(?:has\s+)?shouted\s+at\s+me|(?:has\s+)?scolded\s+me)\b")
_QUOTED = re.compile(r"[\"“”]|\b(?:anasema|alisema|walisema|beshte\s+amesema|my\s+friend\s+says|someone\s+said)\b")
_NEGATED = re.compile(r"\b(?:si\s+kwamba|sijasema|siyo\s+kwamba|not\s+that|never\s+said|didn't\s+say)\b")
_CLAUSE = re.compile(r"[,.!?;]|\b(?:lakini|but|however|ingawa|although)\b")
_ITEM = {
    "English": {"id": "your ID", "kitambulisho": "your ID", "boots": "your boots", "buti": "your boots", "viatu": "your shoes", "notebook": "your notebook", "daftari": "your notebook", "notes": "your notes"},
    "Kiswahili": {"id": "kitambulisho", "kitambulisho": "kitambulisho", "boots": "viatu", "buti": "viatu", "viatu": "viatu", "notebook": "daftari", "daftari": "daftari", "notes": "maelezo"},
    "Sheng": {"id": "ID", "kitambulisho": "ID", "boots": "boots", "buti": "boots", "viatu": "viatu", "notebook": "notebook", "daftari": "daftari", "notes": "notes"},
}
_REPLIES = {
    "arrived_late": {
        "English": "You have arrived late, and that can feel stressful. You could briefly explain what delayed you and ask how to join in.",
        "Kiswahili": "Umeshafika kwa kuchelewa, na hilo linaweza kuleta wasiwasi. Unaweza kueleza kwa ufupi kilichokuchelewesha na kuuliza jinsi ya kujiunga.",
        "Sheng": "Umeshafika late, na hiyo inaweza kuleta pressure. Unaweza explain kwa ufupi kilikuchelewesha, halafu ask vile utajoin.",
    },
    "arrived_after_delay": {
        "English": "You have arrived and described a transport delay. You could briefly explain what happened and ask how to join in.",
        "Kiswahili": "Umeshafika na umeeleza kuhusu kucheleweshwa kwa usafiri. Unaweza kueleza kwa ufupi kilichotokea na kuuliza jinsi ya kujiunga.",
        "Sheng": "Umeshafika, na umesema kuna kucheleweshwa. Unaweza explain kilihappen kwa ufupi, halafu ask vile utajoin.",
    },
    "arrived_reprimanded": {
        "English": "You have arrived late and someone has already shouted at you. When you feel ready, you could explain the delay in a private conversation.",
        "Kiswahili": "Umeshafika kwa kuchelewa na mtu tayari amekufokea. Ukijisikia tayari, unaweza kueleza kilichokuchelewesha kwa mazungumzo ya faragha.",
        "Sheng": "Umeshafika late na mtu ameshakufokea. Ukifeel ready, unaweza explain kilikuchelewesha kwa story ya private.",
    },
    "future_late": {
        "English": "You expect to arrive late. You could let the person expecting you know about the delay, giving an arrival time only if you know it.",
        "Kiswahili": "Unatarajia kufika kwa kuchelewa. Unaweza kumjulisha anayekusubiri kuhusu kucheleweshwa, ukisema muda wa kufika ikiwa unaujua.",
        "Sheng": "Unatarajia kufika late. Unaweza notify anayekungoja kuhusu delay, na umshow time ya kufika kama unaijua.",
    },
    "not_late_yet": {
        "English": "You have not been late; this is a worry about what might happen. You could plan when to leave and allow some extra time if possible.",
        "Kiswahili": "Bado hujachelewa; huu ni wasiwasi kuhusu kinachoweza kutokea. Unaweza kupanga muda wa kuondoka na kuongeza muda wa ziada ikiwezekana.",
        "Sheng": "Bado hujachelewa; unaworry kuhusu kitu kinaweza kuhappen. Unaweza plan time ya kutoka na ujipe time ya ziada ikiwezekana.",
    },
    "rescheduled": {
        "English": "The event has been moved to another time. You could confirm the new time and adjust your plans.",
        "Kiswahili": "Shughuli imehamishwa hadi wakati mwingine. Unaweza kuthibitisha muda mpya na kubadili mipango yako.",
        "Sheng": "Event imehamishwa kwa time ingine. Unaweza confirm time mpya halafu adjust plans zako.",
    },
    "arrived_after_worry": {
        "English": "You have now arrived. You could briefly explain what happened and ask how to join in, without guessing anyone's reaction.",
        "Kiswahili": "Sasa umeshafika. Unaweza kueleza kwa ufupi kilichotokea na kuuliza jinsi ya kujiunga bila kubuni itikio la mtu.",
        "Sheng": "Sasa umeshafika. Unaweza explain kilihappen kwa ufupi, halafu ask vile utajoin bila kuguess reaction ya mtu.",
    },
}


def _future_late(value):
    return any(_FUTURE.search(clause) and (_LATE.search(clause)
               or re.search(r"\bnitachelewa\b", clause)) for clause in _CLAUSE.split(value))


def context_support(text, language, history=()):
    """Return a labelled script for a clearly stated situation, otherwise None."""
    value = normalise(text)
    lang = language_name(language)
    if _QUOTED.search(value) or _NEGATED.search(value):
        return None
    if _ARRIVED.search(value) and _FUTURE.search(value):
        return None  # Multiple first-person arrival states need interpretation.
    punctual = any(_ARRIVED.search(clause) and _ON_TIME.search(clause) and not _LATE.search(clause)
                   for clause in _CLAUSE.split(value))
    if punctual and _FORGOT.search(value):
        item = next((mapped for word, mapped in _ITEM[lang].items()
                     if re.search(r"\b" + re.escape(word) + r"\b", value)),
                    {"English": "something", "Kiswahili": "kitu", "Sheng": "kitu"}[lang])
        reply = {
            "English": f"You arrived on time, but forgot {item}. You could explain what is missing and ask what options are available to continue.",
            "Kiswahili": f"Ulifika kwa wakati, lakini ulisahau {item}. Unaweza kueleza kilichokosekana na kuuliza njia nyingine inayowezekana ya kuendelea.",
            "Sheng": f"Ulifika on time, lakini ulisahau {item}. Unaweza explain kilimiss na ask kama kuna option ingine ya kuendelea.",
        }[lang]
        return ContextSupport("on_time_forgot", reply)
    if _RESCHEDULED.search(value) and _SCHEDULE.search(value):
        intent = "rescheduled"
    elif _future_late(value):
        intent = "future_late"
    elif _NOT_LATE.search(value) and re.search(r"\b(?:naogopa|nafeel|worry|worried|fear|scared|kesho|tomorrow)\b", value):
        intent = "not_late_yet"
    elif not punctual and not re.search(r"\b(?:bado\s+(?:niko|uko)\s+njiani|still\s+on\s+the\s+way)\b", value) and any(_ARRIVED.search(clause) and _LATE.search(clause)
                                           for clause in _CLAUSE.split(value)):
        intent = "arrived_reprimanded" if _REPRIMAND.search(value) else "arrived_late"
    elif (_ARRIVED.search(value) and not punctual
          and re.search(r"\b(?:bus|busi|mat|train|gari)\b.{0,40}\b(?:ilichelewa|imechelewa|was\s+delayed)\b", value)):
        intent = "arrived_after_delay"
    elif _ARRIVED.search(value) and not punctual and history:
        # A previous prediction does not prove the user actually arrived late.
        previous = next((normalise(turn.get("content", "")) for turn in reversed(history)
                         if isinstance(turn, dict) and turn.get("role") == "user"), "")
        if not _future_late(previous):
            return None
        intent = "arrived_after_worry"
    else:
        return None
    return ContextSupport(intent, _REPLIES[intent][lang])
