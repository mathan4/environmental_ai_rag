"""
Seeds the structured intervention benchmark table. These are the quantified,
citable claims the system is allowed to state numbers for -- the LLM is instructed
to only use figures that came from here or the RAG documents, never invent new ones.

Each intervention declares `targets_issues`: a list of issue tags matching what
reasoning/multi_metric_engine.py's analyze() can detect. This replaces the old
land_use/rainfall/soc-specific filter columns -- adding a new soil metric (or any
other variable) just needs a new tag here and in the reasoning engine, no schema change.
"""
from db.connection import get_connection, init_schema

INTERVENTIONS = [
    {
        "name": "Legume-based cover cropping",
        "action_summary": "Introduce legume-based cover crops (e.g. clover, vetch, cowpea) between or alongside the main crop.",
        "mechanism": "Nitrogen-fixing legumes add organic matter via root turnover and biomass incorporation, rebuilding soil organic carbon and feeding soil microbial communities.",
        "impacted_metric": "soil_organic_carbon",
        "effect_low_pct": 15, "effect_high_pct": 25,
        "time_horizon": "medium", "time_horizon_detail": "2-3 years",
        "confidence": "high", "source_org": "FAO",
        "targets_issues": ["low_soil_organic_carbon"],
    },
    {
        "name": "Agroforestry / intercropping with trees",
        "action_summary": "Integrate rows or scattered trees (e.g. nitrogen-fixing or fruit species suited to the region) into the existing cropland.",
        "mechanism": "Tree root systems and leaf litter add a deeper, longer-lived carbon pool than annual cover crops; canopy shade and windbreak effects reduce soil surface temperature and moisture loss, disproportionately valuable in low-rainfall regions.",
        "impacted_metric": "soil_organic_carbon",
        "effect_low_pct": 20, "effect_high_pct": 35,
        "time_horizon": "long", "time_horizon_detail": "5-10 years",
        "confidence": "high", "source_org": "IPCC / FAO agroforestry guidance",
        "targets_issues": ["low_soil_organic_carbon", "low_rainfall_stress", "compounding_soc_rainfall"],
    },
    {
        "name": "Agroforestry / intercropping -- habitat effect",
        "action_summary": "Same agroforestry/intercropping intervention as above, evaluated for its habitat and pollinator effect rather than its soil-carbon effect.",
        "mechanism": "Vertical canopy structure and flowering tree/shrub species create niches unavailable in single-species monoculture, supporting a wider range of insects, birds, and pollinators; microclimate buffering reduces moisture stress on edge species during dry periods.",
        "impacted_metric": "pollinator_diversity",
        "effect_low_pct": 20, "effect_high_pct": 40,
        "time_horizon": "medium", "time_horizon_detail": "2-4 years",
        "confidence": "medium", "source_org": "CBD/IPBES; FAO agroecology reports",
        "targets_issues": ["monoculture_habitat_simplification"],
    },
    {
        "name": "Strip-cropping / intercropping (non-tree)",
        "action_summary": "Alternate strips or rows of a second crop species (e.g. legume or flowering companion crop) within the existing field, without full agroforestry conversion.",
        "mechanism": "Restores some structural and temporal niche diversity that monoculture removes; lower-cost, faster-to-implement intermediate step compared to agroforestry.",
        "impacted_metric": "beneficial_insect_abundance",
        "effect_low_pct": 10, "effect_high_pct": 30,
        "time_horizon": "short", "time_horizon_detail": "1-2 growing seasons",
        "confidence": "medium", "source_org": "IPCC land-use assessments; FAO agroecology guidance",
        "targets_issues": ["monoculture_habitat_simplification"],
    },
    {
        "name": "Hedgerows / buffer strips for connectivity",
        "action_summary": "Establish hedgerows or vegetated buffer strips along field edges and waterways.",
        "mechanism": "Re-establishes habitat corridors between fragmented patches, which pollinators, amphibians, and small mammals require for viable populations even when individual patches are otherwise healthy; buffer strips along waterways also filter agrochemical runoff.",
        "impacted_metric": "habitat_connectivity",
        "effect_low_pct": None, "effect_high_pct": None,
        "time_horizon": "medium", "time_horizon_detail": "2-5 years for full corridor function",
        "confidence": "medium", "source_org": "CBD/IPBES",
        "targets_issues": ["habitat_fragmentation", "monoculture_habitat_simplification"],
    },
    {
        "name": "Reduced tillage / no-till",
        "action_summary": "Shift from conventional tillage to reduced or no-till cultivation.",
        "mechanism": "Tillage accelerates soil organic carbon oxidation and disrupts fungal networks (especially mycorrhizae); reducing it slows carbon loss and preserves soil structure and microbial habitat.",
        "impacted_metric": "soil_microbial_diversity",
        "effect_low_pct": 10, "effect_high_pct": 20,
        "time_horizon": "medium", "time_horizon_detail": "2-4 years",
        "confidence": "high", "source_org": "FAO",
        "targets_issues": ["low_soil_organic_carbon"],
    },
    {
        "name": "Riparian buffer restoration",
        "action_summary": "Restore or plant vegetated buffers along waterways bordering the land.",
        "mechanism": "Simultaneously filters agrochemical runoff before it reaches waterways, restores terrestrial corridor connectivity, and reduces edge-effect degradation of adjacent habitat -- a disproportionately high-value intervention relative to the land area it uses.",
        "impacted_metric": "aquatic_and_terrestrial_biodiversity",
        "effect_low_pct": None, "effect_high_pct": None,
        "time_horizon": "long", "time_horizon_detail": "3-7 years for mature buffer function",
        "confidence": "medium", "source_org": "CBD/IPBES",
        "targets_issues": ["habitat_fragmentation", "agrochemical_pollution"],
    },
    {
        "name": "Integrated pest management (reduced agrochemical input)",
        "action_summary": "Adopt integrated pest management to reduce synthetic pesticide/herbicide reliance, paired with habitat refuges (hedgerows/buffer strips).",
        "mechanism": "Reduces direct pollinator and aquatic-species exposure to agrochemical runoff; pairing with habitat refuges allows predator-insect and pollinator populations to recover between exposure events, which input reduction alone does not achieve.",
        "impacted_metric": "pollinator_diversity",
        "effect_low_pct": None, "effect_high_pct": None,
        "time_horizon": "short", "time_horizon_detail": "1-2 seasons for initial recovery",
        "confidence": "medium", "source_org": "FAO / CBD",
        "targets_issues": ["agrochemical_pollution"],
    },
    # --- New: soil pH correction (previously impossible -- pH had no intervention at all) ---
    {
        "name": "Soil pH correction (lime or elemental sulfur amendment)",
        "action_summary": "Apply agricultural lime to raise pH in acidic soil, or elemental sulfur to lower pH in alkaline soil, based on a current soil test.",
        "mechanism": "Correcting pH back toward the 6.0-7.5 range most species tolerate restores micronutrient availability (iron/zinc lockup at high pH; aluminum toxicity at low pH), which directly limits both crop yield and understory plant diversity, and cascades to reduced insect and pollinator diversity when left uncorrected.",
        "impacted_metric": "soil_ph",
        "effect_low_pct": None, "effect_high_pct": None,
        "time_horizon": "short", "time_horizon_detail": "3-6 months for measurable pH shift, longer for full nutrient recovery",
        "confidence": "high", "source_org": "FAO soil health guidance",
        "targets_issues": ["soil_ph_imbalance"],
    },
    # --- New: soil moisture retention (previously impossible -- moisture had no intervention at all) ---
    {
        "name": "Mulching and moisture-retention groundcover",
        "action_summary": "Apply organic mulch (straw, crop residue, wood chips) or establish a low groundcover between rows to reduce bare-soil evaporation.",
        "mechanism": "Mulch cover reduces direct soil-surface evaporation and buffers surface temperature spikes, directly easing moisture stress in low-rainfall conditions; it also slows runoff, allowing more water to infiltrate rather than being lost, which compounds with soil organic carbon's own water-holding benefit.",
        "impacted_metric": "soil_moisture",
        "effect_low_pct": 15, "effect_high_pct": 30,
        "time_horizon": "short", "time_horizon_detail": "1 growing season",
        "confidence": "medium", "source_org": "FAO water-conservation guidance",
        "targets_issues": ["low_soil_moisture", "low_rainfall_stress", "compounding_soc_rainfall"],
    },
]

METRIC_THRESHOLDS = [
    ("soil_organic_carbon", 0.5, 3.0, "%", "Below 0.5% typically indicates degraded, low-biodiversity soil."),
    ("soil_ph", 6.0, 7.5, "pH", "Outside this range, micronutrient lockup suppresses plant and pollinator diversity."),
    ("soil_moisture", 20.0, 60.0, "%", "Below ~20% volumetric moisture generally stresses both crop and wild-species survival in most soils."),
    ("rainfall_mm_annual", 400, 1000, "mm/year", "Below ~400mm/year is generally semi-arid to arid."),
]


def seed():
    init_schema()
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM interventions")
        cur.execute("DELETE FROM metric_thresholds")
        for i in INTERVENTIONS:
            cur.execute(
                """
                INSERT INTO interventions
                (name, action_summary, mechanism, impacted_metric, effect_low_pct, effect_high_pct,
                 time_horizon, time_horizon_detail, confidence, source_org, targets_issues)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (i["name"], i["action_summary"], i["mechanism"], i["impacted_metric"],
                 i["effect_low_pct"], i["effect_high_pct"], i["time_horizon"], i["time_horizon_detail"],
                 i["confidence"], i["source_org"], ",".join(i["targets_issues"])),
            )
        for m in METRIC_THRESHOLDS:
            cur.execute(
                "INSERT INTO metric_thresholds (metric, low_bound, high_bound, unit, notes) VALUES (?, ?, ?, ?, ?)",
                m,
            )
        conn.commit()
        print(f"Seeded {len(INTERVENTIONS)} interventions and {len(METRIC_THRESHOLDS)} thresholds.")
    finally:
        conn.close()


if __name__ == "__main__":
    seed()
