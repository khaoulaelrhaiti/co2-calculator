import pandas as pd
import streamlit as st
import plotly.express as px
import requests
import json

# --- GEMINI AI CONFIGURATION ---
# IMPORTANT: Your API key is visible here. For production, use st.secrets.
GEMINI_API_KEY = "AIzaSyCx7gfigfB0nEu2nZ-LGUNLnAuKcN8iWrk" 
# --- END GEMINI CONFIGURATION ---


def get_gemini_response(chat_history: list):
    """
    Sends a conversation history to the Gemini API using a direct HTTP request.

    Args:
        chat_history (list): A list of dictionaries representing the conversation.
                             Example: [{"role": "user", "parts": [{"text": "Hello"}]}]

    Returns:
        str: The text response from the AI model, or an error message.
    """
    if not GEMINI_API_KEY or GEMINI_API_KEY == "YOUR_GEMINI_API_KEY_HERE":
        return "Error: Gemini API key is not configured. Please set it at the top of the script."

    # Corrected model name to a valid one
    model_name = "gemini-2.5-flash-preview-05-20"
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={GEMINI_API_KEY}"
    
    headers = {
        "Content-Type": "application/json"
    }
    
    payload = {
        "contents": chat_history
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=90)
        response.raise_for_status() 
        
        response_json = response.json()
        
        candidates = response_json.get("candidates", [])
        if not candidates:
            return "Error: The AI model returned no candidates. This may be due to safety filters or an API issue."
            
        content = candidates[0].get("content", {})
        parts = content.get("parts", [])
        if not parts:
            return "Error: The AI model's response was empty."

        return parts[0].get("text", "Error: Could not extract text from the AI response.")

    except requests.exceptions.HTTPError as http_err:
        error_details = response.json().get("error", {})
        error_message = error_details.get("message", "No specific error message provided.")
        return f"**Error: An HTTP error occurred while contacting the Gemini API.**\n\n*Details:* {error_message}"
    except requests.exceptions.RequestException as e:
        return f"**Error: A network error occurred.** Please check your connection. \n\n*Details:* {e}"
    except (KeyError, IndexError, json.JSONDecodeError) as e:
        return f"**Error: Could not parse the AI's response.** It may be malformed. \n\n*Details:* {e}"


st.set_page_config(page_title="Interface", layout="centered")

st.title("🌍 CO2 Footprint Calculator")
st.write("Calculate your carbon footprint and see the impact of green energy.")

# Emissions per unit
CO2_PER_CAR = 0.87
CO2_PER_PASSENGER = 0.25
CO2_PER_CONTAINER = 10.21

# Coal-based emissions
COAL_PER_CAR = 1.25
COAL_PER_PASSENGER = 0.36
COAL_PER_CONTAINER = 14.71

# Green energy CO₂ per kWh
SOLAR_COEF = 0.012
WIND_COEF = 0.011
HYDRO_COEF = 0.004
DEFAULT_GREEN_COEF = 0.03385

with st.form("co2_form"):
    st.markdown("### 🚗 Transportation Details")

    col1, col2 = st.columns(2)
    with col1:
        cars = st.number_input("Number of Cars", value=0, step=1)
        if cars < 0:
            st.error("❌ Number of cars must be greater than 0")

    with col2:
        passengers = st.number_input("Number of Passengers", value=0, step=1)
        if passengers < 0:
            st.error("❌ Number of passengers must be greater than 0")

    containers = st.number_input("Number of Containers", value=0, step=1)
    if containers < 0:
        st.error("❌ Number of containers must be greater than 0")

    if cars <= 0 and passengers <= 0 and containers <= 0:
        st.warning("⚠️ Please provide at least one transportation value (cars, passengers, or containers) greater than 0.")

    st.markdown("### 🍃 Green Energy (Optional)")
    col1, col2, col3 = st.columns(3)
    with col1:
        solar = st.number_input("Solar Energy (%)", min_value=0.0, max_value=100.0, step=1.0, value=0.0)
    with col2:
        wind = st.number_input("Wind Energy (%)", min_value=0.0, max_value=100.0, step=1.0, value=0.0)
    with col3:
        hydro = st.number_input("Hydro Energy (%)", min_value=0.0, max_value=100.0, step=1.0, value=0.0)

    total_renewable = solar + wind + hydro

    if total_renewable > 100:
        st.markdown(
        f"""
        <div style="
            background-color: rgba(248, 215, 218, 0.85);
            color: #721c24;
            padding: 12px;
            border-radius: 8px;
            margin-bottom: 20px;">
            <strong>❌ Error:</strong> Total green energy percentage cannot exceed 100%.<br>
            <strong>Current total: {total_renewable:.1f}%</strong>
        </div>
        """,
        unsafe_allow_html=True
    )

    else:
        st.markdown(
    f"""
    <div style="
    background-color: #415D43;
    color: #E8F5E9;
    padding: 12px;
    border-radius: 8px;
    margin-bottom: 0px;  <!-- Set to 0 since we'll use BR -->
    border-left: 6px solid #A5D6A7;
    font-family: 'sans-serif';
    ">
    ✅ Total Green Energy: <strong>{total_renewable:.1f}%</strong>
    </div>
    <br>  <!-- Adds two line breaks -->
    """,
    unsafe_allow_html=True
)

    submitted = st.form_submit_button("✅ Calculate CO2 Footprint")

if submitted and total_renewable <= 100 and (cars > 0 or passengers > 0 or containers > 0):
    # Clear previous chat history for a new calculation
    st.session_state.messages = []

    st.markdown("## 📈 CO2 Emission Table")

    data = []
    total_co2 = total_coal = total_green = 0

    def calc_green_coef(solar, wind, hydro):
        total = solar + wind + hydro
        if total == 0:
            return DEFAULT_GREEN_COEF
        return (
            (solar / total) * SOLAR_COEF +
            (wind / total) * WIND_COEF +
            (hydro / total) * HYDRO_COEF
        )

    green_coef = calc_green_coef(solar, wind, hydro)

    def calc_green_emission(co2):
        return co2 * green_coef

    if cars > 0:
        co2_val = cars * CO2_PER_CAR
        coal = cars * COAL_PER_CAR
        green = calc_green_emission(co2_val)
        data.append(["Car", cars, co2_val, coal, green])
        total_co2 += co2_val
        total_coal += coal
        total_green += green

    if passengers > 0:
        co2_val = passengers * CO2_PER_PASSENGER
        coal = passengers * COAL_PER_PASSENGER
        green = calc_green_emission(co2_val)
        data.append(["Passenger", passengers, co2_val, coal, green])
        total_co2 += co2_val
        total_coal += coal
        total_green += green

    if containers > 0:
        co2_val = containers * CO2_PER_CONTAINER
        coal = containers * COAL_PER_CONTAINER
        green = calc_green_emission(co2_val)
        data.append(["Container", containers, co2_val, coal, green])
        total_co2 += co2_val
        total_coal += coal
        total_green += green

    df = pd.DataFrame(data, columns=[
        "Type", "Quantity", "Total CO₂ (kg)", "Total Coal CO₂ (kg)", "Green Energy CO₂ (kg)"
    ])
    st.table(df)

    st.markdown("""<small><div style="display: flex; justify-content: space-between; color: grey"><div>Per unit CO₂ emissions <br>Car: 0.87 kg <br>Passenger: 0.25 kg <br>Container: 10.21 kg</div><div style="text-align: right;">Coal per unit <br>Car: 1.25 kg <br>Passenger: 0.36 kg <br>Container: 14.71 kg</div></div></small><br>""", unsafe_allow_html=True)
    
    reduction = (1 - total_green / total_co2) * 100 if total_co2 != 0 else 0
    
    # Tabs
    tab1, tab2, tab3 = st.tabs(["📊 Comparison", "📈 Visualization", "🧠 AI Chat"])
    with tab1:
        col1, col2 = st.columns(2)

        with col1:
            st.error("🔺 Without Green Energy")
            st.markdown(f"<h2 style='color:red;'>{total_co2:.2f} kg CO₂</h2>", unsafe_allow_html=True)
        with col2:
            st.success("🌱 With Green Energy")
            st.markdown(f"<h2 style='color:green;'>{total_green:.2f} kg CO₂</h2>", unsafe_allow_html=True)

        st.markdown("### 🧮 Reduction Impact")
        
        safe_reduction = max(0, min(int(reduction), 100))
        st.markdown("High Positive Impact")
        st.progress(safe_reduction)
        st.caption(f"{reduction:.0f}% reduction")

        with st.expander("🔍 Details", expanded=True):
            st.markdown("#### Input Details:")
            if cars > 0: st.write(f"🚗 Cars: {cars}")
            if passengers > 0: st.write(f"🧍 Passengers: {passengers}")
            if containers > 0: st.write(f"📦 Containers: {containers}")
            st.write(f"🔋 Solar Energy: {solar}%")
            st.write(f"🌬️ Wind Energy: {wind}%")
            st.write(f"💧 Hydro Energy: {hydro}%")

            st.markdown("#### 🌎 Environmental Impact:")
            st.markdown(f"""<div style='background-color:rgba(248, 215, 218, 0.85); color:#721c24; padding:10px; border-radius:8px;'><strong>🚨 High CO2 Emissions Impact</strong><br>The <b>{total_co2:.0f} kg</b> of CO₂ emissions contribute to global warming and pollution.</div>""", unsafe_allow_html=True)
            st.markdown(f"""<div style='background-color:rgba(215, 248, 222, 0.85); color:#1c7224; padding:10px; border-radius:8px; margin-top:10px;'><strong>🌿 Green Energy Benefits</strong><br>By reducing emissions to <b>{total_green:.0f} kg CO₂</b> with renewables, you're helping protect our planet.</div>""", unsafe_allow_html=True)
            st.markdown(f"""<div style='background-color:rgba(215, 230, 248, 0.85); color:#1c2472; padding:10px; border-radius:8px; margin-top:10px;'><strong>🔍 Why This Matters</strong><br>Every kilogram of CO₂ avoided makes a difference in fighting climate change.</div><br>""", unsafe_allow_html=True)
            
    with tab2:
        st.subheader("📉 Emission Sources by Transport Type")
        detailed_data = pd.DataFrame([
            {"Type": "Car", "Emission Source": "Total CO₂", "Emissions (kg)": cars * CO2_PER_CAR},
            {"Type": "Car", "Emission Source": "Coal-based CO₂", "Emissions (kg)": cars * COAL_PER_CAR},
            {"Type": "Car", "Emission Source": "Green Energy CO₂", "Emissions (kg)": round(calc_green_emission(cars * CO2_PER_CAR), 2)},
            {"Type": "Passenger", "Emission Source": "Total CO₂", "Emissions (kg)": passengers * CO2_PER_PASSENGER},
            {"Type": "Passenger", "Emission Source": "Coal-based CO₂", "Emissions (kg)": passengers * COAL_PER_PASSENGER},
            {"Type": "Passenger", "Emission Source": "Green Energy CO₂", "Emissions (kg)": round(calc_green_emission(passengers * CO2_PER_PASSENGER), 2)},
            {"Type": "Container", "Emission Source": "Total CO₂", "Emissions (kg)": containers * CO2_PER_CONTAINER},
            {"Type": "Container", "Emission Source": "Coal-based CO₂", "Emissions (kg)": containers * COAL_PER_CONTAINER},
            {"Type": "Container", "Emission Source": "Green Energy CO₂", "Emissions (kg)": round(calc_green_emission(containers * CO2_PER_CONTAINER), 2)},
        ])
        fig = px.bar(detailed_data, x="Type", y="Emissions (kg)", color="Emission Source", barmode="group", text="Emissions (kg)", color_discrete_map={"Total CO₂": "#FFE6E1", "Coal-based CO₂": "#FF3F33", "Green Energy CO₂": "#9FC87E"}, title="Grouped CO₂ Emissions by Transport Type")
        fig.update_traces(texttemplate='%{text:.2f}')
        fig.update_layout(xaxis_title="Transport Type", yaxis_title="CO₂ Emissions (kg)", title_x=0.3, plot_bgcolor='rgba(0,0,0,0)', bargap=0.3)
        st.plotly_chart(fig, use_container_width=True)

    # --- AI CHAT TAB ---
    with tab3:
        st.subheader("🤖 AI-Powered Analysis & Chat")

        if not GEMINI_API_KEY or GEMINI_API_KEY == "YOUR_GEMINI_API_KEY_HERE":
            st.warning("⚠️ Please configure your Gemini API key at the top of the script to enable the AI chat.")
        else:
            # Generate initial analysis if chat is empty
            if not st.session_state.messages:
                with st.spinner("🧠 The AI is analyzing your data..."):
                    initial_prompt_text = f"""
                    You are an expert analyst in climate science and renewable energy. Your task is to provide a deep, data-driven analysis of a user's carbon footprint based on the data they provided from a calculator. Structure your response in well-formatted Markdown.

                    **User's Input Data:**
                    - Number of Cars: {cars}
                    - Number of Passengers: {passengers}
                    - Number of Containers: {containers}
                    - Green Energy Mix: {solar}% Solar, {wind}% Wind, {hydro}% Hydro.

                    **Calculated Results:**
                    - CO2 Footprint (Before Green Energy): {total_co2:.2f} kg CO₂
                    - CO2 Footprint (After applying Green Energy Mix): {total_green:.2f} kg CO₂
                    - CO2 Reduction Achieved: {reduction:.2f}%

                    **Your Task:**
                    Based on all the data above, provide a comprehensive analysis and actionable recommendations.

                    1.  **Executive Summary:** Start with a brief, impactful summary. Highlight the total potential emissions and the significant positive impact of their green energy choice.
                    2.  **Deep Dive Analysis:** Analyze the sources of their emissions (which transport is the biggest contributor?). Explain the significance of the **{total_co2:.2f} kg CO₂** figure in a relatable way. Analyze their chosen green energy mix and why it resulted in a footprint of **{total_green:.2f} kg CO₂**.
                    3.  **Predictions & Future Impact:** Assume this input represents a daily activity and project the annual CO2 emissions *before* and *after* their green energy choices. Frame the annual reduction in a powerful way.
                    4.  **Actionable Recommendations:** Provide 3 clear, personalized recommendations for further reducing their footprint, based on their specific data.
                    5.  **Concluding Encouragement:** End with a positive and encouraging message.
                    make it engaging, Summarize at first and if person want to read more show the longer version. Use bullet points, headings, and formatting to enhance readability.
                    """
                    
                    initial_api_call_history = [{"role": "user", "parts": [{"text": initial_prompt_text}]}]
                    ai_response = get_gemini_response(initial_api_call_history)
                    
                    # Add the AI's first message to the chat history
                    st.session_state.messages.append({"role": "assistant", "content": ai_response})

            # Display entire chat history
            for message in st.session_state.messages:
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])

            # Get user input from chat box
            if prompt := st.chat_input("Ask a follow-up question..."):
                st.session_state.messages.append({"role": "user", "content": prompt})
                with st.chat_message("user"):
                    st.markdown(prompt)

                with st.chat_message("assistant"):
                    with st.spinner("Thinking..."):
                        # Prepare the full conversation history for the API
                        api_history = [
                            {"role": "model" if msg["role"] == "assistant" else "user", "parts": [{"text": msg["content"]}]}
                            for msg in st.session_state.messages
                        ]
                        
                        response = get_gemini_response(api_history)
                        st.markdown(response)
                
                st.session_state.messages.append({"role": "assistant", "content": response})