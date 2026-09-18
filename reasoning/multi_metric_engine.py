"""
Rule-based multi-metric reasoning layer. This runs BEFORE any LLM call — it decides
which cross-variable issues are actually present from the structured inputs, which
then drives what gets retrieved (both structured interventions and semantic search
queries). This is what keeps the system from giving single-variable, generic answers:
the LLM never reasons about raw numbers directly, it reasons about pre-linked issues.
"""

REQUIRED_FIELDS = ["soil_organic_carbon_pct", "rainfall_level", "land_use"]
OPTIONAL_FIELDS = ["soil_ph", "region_type", "pollution_level", "deforestation_level"]


def missing_required_fields(inputs: dict) -> list[str]:
    return [f for f in REQUIRED_FIELDS if inputs.get(f) in (None, "")]


def analyze(inputs: dict) -> dict:
    """
    Takes normalized inputs (soil_organic_carbon_pct: float, rainfall_level: 'low'|'medium'|'high',
    land_use: 'monoculture'|'polyculture'|'agroforestry'|..., plus optional fields) and returns
    the linked cross-variable issues actually present.
    """
    soc = inputs.get("soil_organic_carbon_pct")
    rainfall = inputs.get("rainfall_level")
    land_use = inputs.get("land_use")
    pollution = inputs.get("pollution_level")
    deforestation = inputs.get("deforestation_level")

    issues = []
    linked_variables = []

    low_soc = soc is not None and soc < 0.5
    low_rainfall = rainfall == "low"
    is_monoculture = land_use == "monoculture"

    # Soil <-> biodiversity
    if low_soc:
        issues.append({
            "issue": "low_soil_organic_carbon",
            "detail": f"Soil organic carbon at {soc}% is below the ~0.5% threshold associated with degraded microbial and pollinator support.",
        })
        linked_variables.append("soil_organic_carbon <-> soil_microbial_diversity <-> pollinator_support")

    # Water <-> species survival, compounded by low SOC
    if low_rainfall:
        issues.append({
            "issue": "low_rainfall_stress",
            "detail": "Low rainfall increases moisture stress on both crop and wild species survival.",
        })
        linked_variables.append("rainfall <-> soil_moisture_retention <-> species_survival")
        if low_soc:
            issues.append({
                "issue": "compounding_soc_rainfall",
                "detail": "Low SOC reduces water-holding capacity precisely where rainfall is already limiting — a compounding feedback loop, not two independent problems.",
            })
            linked_variables.append("soil_organic_carbon <-> water_holding_capacity <-> rainfall_variability")

    # Land use <-> habitat fragmentation
    if is_monoculture:
        issues.append({
            "issue": "monoculture_habitat_simplification",
            "detail": "Monoculture removes structural/temporal niche diversity, reducing insect, pollinator, and bird diversity.",
        })
        linked_variables.append("land_use <-> habitat_structure <-> species_richness")
        if low_rainfall:
            linked_variables.append("land_use <-> microclimate_buffering <-> moisture_stress")

    # Human impact factors
    if pollution == "high":
        issues.append({
            "issue": "agrochemical_pollution",
            "detail": "High agrochemical input directly suppresses pollinator and aquatic biodiversity.",
        })
        linked_variables.append("pollution <-> pollinator_diversity <-> aquatic_biodiversity")

    if deforestation in ("high", "medium"):
        issues.append({
            "issue": "habitat_fragmentation",
            "detail": "Deforestation/clearing creates edge effects and fragmentation extending beyond the cleared area itself.",
        })
        linked_variables.append("deforestation <-> habitat_connectivity <-> species_range")

    return {
        "issues": issues,
        "linked_variables": linked_variables,
        "flags": {
            "low_soc": low_soc,
            "low_rainfall": low_rainfall,
            "is_monoculture": is_monoculture,
        },
    }
