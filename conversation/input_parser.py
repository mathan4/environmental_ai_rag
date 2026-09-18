"""
Extracts structured fields from free-text user input. Deliberately simple
(regex/keyword based) -- good enough for the fields this system needs, and
transparent/debuggable rather than an opaque second LLM call just for extraction.
Structured JSON input bypasses this entirely (see core/engine.py).
"""
import re

# Ordered so more specific categories are checked before generic catch-alls --
# dict insertion order is preserved in Python 3.7+, and _match_keywords returns
# the first match, so "monoculture wheat" matches monoculture, not the generic
# "agriculture" bucket, even though both technically apply.
LAND_USE_KEYWORDS = {
    "monoculture": [
        "monoculture", "single crop", "single-crop", "one crop", "mono-crop", "monocrop",
        "intensive farming", "industrial farming",
    ],
    "polyculture": [
        "polyculture", "mixed crop", "multiple crops", "mixed farming", "crop rotation",
        "rotational farming", "diverse crops",
    ],
    "agroforestry": [
        "agroforestry", "trees and crops", "silvopasture", "alley cropping",
    ],
    "pasture": [
        "pasture", "grazing", "livestock", "rangeland", "grassland farming", "cattle",
    ],
    "orchard": ["orchard", "vineyard", "plantation"],
    "fallow": ["fallow", "unused", "left bare", "abandoned land", "uncultivated"],
    "forest": ["forest", "forested", "woodland", "wooded"],
    "wetland": ["wetland", "marsh", "swamp", "floodplain"],
    "urban": ["urban", "built-up", "developed land", "residential", "paved"],
    # Generic catch-all: real answers are often just "agriculture"/"farmland" without
    # specifying monoculture vs polyculture. Recognizing it satisfies the required
    # field instead of looping while waiting for more specific wording; the reasoning
    # engine simply won't fire its monoculture-specific check for this generic value.
    "agriculture": [
        "agriculture", "agricultural", "farmland", "cropland", "farming", "crops",
        "crop land", "arable land", "subsistence farming", "organic farming",
    ],
}

# Common crop names -- used as a fallback when no explicit land-use phrase (like
# "monoculture" or "agriculture") is present but the user just names what they grow,
# e.g. "we grow wheat". One distinct crop named -> assume monoculture; two or more
# distinct crops named -> assume polyculture. This is a reasonable default matching
# how people actually talk, not a certainty -- flagged in the code, not hidden.
COMMON_CROPS = [
    "wheat", "corn", "maize", "rice", "soybean", "soybeans", "soy", "cotton", "barley",
    "sorghum", "millet", "oats", "rye", "sunflower", "canola", "rapeseed",
    "peanut", "peanuts", "groundnut", "cocoa", "coffee", "tea", "sugarcane", "sugar cane",
    "potato", "potatoes", "tomato", "tomatoes", "cassava", "banana", "bananas",
    "coconut", "cabbage", "onion", "onions", "carrot", "carrots", "lentil", "lentils",
    "chickpea", "chickpeas", "quinoa", "sesame", "flax", "hemp", "tobacco", "grape", "grapes",
]

# Direct word-based rainfall cues (used only if no explicit "low/medium/high" or
# numeric mm/inches value is found in the text).
RAINFALL_KEYWORDS = {
    "low": [
        "semi-arid", "arid", "dry", "drought", "scarce rain", "little rain",
        "water-scarce", "water scarce", "drought-prone",
    ],
    "high": [
        "wet", "humid", "monsoon", "plentiful rain", "abundant rain", "high precipitation",
        "flooding", "waterlogged",
    ],
    "medium": ["seasonal rain", "erratic rain", "unpredictable rain"],
}

# Rainfall thresholds in mm/year, kept consistent with db/seed_data.py's
# metric_thresholds seed (400 / 1000) -- update both if you change these.
RAINFALL_MM_LOW_MAX = 400
RAINFALL_MM_HIGH_MIN = 1000

LEVEL_KEYWORDS = {
    "high": ["high", "heavy", "severe", "a lot of", "significant", "extensive", "widespread"],
    "low": ["low", "minimal", "little", "slight", "limited"],
    "medium": ["moderate", "medium", "some", "occasional"],
}


def _match_keywords(text: str, keyword_map: dict) -> str | None:
    text_lower = text.lower()
    for value, keywords in keyword_map.items():
        for kw in keywords:
            if kw in text_lower:
                return value
    return None


def _extract_level(text: str) -> str | None:
    """Generic low/medium/high word detection, used for pollution/deforestation levels."""
    return _match_keywords(text, LEVEL_KEYWORDS)


def _extract_crop_based_land_use(text: str) -> str | None:
    """
    Fallback for answers like "we grow wheat" or "wheat and lentils" that name a crop
    without ever saying "monoculture" or "agriculture". Counts distinct named crops:
    one -> monoculture, two or more -> polyculture.
    """
    text_lower = text.lower()
    found = set()
    for crop in COMMON_CROPS:
        if re.search(rf"\b{re.escape(crop)}\b", text_lower):
            found.add(crop)
    if not found:
        return None
    return "monoculture" if len(found) == 1 else "polyculture"


def _mm_to_level(mm: float) -> str:
    if mm < RAINFALL_MM_LOW_MAX:
        return "low"
    if mm > RAINFALL_MM_HIGH_MIN:
        return "high"
    return "medium"


def _extract_rainfall(text: str) -> str | None:
    """
    Tries, in order:
    1. An explicit numeric rainfall value ("rainfall is 350mm", "800 mm of rain a year")
       -- most reliable when present, mapped to low/medium/high via fixed thresholds.
    2. "low/medium/high" stated near the word "rainfall", in either word order
       ("rainfall level low" AND "low rainfall" both match).
    3. Indirect climate-descriptor words (semi-arid, humid, monsoon, etc.) as a fallback.
    """
    mm_match = re.search(r"(\d+\.?\d*)\s*mm\b", text, re.IGNORECASE)
    if mm_match:
        return _mm_to_level(float(mm_match.group(1)))

    inch_match = re.search(r"(\d+\.?\d*)\s*(?:inch|in\.?)\b", text, re.IGNORECASE)
    if inch_match:
        return _mm_to_level(float(inch_match.group(1)) * 25.4)

    patterns = [
        r"rainfall[\s\w]{0,15}?\b(low|medium|moderate|high)\b",
        r"\b(low|medium|moderate|high)\b[\s\w]{0,15}?rainfall",
        r"precipitation[\s\w]{0,15}?\b(low|medium|moderate|high)\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            level = match.group(1).lower()
            return "medium" if level == "moderate" else level

    return _match_keywords(text, RAINFALL_KEYWORDS)


def extract_fields(text: str, pending_fields: list[str] = None) -> dict:
    """
    pending_fields: the required fields that were missing (and just asked about) on
    the previous turn. Used as a fallback so a bare one-word reply like "low" gets
    correctly understood as answering "what's the rainfall level?" even though the
    text alone has no context clues (no "rainfall" word, no field name).
    """
    fields = {}

    # Soil organic carbon: "0.3%", "soil organic carbon of 0.3", "SOC 0.3"
    soc_match = re.search(r"(?:organic carbon|soc)[^\d]{0,15}(\d+\.?\d*)\s*%?", text, re.IGNORECASE)
    if not soc_match:
        soc_match = re.search(r"(\d+\.?\d*)\s*%\s*(?:soil )?organic carbon", text, re.IGNORECASE)
    if soc_match:
        fields["soil_organic_carbon_pct"] = float(soc_match.group(1))

    # Soil pH -- word-boundary + "soil" or standalone "pH", to avoid false-matching
    # inside unrelated words that happen to contain "ph" (e.g. "phosphorus").
    ph_match = re.search(r"\b(?:soil\s+)?ph\b[^\d]{0,10}(\d+\.?\d*)", text, re.IGNORECASE)
    if ph_match:
        fields["soil_ph"] = float(ph_match.group(1))

    # Soil moisture: "soil moisture of 25%", "moisture content 20%", "25% moisture"
    moisture_match = re.search(r"(?:soil\s+moisture|moisture\s+content|moisture)[^\d]{0,15}(\d+\.?\d*)\s*%?", text, re.IGNORECASE)
    if not moisture_match:
        moisture_match = re.search(r"(\d+\.?\d*)\s*%\s*(?:soil\s+)?moisture", text, re.IGNORECASE)
    if moisture_match:
        fields["soil_moisture_pct"] = float(moisture_match.group(1))

    land_use = _match_keywords(text, LAND_USE_KEYWORDS)
    if not land_use:
        land_use = _extract_crop_based_land_use(text)
    if land_use:
        fields["land_use"] = land_use

    rainfall = _extract_rainfall(text)
    if rainfall:
        fields["rainfall_level"] = rainfall

    text_lower = text.lower()

    if any(kw in text_lower for kw in ["pollution", "pesticide", "agrochemical", "herbicide", "chemical runoff", "fertilizer overuse"]):
        fields["pollution_level"] = _extract_level(text) or "medium"

    if any(kw in text_lower for kw in ["deforest", "clearing", "cleared", "logged", "logging", "cut down", "tree loss"]):
        fields["deforestation_level"] = _extract_level(text) or "medium"

    region_match = re.search(
        r"(semi-arid|arid|tropical|temperate|humid|coastal|mediterranean|alpine|subtropical)\s*region?",
        text, re.IGNORECASE,
    )
    if region_match:
        fields["region_type"] = region_match.group(1).lower()

    # Context-aware fallback: a short, otherwise-unparsed reply to a field we just
    # asked about. Only applies to fields still missing after the normal parse above,
    # and only when the reply is short (<=4 words) so it doesn't misfire on longer,
    # unrelated sentences that happen to contain a stray "low"/"high".
    if pending_fields and len(text.split()) <= 4:
        stripped = text.strip().lower().rstrip(".!")

        if "rainfall_level" in pending_fields and "rainfall_level" not in fields:
            bare_level = {"low": "low", "medium": "medium", "moderate": "medium", "high": "high"}
            if stripped in bare_level:
                fields["rainfall_level"] = bare_level[stripped]

        if "soil_organic_carbon_pct" in pending_fields and "soil_organic_carbon_pct" not in fields:
            bare_number = re.fullmatch(r"(\d+\.?\d*)\s*%?", stripped)
            if bare_number:
                fields["soil_organic_carbon_pct"] = float(bare_number.group(1))
        # Note: soil_ph and soil_moisture_pct are OPTIONAL fields (see
        # reasoning/multi_metric_engine.py's OPTIONAL_FIELDS), so they're never in
        # pending_fields today -- this bare-number fallback only fires for REQUIRED
        # fields the system explicitly blocked on. If you later promote pH/moisture
        # to required, add matching blocks here following the SOC pattern above.

        if "land_use" in pending_fields and "land_use" not in fields:
            # Bare single-word land-use answers ("farm", "grazing land") that don't
            # hit the main keyword lists as a full phrase.
            bare_land_use = {"farm": "agriculture", "cropland": "agriculture", "grazing": "pasture"}
            if stripped in bare_land_use:
                fields["land_use"] = bare_land_use[stripped]

    return fields
