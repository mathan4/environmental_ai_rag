"""
Eco Advisor Streamlit Web Application
Simple Conversational Interface for Ecosystem Analysis & Agroecology Interventions.
"""
import streamlit as st
from core.engine import handle_message

# Page configuration
st.set_page_config(
    page_title="Eco Advisor",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom Styling
st.markdown(
    """
    <style>
    .main-header {
        font-size: 2rem;
        font-weight: 700;
        color: #1E3A8A;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        font-size: 1rem;
        color: #4B5563;
        margin-bottom: 1.5rem;
    }
    .card-recommendation {
        background-color: #F9FAFB;
        border: 1px solid #E5E7EB;
        border-left: 4px solid #059669;
        border-radius: 0.5rem;
        padding: 1rem 1.25rem;
        margin-bottom: 1rem;
    }
    .card-title {
        font-size: 1.05rem;
        font-weight: 700;
        color: #065F46;
        margin-bottom: 0.4rem;
    }
    .card-mechanism {
        font-size: 0.93rem;
        color: #374151;
        margin-bottom: 0.6rem;
    }
    .meta-tag {
        background-color: #E0E7FF;
        color: #3730A3;
        font-weight: 600;
        font-size: 0.8rem;
        padding: 0.15rem 0.5rem;
        border-radius: 0.25rem;
        margin-right: 0.4rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Initialize Session State
if "messages" not in st.session_state:
    st.session_state.messages = []

if "session_id" not in st.session_state:
    st.session_state.session_id = "streamlit-session"

if "inputs" not in st.session_state:
    st.session_state.inputs = {
        "soil_organic_carbon_pct": None,
        "rainfall_mm_annual": None,
        "soil_ph": None,
        "soil_moisture_pct": None,
        "land_use": "",
        "region": "",
        "crop": "",
    }

# Header Section
st.markdown('<div class="main-header">Eco Advisor</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="sub-header">AI Ecosystem Analysis & Quantitative Agroecology Recommendations</div>',
    unsafe_allow_html=True,
)
st.divider()

# Sidebar: Parameters & Controls
with st.sidebar:
    st.header("Land & Soil Metrics")
    st.caption("Provide measured site parameters to enhance multi-metric reasoning.")

    # Preset Button
    if st.button("Load Spec Example Scenario", use_container_width=True):
        st.session_state.inputs["soil_organic_carbon_pct"] = 0.3
        st.session_state.inputs["rainfall_mm_annual"] = 350.0
        st.session_state.inputs["land_use"] = "Monoculture wheat"
        st.session_state.inputs["region"] = "Semi-arid"
        st.rerun()

    soc_input = st.number_input(
        "Soil Organic Carbon (%)",
        min_value=0.0,
        max_value=20.0,
        value=float(st.session_state.inputs["soil_organic_carbon_pct"]) if st.session_state.inputs["soil_organic_carbon_pct"] is not None else 0.0,
        step=0.1,
        help="Target healthy threshold is ~3.0%. Below 0.5% indicates severe soil degradation.",
    )
    if soc_input > 0.0:
        st.session_state.inputs["soil_organic_carbon_pct"] = soc_input
    else:
        st.session_state.inputs["soil_organic_carbon_pct"] = None

    rainfall_input = st.number_input(
        "Annual Rainfall (mm/year)",
        min_value=0.0,
        max_value=5000.0,
        value=float(st.session_state.inputs["rainfall_mm_annual"]) if st.session_state.inputs["rainfall_mm_annual"] is not None else 0.0,
        step=50.0,
        help="Semi-arid regions typically receive <400mm/year.",
    )
    if rainfall_input > 0.0:
        st.session_state.inputs["rainfall_mm_annual"] = rainfall_input
    else:
        st.session_state.inputs["rainfall_mm_annual"] = None

    ph_input = st.number_input(
        "Soil pH",
        min_value=0.0,
        max_value=14.0,
        value=float(st.session_state.inputs["soil_ph"]) if st.session_state.inputs["soil_ph"] is not None else 0.0,
        step=0.1,
        help="Optimal range for most crops is 6.0 - 7.5.",
    )
    if ph_input > 0.0:
        st.session_state.inputs["soil_ph"] = ph_input
    else:
        st.session_state.inputs["soil_ph"] = None

    moisture_input = st.number_input(
        "Soil Volumetric Moisture (%)",
        min_value=0.0,
        max_value=100.0,
        value=float(st.session_state.inputs["soil_moisture_pct"]) if st.session_state.inputs["soil_moisture_pct"] is not None else 0.0,
        step=1.0,
        help="Moisture below 20% indicates significant crop and wild species drought stress.",
    )
    if moisture_input > 0.0:
        st.session_state.inputs["soil_moisture_pct"] = moisture_input
    else:
        st.session_state.inputs["soil_moisture_pct"] = None

    st.session_state.inputs["land_use"] = st.text_input(
        "Land Use / Management",
        value=st.session_state.inputs.get("land_use", ""),
        placeholder="e.g. Monoculture wheat, Agroforestry",
    )

    st.session_state.inputs["region"] = st.text_input(
        "Region / Climate Zone",
        value=st.session_state.inputs.get("region", ""),
        placeholder="e.g. Semi-arid, Mediterranean",
    )

    st.session_state.inputs["crop"] = st.text_input(
        "Primary Crop / Plant Species",
        value=st.session_state.inputs.get("crop", ""),
        placeholder="e.g. Wheat, Maize, Coffee",
    )

    st.divider()
    if st.button("Reset Conversation", use_container_width=True):
        st.session_state.messages = []
        st.session_state.inputs = {
            "soil_organic_carbon_pct": None,
            "rainfall_mm_annual": None,
            "soil_ph": None,
            "soil_moisture_pct": None,
            "land_use": "",
            "region": "",
            "crop": "",
        }
        st.rerun()

# Main Chat Interface
st.caption("Ask general ecological questions or describe your land situation for analysis.")

# Render conversation history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        if msg["role"] == "user":
            st.markdown(msg["content"])
        else:
            res = msg.get("result_data", {})
            if res.get("clarifying_question"):
                st.warning(f"**Clarifying Question:** {res['clarifying_question']}")
            elif res.get("reply"):
                st.markdown(res["reply"])
            else:
                recs = res.get("recommendations", [])
                if recs:
                    st.subheader("Recommended Ecological Interventions")
                    for idx, rec in enumerate(recs, 1):
                        with st.container():
                            st.markdown(
                                f"""
                                <div class="card-recommendation">
                                    <div class="card-title">[{idx}] {rec.get('intervention_name')}</div>
                                    <div class="card-mechanism"><b>Action:</b> {rec.get('action_summary', '')}</div>
                                    <div class="card-mechanism"><b>Why (Scientific Mechanism):</b> {rec.get('mechanism', '')}</div>
                                    <div>
                                        <span class="meta-tag">Metrics: {", ".join(rec.get('impacted_metrics', []))}</span>
                                        <span class="meta-tag">Effect: {rec.get('estimated_effect', 'N/A')}</span>
                                        <span class="meta-tag">Timeframe: {rec.get('time_horizon', 'N/A')} ({rec.get('time_horizon_detail', '')})</span>
                                        <span class="meta-tag">Confidence: {rec.get('confidence', 'N/A')}</span>
                                    </div>
                                </div>
                                """,
                                unsafe_allow_html=True,
                            )

                links = res.get("cross_variable_links_considered", [])
                if links:
                    with st.expander("Cross-Variable Ecological Feedbacks Considered"):
                        for link in links:
                            st.markdown(f"- `{link}`")

            debug_info = res.get("_debug", {})
            if debug_info:
                with st.expander("System Reasoning & Evidence Metadata"):
                    st.json(debug_info)

# Chat Input
prompt = st.chat_input("Describe your land, ask a question, or answer a clarifying prompt...")
if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    active_structured = {
        k: v for k, v in st.session_state.inputs.items() if v is not None and v != ""
    }

    with st.spinner("Analyzing ecosystem metrics..."):
        result = handle_message(
            user_text=prompt,
            session_id=st.session_state.session_id,
            structured_input=active_structured if active_structured else None,
        )

    st.session_state.messages.append({"role": "assistant", "content": "", "result_data": result})
    st.rerun()
