"""
Rule-based multi-metric reasoning layer. This runs BEFORE any LLM call -- it decides
which cross-variable issues are actually present from the structured inputs, which
then drives what gets retrieved (both structured interventions and semantic search
queries). This is what keeps the system from giving single-variable, generic answers:
the LLM never reasons about raw numbers directly, it reasons about pre-linked issues.

Soil health is multi-factor (organic carbon, pH, moisture -- not just SOC): thresholds
for all three are read from the metric_thresholds table (rag/retriever.py's
get_metric_thresholds()) rather than hardcoded here, so adding a fourth soil metric
later means adding a row to db/seed_data.py's METRIC_THRESHOLDS, not editing this file.
"""
from rag.retriever import get_metric_thresholds

REQUIRED_FIELDS = ["soil_organic_carbon_pct", "rainfall_level", "land_use"]
OPTIONAL_FIELDS = ["soil_ph", "soil_moisture_pct", "region_type", "pollution_level", "deforestation_level"]


def missing_required_fields(inputs: dict) -> list[str]:
    return [f for f in REQUIRED_FIELDS if inputs.get(f) in (None, "")]


def analyze(inputs: dict) -> dict:
    """
    Takes normalized inputs (soil_organic_carbon_pct: float, soil_ph: float,
    soil_moisture_pct: float, rainfall_level: 'low'|'medium'|'high',
    land_use: 'monoculture'|'polyculture'|'agroforestry'|..., plus other optional
    fields) and returns the linked cross-variable issues actually present.
    """
    thresholds = get_metric_thresholds()

    soc = inputs.get("soil_organic_carbon_pct")
    soil_ph = inputs.get("soil_ph")
    soil_moisture = inputs.get("soil_moisture_pct")
    rainfall = inputs.get("rainfall_level")
    land_use = inputs.get("land_use")
    pollution = inputs.get("pollution_level")
    deforestation = inputs.get("deforestation_level")

    issues = []
    linked_variables = []

    soc_bounds = thresholds.get("soil_organic_carbon", {})
    low_soc = soc is not None and soc_bounds.get("low_bound") is not None and soc < soc_bounds["low_bound"]

    ph_bounds = thresholds.get("soil_ph", {})
    ph_imbalanced = (
        soil_ph is not None and ph_bounds.get("low_bound") is not None and ph_bounds.get("high_bound") is not None
        and not (ph_bounds["low_bound"] <= soil_ph <= ph_bounds["high_bound"])
    )

    moisture_bounds = thresholds.get("soil_moisture", {})
    low_moisture = (
        soil_moisture is not None and moisture_bounds.get("low_bound") is not None
        and soil_moisture < moisture_bounds["low_bound"]
    )

    low_rainfall = rainfall == "low"
    is_monoculture = land_use == "monoculture"

    # --- Soil organic carbon <-> biodiversity ---
    if low_soc:
        issues.append({
            "issue": "low_soil_organic_carbon",
            "detail": f"Soil organic carbon at {soc}% is below the ~{soc_bounds.get('low_bound')}% threshold associated with degraded microbial and pollinator support.",
        })
        linked_variables.append("soil_organic_carbon <-> soil_microbial_diversity <-> pollinator_support")

    # --- Soil pH <-> nutrient availability <-> plant/pollinator diversity ---
    if ph_imbalanced:
        direction = "acidic" if soil_ph < ph_bounds["low_bound"] else "alkaline"
        issues.append({
            "issue": "soil_ph_imbalance",
            "detail": f"Soil pH at {soil_ph} is outside the {ph_bounds['low_bound']}-{ph_bounds['high_bound']} range most species tolerate ({direction}), which locks up micronutrients and suppresses both plant and pollinator diversity.",
        })
        linked_variables.append("soil_ph <-> nutrient_availability <-> plant_diversity <-> pollinator_diversity")

    # --- Soil moisture <-> species survival, distinct from (but related to) rainfall ---
    if low_moisture:
        issues.append({
            "issue": "low_soil_moisture",
            "detail": f"Soil moisture at {soil_moisture}% is below the ~{moisture_bounds.get('low_bound')}% threshold generally needed to avoid stressing crop and wild-species survival.",
        })
        linked_variables.append("soil_moisture <-> species_survival")

    # --- Water (rainfall) <-> species survival, compounded by low SOC and/or low measured moisture ---
    if low_rainfall:
        issues.append({
            "issue": "low_rainfall_stress",
            "detail": "Low rainfall increases moisture stress on both crop and wild species survival.",
        })
        linked_variables.append("rainfall <-> soil_moisture_retention <-> species_survival")
        if low_soc:
            issues.append({
                "issue": "compounding_soc_rainfall",
                "detail": "Low SOC reduces water-holding capacity precisely where rainfall is already limiting -- a compounding feedback loop, not two independent problems.",
            })
            linked_variables.append("soil_organic_carbon <-> water_holding_capacity <-> rainfall_variability")
        if low_moisture:
            linked_variables.append("rainfall <-> soil_moisture <-> species_survival (directly measured, not just inferred from rainfall)")

    # --- Land use <-> habitat fragmentation ---
    if is_monoculture:
        issues.append({
            "issue": "monoculture_habitat_simplification",
            "detail": "Monoculture removes structural/temporal niche diversity, reducing insect, pollinator, and bird diversity.",
        })
        linked_variables.append("land_use <-> habitat_structure <-> species_richness")
        if low_rainfall:
            linked_variables.append("land_use <-> microclimate_buffering <-> moisture_stress")
        if ph_imbalanced:
            linked_variables.append("land_use <-> nutrient_depletion <-> soil_ph_imbalance")

    # --- Human impact factors ---
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
            "ph_imbalanced": ph_imbalanced,
            "low_moisture": low_moisture,
            "low_rainfall": low_rainfall,
            "is_monoculture": is_monoculture,
        },
    }
