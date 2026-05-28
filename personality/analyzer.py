from dataclasses import dataclass
import re

EMOJI_VALENCE = {
    "❤": 0.9, "🔥": 0.3, "😊": 0.7, "😢": -0.6, "😡": -0.8,
    "🥰": 0.9, "😘": 0.9, "💔": -0.7, "😭": -0.5, "😤": -0.6,
    "👍": 0.5, "💕": 0.9, "✨": 0.5, "😏": 0.2, "🤗": 0.7,
}

LEXICON: list[tuple[re.Pattern, str, float, float]] = [
    (re.compile(r"\bsayang\b"), "intimate", 0.8, 0.7),
    (re.compile(r"\bcinta\b"), "intimate", 0.9, 0.8),
    (re.compile(r"\brindu\b"), "intimate", 0.7, 0.6),
    (re.compile(r"\bkangen\b"), "intimate", 0.6, 0.5),
    (re.compile(r"\bpeluk\b"), "intimate", 0.8, 0.4),
    (re.compile(r"\bmesra\b"), "intimate", 0.8, 0.6),
    (re.compile(r"\bbersama\b"), "intimate", 0.6, 0.3),
    (re.compile(r"\bdekat\b"), "intimate", 0.5, 0.3),
    (re.compile(r"\bhayat\b"), "intimate", 0.7, 0.5),
    (re.compile(r"\bbutuh\b"), "intimate", 0.5, 0.6),
    (re.compile(r"\bmakasih\b"), "positive", 0.6, 0.3),
    (re.compile(r"\bterima kasih\b"), "positive", 0.6, 0.2),
    (re.compile(r"\bsuka\b"), "positive", 0.6, 0.4),
    (re.compile(r"\bsenang\b"), "positive", 0.7, 0.5),
    (re.compile(r"\bbaik\b"), "positive", 0.5, 0.3),
    (re.compile(r"\bbangga\b"), "positive", 0.7, 0.6),
    (re.compile(r"\bsemangat\b"), "positive", 0.7, 0.6),
    (re.compile(r"\bhebat\b"), "positive", 0.6, 0.4),
    (re.compile(r"\bkeren\b"), "positive", 0.6, 0.4),
    (re.compile(r"\bpintar\b"), "positive", 0.5, 0.3),
    (re.compile(r"\bcantik\b"), "positive", 0.7, 0.4),
    (re.compile(r"\bganteng\b"), "positive", 0.7, 0.4),
    (re.compile(r"\blucu\b"), "positive", 0.6, 0.5),
    (re.compile(r"\bbahagia\b"), "positive", 0.8, 0.6),
    (re.compile(r"\btenang\b"), "positive", 0.4, 0.2),
    (re.compile(r"\bnyaman\b"), "positive", 0.5, 0.3),
    (re.compile(r"\bindah\b"), "positive", 0.5, 0.3),
    (re.compile(r"\bbersyukur\b"), "positive", 0.6, 0.3),
    (re.compile(r"\blega\b"), "positive", 0.5, 0.3),
    (re.compile(r"\bsenyum\b"), "positive", 0.5, 0.3),
    (re.compile(r"\btertawa\b"), "positive", 0.6, 0.6),
    (re.compile(r"\boptimis\b"), "positive", 0.5, 0.4),
    (re.compile(r"\bhappy\b"), "positive", 0.7, 0.6),
    (re.compile(r"\bkenapa\b"), "negative", -0.4, 0.5),
    (re.compile(r"\bkesel\b"), "negative", -0.7, 0.7),
    (re.compile(r"\bmarah\b"), "negative", -0.9, 0.9),
    (re.compile(r"\bbenci\b"), "negative", -0.8, 0.8),
    (re.compile(r"\bcapek\b"), "negative", -0.4, 0.3),
    (re.compile(r"\bsedih\b"), "negative", -0.7, 0.5),
    (re.compile(r"\bkecewa\b"), "negative", -0.6, 0.6),
    (re.compile(r"\bkesepian\b"), "negative", -0.6, 0.5),
    (re.compile(r"\bsakit hati\b"), "negative", -0.7, 0.7),
    (re.compile(r"\bfrustasi\b"), "negative", -0.7, 0.8),
    (re.compile(r"\bbosan\b"), "negative", -0.4, 0.3),
    (re.compile(r"\bpusing\b"), "negative", -0.4, 0.5),
    (re.compile(r"\blelah\b"), "negative", -0.4, 0.3),
    (re.compile(r"\bbingung\b"), "negative", -0.3, 0.5),
    (re.compile(r"\btakut\b"), "negative", -0.6, 0.7),
    (re.compile(r"\bcemas\b"), "negative", -0.5, 0.7),
    (re.compile(r"\bkhawatir\b"), "negative", -0.5, 0.6),
    (re.compile(r"\bsakit\b"), "negative", -0.5, 0.5),
    (re.compile(r"\bjengkel\b"), "negative", -0.6, 0.6),
    (re.compile(r"\bmuak\b"), "negative", -0.6, 0.6),
    (re.compile(r"\bsebel\b"), "negative", -0.5, 0.5),
    (re.compile(r"\bbete\b"), "negative", -0.5, 0.5),
    (re.compile(r"\bgalau\b"), "negative", -0.5, 0.5),
    (re.compile(r"\bdown\b"), "negative", -0.4, 0.3),
    (re.compile(r"\bminder\b"), "negative", -0.4, 0.4),
    (re.compile(r"\binsecure\b"), "negative", -0.5, 0.5),
    (re.compile(r"\biri\b"), "negative", -0.4, 0.4),
    (re.compile(r"\bdengki\b"), "negative", -0.5, 0.5),
    (re.compile(r"\bpergi\b.*\bsaja\b"), "negative", -0.4, 0.4),  # "pergi saja" spesifik
    (re.compile(r"\btinggal\b"), "negative", -0.3, 0.3),
    (re.compile(r"\bpergilah\b"), "negative", -0.5, 0.5),
    (re.compile(r"\bgak sayang\b"), "negative", -0.7, 0.7),
    (re.compile(r"\bga sayang\b"), "negative", -0.7, 0.7),
    (re.compile(r"\bnggak sayang\b"), "negative", -0.7, 0.7),
    (re.compile(r"\bga suka\b"), "negative", -0.5, 0.5),
    (re.compile(r"\bgak suka\b"), "negative", -0.5, 0.5),
    (re.compile(r"\btidak suka\b"), "negative", -0.5, 0.5),
    (re.compile(r"\bgak mau\b"), "negative", -0.4, 0.5),
    (re.compile(r"\bga mau\b"), "negative", -0.4, 0.5),
    (re.compile(r"\bnggak mau\b"), "negative", -0.4, 0.5),
    (re.compile(r"\bgak pernah\b"), "negative", -0.3, 0.4),
    (re.compile(r"\bga pernah\b"), "negative", -0.3, 0.4),
    (re.compile(r"\bgak peduli\b"), "negative", -0.5, 0.5),
    (re.compile(r"\bga peduli\b"), "negative", -0.5, 0.5),
]

INTENSIFIERS = [
    (re.compile(r"!"), 0.2),
    (re.compile(r"\?\?"), 0.2),
    (re.compile(r"[A-Z]{4,}"), 0.3),
]

# Kata negasi eksplisit — bukan kata negatif, tapi kata yang membalik makna
_NEGATION_WORDS = re.compile(
    r"\b(tidak|ga|gak|nggak|enggak|bukan|tak|jangan|belum|kurang)\b"
)


@dataclass
class EmotionAnalysis:
    emotion: str = "neutral"
    valence: float = 0.0
    arousal: float = 0.0
    confidence: float = 0.0


def _find_emojis(text: str) -> list[str]:
    emoji_pattern = re.compile("[" + "".join(EMOJI_VALENCE.keys()) + "]")
    return emoji_pattern.findall(text)


def analyze(text: str) -> EmotionAnalysis:
    lower = text.lower().strip()
    if not lower:
        return EmotionAnalysis()

    words = lower.split()
    matched_valences: list[float] = []
    matched_arousals: list[float] = []
    matched_emotions: list[str] = []

    for pattern, emotion, val, aro in LEXICON:
        match = pattern.search(lower)
        if match:
            # Cek apakah pattern ini sendiri merupakan pattern negasi eksplisit
            is_explicit_neg = any(x in pattern.pattern for x in ["ga", "gak", "nggak", "tidak", "bukan", "tak"])
            
            # Cek apakah ada kata negasi yang mendahului match ini dalam kalimat (jarak 3 kata)
            pre_text = lower[:match.start()].strip()
            has_pre_negation = False
            if pre_text:
                pre_words = pre_text.split()
                recent_pre_words = pre_words[-3:]
                has_pre_negation = any(_NEGATION_WORDS.search(w) for w in recent_pre_words)
            
            if has_pre_negation and not is_explicit_neg:
                # Balikkan sentimen jika didahului negasi
                val = -val * 0.8
                if emotion in ("positive", "intimate"):
                    emotion = "negative"
                elif emotion == "negative":
                    emotion = "positive"

            matched_valences.append(val)
            matched_arousals.append(aro)
            matched_emotions.append(emotion)

    emojis = _find_emojis(text)
    for em in emojis:
        v = EMOJI_VALENCE.get(em, 0.0)
        matched_valences.append(v)
        matched_arousals.append(0.6)
        matched_emotions.append("positive" if v > 0 else "negative" if v < 0 else "neutral")

    arousal_boost = 0.0
    for pattern, boost in INTENSIFIERS:
        if pattern.search(text):
            arousal_boost += boost

    # Cek kata negasi eksplisit (tidak/ga/gak/nggak/...) — bukan kata negatif
    has_negation = bool(_NEGATION_WORDS.search(lower))

    if matched_valences:
        avg_val = sum(matched_valences) / len(matched_valences)
        avg_aro = sum(matched_arousals) / len(matched_arousals) + arousal_boost
        avg_aro = min(1.0, avg_aro)

        emotion_counts: dict[str, int] = {}
        for e in matched_emotions:
            emotion_counts[e] = emotion_counts.get(e, 0) + 1

        if has_negation:
            neg_count = emotion_counts.get("negative", 0)
            non_neg_count = len(matched_emotions) - neg_count
            if neg_count >= non_neg_count:
                dominant = "negative"
            else:
                dominant = max(emotion_counts, key=emotion_counts.get)
        else:
            dominant = max(emotion_counts, key=emotion_counts.get)

        confidence = min(1.0, len(matched_valences) / max(len(words), 1) * 2)
        return EmotionAnalysis(emotion=dominant, valence=avg_val, arousal=avg_aro, confidence=confidence)

    return EmotionAnalysis(emotion="neutral", valence=0.0, arousal=0.1, confidence=0.2)
