"""
TravelGenie — multi-agent trip planner.

A Streamlit front-end that fans out to:
  - Flight agent      (flight.py)
  - Hotel agent       (hotel.py)
  - Activities agent  (activities.py)
  - Weather agent     (weather.py)
  - Budget agent      (budget.py)
  - Itinerary agent   (itinerary.py)

All agents use Groq (openai/gpt-oss-120b by default).
"""

import os
import json
import datetime as dt
from typing import Any

import streamlit as st
from dotenv import load_dotenv

from flight import get_flights
from hotel import get_hotels
from activities import get_activities
from weather import get_weather
from budget import calculate_budget
from itinerary import build_itinerary

load_dotenv()

# --------------------------------------------------------------------------------------
# Page config
# --------------------------------------------------------------------------------------
st.set_page_config(
    page_title="TravelGenie",
    page_icon="🧞",
    layout="wide",
    initial_sidebar_state="expanded",
)

CURRENCY = "PKR"  # all agents are assumed to price in PKR per the original contracts


# Open-Meteo provides a maximum 16-day forecast.
FORECAST_DAYS_MAX = 16


def weather_available(start_date, duration: int) -> bool:
    """Return True only when the complete trip fits in Open-Meteo's 16-day window."""
    try:
        if isinstance(start_date, str):
            start = dt.date.fromisoformat(start_date)
        else:
            start = start_date

        today = dt.date.today()
        days_until_start = (start - today).days

        if duration > FORECAST_DAYS_MAX:
            return False

        forecast_coverage = FORECAST_DAYS_MAX - days_until_start
        return forecast_coverage >= duration

    except (TypeError, ValueError):
        return False



# --------------------------------------------------------------------------------------
# Small helpers
# --------------------------------------------------------------------------------------
def fmt_money(value: Any) -> str:
    """Format a number as PKR with thousands separator, or '—' if missing."""
    try:
        return f"{CURRENCY} {int(round(float(value))):,}"
    except (TypeError, ValueError):
        return "—"


def safe_get(d: dict | None, *keys, default=None):
    """Get nested dict keys without exploding."""
    cur = d
    for k in keys:
        if isinstance(cur, dict):
            cur = cur.get(k)
        else:
            return default
    return cur if cur is not None else default


def run_pipeline(origin, destination, start_date, duration, travelers, budget, preferences):
    """Run all six agents in order. Returns a dict of results."""
    results: dict[str, Any] = {}

    progress = st.progress(0.0, text="Starting TravelGenie agents…")
    status = st.status("Agents running…", expanded=True)

    # 1. Flights
    with status:
        st.write("✈️  Flight agent — searching options…")
        results["flights"] = get_flights(origin, destination, budget, travelers, duration)
    progress.progress(0.18, text="Flights done")

    # 2. Hotels
    with status:
        st.write("🏨  Hotel agent — searching options…")
        results["hotels"] = get_hotels(destination, budget, travelers, duration)
    progress.progress(0.34, text="Hotels done")

    # 3. Activities
    with status:
        st.write("🎯  Activities agent — finding things to do…")
        results["activities"] = get_activities(
            destination, budget, travelers, duration, preferences
        )
    progress.progress(0.50, text="Activities done")

    # 4. Weather
    with status:
        st.write("🌤️  Weather agent — building forecast…")

        # Only show/use weather when the complete trip fits
        # inside Open-Meteo's 16-day forecast window.
        if weather_available(start_date, duration):
            results["weather"] = get_weather(destination, start_date, duration)
        else:
            results["weather"] = []
    progress.progress(0.66, text="Weather done")

    # 5. Budget
    with status:
        st.write("💰  Budget agent — picking best fit…")
        results["budget"] = calculate_budget(
            results["flights"],
            results["hotels"],
            results["activities"],
            budget,
            travelers,
            duration,
        )
    progress.progress(0.84, text="Budget done")

    # 6. Itinerary
    with status:
        st.write("🗓️  Itinerary agent — building day-by-day plan…")
        results["itinerary"] = build_itinerary(
            results["budget"], results["weather"], duration
        )
    progress.progress(1.0, text="All done!")
    status.update(label="All agents finished ✅", state="complete")

    return results


# --------------------------------------------------------------------------------------
# Sidebar — inputs
# --------------------------------------------------------------------------------------
with st.sidebar:
    st.title("🧞 TravelGenie")
    st.caption("Multi-agent trip planner — flights, hotels, activities, weather, budget & itinerary in one go.")
    st.divider()

    with st.form("trip_form"):
        st.subheader("Trip details")

        origin = st.text_input("From (origin city)", value="Karachi, Pakistan")
        destination = st.text_input("To (destination city)", value="Istanbul, Turkey")

        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input(
                "Start date",
                value=dt.date.today(),
                min_value=dt.date.today(),
            )
        with col2:
            duration = st.number_input(
                "Trip length (nights)", min_value=1, max_value=30, value=4, step=1
            )

        col3, col4 = st.columns(2)
        with col3:
            travelers = st.number_input(
                "Travelers", min_value=1, max_value=20, value=2, step=1
            )
        with col4:
            budget = st.number_input(
                f"Total budget ({CURRENCY})",
                min_value=1000,
                max_value=10_000_000,
                value=150_000,
                step=5_000,
            )

        preferences = st.multiselect(
            "Activity preferences (optional)",
            ["culture", "food", "outdoor", "adventure", "shopping", "relaxation"],
            default=["culture", "food"],
            help="Used by the activities agent to balance its 8 suggestions.",
        )

        submit = st.form_submit_button(
            "✨ Plan my trip", use_container_width=True, type="primary"
        )

    st.divider()
    with st.expander("⚙️  Setup notes", expanded=False):
        st.markdown(
            """
1. Get a free Groq API key → [console.groq.com](https://console.groq.com)
2. Put it in `.env`:
   ```
   GROQ_API_KEY=your_key_here
   ```
3. Run locally: `streamlit run app.py`
4. Deploy to Streamlit Cloud: push to GitHub → [share.streamlit.io](https://share.streamlit.io) → set `GROQ_API_KEY` in **Secrets**.
"""
        )


# --------------------------------------------------------------------------------------
# Main area
# --------------------------------------------------------------------------------------
st.title("TravelGenie 🧞")
st.markdown(
    f"Tell me where you want to go, and I'll spin up **6 agents** to plan the whole trip — "
    f"flights, hotels, activities, weather, budget, and a day-by-day itinerary."
)

if not os.environ.get("GROQ_API_KEY"):
    st.error(
        "❌ `GROQ_API_KEY` not found. Add it to your `.env` file (local) or to "
        "Streamlit Secrets (deployed). See the setup notes in the sidebar."
    )
    st.stop()

# Run pipeline
if submit:
    if not origin.strip() or not destination.strip():
        st.warning("Please fill in both origin and destination.")
        st.stop()

    # Store everything in session_state so tabs can re-render without re-running agents
    st.session_state["pipeline_inputs"] = {
        "origin": origin,
        "destination": destination,
        "start_date": str(start_date),
        "duration": int(duration),
        "travelers": int(travelers),
        "budget": int(budget),
        "preferences": preferences,
    }
    st.session_state["results"] = run_pipeline(
        origin=origin,
        destination=destination,
        start_date=str(start_date),
        duration=int(duration),
        travelers=int(travelers),
        budget=int(budget),
        preferences=preferences or None,
    )

results = st.session_state.get("results")
inputs = st.session_state.get("pipeline_inputs")

# --------------------------------------------------------------------------------------
# Display results in tabs
# --------------------------------------------------------------------------------------
if results and inputs:
    has_weather = bool(results.get("weather"))

    if has_weather:
        (
            tab_summary, tab_flights, tab_hotels, tab_activities,
            tab_weather, tab_budget, tab_itinerary,
        ) = st.tabs(
            ["📌 Summary", "✈️ Flights", "🏨 Hotels", "🎯 Activities", "🌤️ Weather", "💰 Budget", "🗓️ Itinerary"]
        )
    else:
        (
            tab_summary, tab_flights, tab_hotels, tab_activities,
            tab_budget, tab_itinerary,
        ) = st.tabs(
            ["📌 Summary", "✈️ Flights", "🏨 Hotels", "🎯 Activities", "💰 Budget", "🗓️ Itinerary"]
        )

    # --- SUMMARY ----------------------------------------------------------------------
    with tab_summary:
        st.subheader(f"Trip to {inputs['destination']} from {inputs['origin']}")

        if not has_weather:
            st.info(
                "ℹ️ **Weather forecast not shown** — Open-Meteo provides a maximum "
                "16-day forecast. Weather is shown only when the complete trip fits "
                "inside the available forecast window."
            )

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Duration", f"{inputs['duration']} nights")
        c2.metric("Travelers", inputs["travelers"])
        c3.metric("Budget", fmt_money(inputs["budget"]))
        b = results.get("budget") or {}
        c4.metric(
            "Estimated total",
            fmt_money(b.get("total_estimated_cost")),
            delta=(
                f"{fmt_money(inputs['budget'] - b.get('total_estimated_cost', 0))} under budget"
                if b.get("within_budget")
                else f"{fmt_money(b.get('total_estimated_cost', 0) - inputs['budget'])} over budget"
            ),
            delta_color="normal" if b.get("within_budget") else "inverse",
        )

        st.markdown("##### Picked by the budget agent")
        picked_flight = safe_get(b, "chosen_flight")
        picked_hotel = safe_get(b, "chosen_hotel")
        picked_acts = safe_get(b, "chosen_activities", default=[]) or []

        sc1, sc2 = st.columns(2)
        with sc1:
            st.markdown("**✈️ Flight**")
            if picked_flight:
                st.markdown(
                    f"- **{picked_flight.get('airline', '—')}** — "
                    f"{picked_flight.get('from', '—')} → {picked_flight.get('to', '—')}\n"
                    f"- {picked_flight.get('departure_time', '—')} → {picked_flight.get('arrival_time', '—')}\n"
                    f"- {fmt_money(picked_flight.get('price'))} per person"
                )
            else:
                st.caption("No flight picked.")
        with sc2:
            st.markdown("**🏨 Hotel**")
            if picked_hotel:
                st.markdown(
                    f"- **{picked_hotel.get('name', '—')}** ({picked_hotel.get('location', '—')})\n"
                    f"- Rating: {picked_hotel.get('rating', '—')} ⭐\n"
                    f"- {fmt_money(picked_hotel.get('price_per_night'))} / night "
                    f"× {b.get('rooms_needed', '—')} room(s)"
                )
            else:
                st.caption("No hotel picked.")

        st.markdown("**🎯 Picked activities**")
        if picked_acts:
            for a in picked_acts:
                st.markdown(
                    f"- **{a.get('name', '—')}** "
                    f"({a.get('category', '—')}, {fmt_money(a.get('estimated_cost', 0))} / person) — "
                    f"{a.get('description', '')}"
                )
        else:
            st.caption("No activities picked.")

    # --- FLIGHTS ----------------------------------------------------------------------
    with tab_flights:
        st.subheader("Flight options")
        flights = results.get("flights") or []
        if flights:
            st.dataframe(
                [
                    {
                        "Airline": f.get("airline"),
                        "From": f.get("from"),
                        "To": f.get("to"),
                        "Departure": f.get("departure_time"),
                        "Arrival": f.get("arrival_time"),
                        f"Price/person ({CURRENCY})": f.get("price"),
                        f"× {inputs['travelers']} travelers": (
                            (f.get("price") or 0) * inputs["travelers"]
                        ),
                    }
                    for f in flights
                ],
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.warning("No flights returned.")

    # --- HOTELS -----------------------------------------------------------------------
    with tab_hotels:
        st.subheader("Hotel options")
        hotels = results.get("hotels") or []
        if hotels:
            for h in hotels:
                with st.container(border=True):
                    c1, c2 = st.columns([3, 1])
                    with c1:
                        st.markdown(f"### {h.get('name', '—')}")
                        st.caption(
                            f"📍 {h.get('location', '—')}  ·  ⭐ {h.get('rating', '—')}"
                        )
                        am = h.get("amenities") or []
                        if am:
                            st.markdown(" · ".join(f"`{a}`" for a in am))
                    with c2:
                        st.metric(
                            "Per night",
                            fmt_money(h.get("price_per_night")),
                            delta=f"× {inputs['duration']}n = {fmt_money((h.get('price_per_night') or 0) * inputs['duration'])}",
                            delta_color="off",
                        )
        else:
            st.warning("No hotels returned.")

    # --- ACTIVITIES -------------------------------------------------------------------
    with tab_activities:
        st.subheader("Activities & things to do")
        activities = results.get("activities") or []
        if activities:
            cols = st.columns(2)
            for i, a in enumerate(activities):
                with cols[i % 2]:
                    with st.container(border=True):
                        st.markdown(f"### {a.get('name', '—')}")
                        cat = (a.get("category") or "").lower()
                        emoji = {
                            "culture": "🏛️",
                            "food": "🍽️",
                            "outdoor": "🌳",
                            "adventure": "🪂",
                            "shopping": "🛍️",
                            "relaxation": "💆",
                        }.get(cat, "🎯")
                        st.caption(
                            f"{emoji} {a.get('category', '—').title()} · "
                            f"⏱️ {a.get('duration_hours', '—')} h · "
                            f"{a.get('best_time_of_day', '—')} · "
                            f"{a.get('indoor_outdoor', '—')}"
                        )
                        st.write(a.get("description", ""))
                        st.markdown(
                            f"**{fmt_money(a.get('estimated_cost', 0))}** / person · "
                            f"× {inputs['travelers']} = "
                            f"{fmt_money((a.get('estimated_cost') or 0) * inputs['travelers'])}"
                        )
        else:
            st.warning("No activities returned.")

    # --- WEATHER ----------------------------------------------------------------------
    if has_weather:
        with tab_weather:
            st.subheader("Weather forecast")
            st.caption("🟢 Real Open-Meteo forecast — your trip falls inside the 16-day forecast window.")

            weather = results.get("weather") or []
            st.dataframe(
                [
                    {
                        "Date": w.get("date"),
                        "Condition": w.get("condition"),
                        "High (°C)": w.get("temp_high"),
                        "Low (°C)": w.get("temp_low"),
                        "Rain %": w.get("precipitation_chance"),
                    }
                    for w in weather
                ],
                use_container_width=True,
                hide_index=True,
            )

    # --- BUDGET -----------------------------------------------------------------------
    with tab_budget:
        st.subheader("Budget breakdown")
        b = results.get("budget") or {}
        breakdown = b.get("breakdown") or {}

        if b:
            bc1, bc2, bc3, bc4 = st.columns(4)
            bc1.metric("Flights", fmt_money(breakdown.get("flights")))
            bc2.metric("Hotels", fmt_money(breakdown.get("hotels")))
            bc3.metric("Activities", fmt_money(breakdown.get("activities")))
            bc4.metric("Misc", fmt_money(breakdown.get("misc")))

            st.markdown("---")
            total = b.get("total_estimated_cost", 0) or 0
            user_b = b.get("user_budget", inputs["budget"])
            within = b.get("within_budget")
            if within:
                st.success(
                    f"✅ Total **{fmt_money(total)}** fits within budget of "
                    f"**{fmt_money(user_b)}** "
                    f"(slack: {fmt_money(user_b - total)})."
                )
            else:
                st.error(
                    f"❌ Total **{fmt_money(total)}** exceeds budget of "
                    f"**{fmt_money(user_b)}** "
                    f"(over by {fmt_money(total - user_b)})."
                )

            suggestions = b.get("suggestions") or []
            if suggestions:
                st.markdown("##### Suggestions")
                for s in suggestions:
                    st.markdown(f"- {s}")

            # Raw JSON for inspection
            with st.expander("Raw budget JSON"):
                st.json(b)
        else:
            st.warning("No budget data returned.")

    # --- ITINERARY --------------------------------------------------------------------
    with tab_itinerary:
        st.subheader("Day-by-day itinerary")
        if not has_weather:
            st.caption(
                "ℹ️ Weather info not shown — the complete trip does not fit "
                "inside Open-Meteo's 16-day forecast window."
            )
        itinerary = results.get("itinerary") or []
        if itinerary:
            for day in itinerary:
                with st.container(border=True):
                    d_num = day.get("day")
                    d_date = day.get("date", "")
                    d_weather = day.get("weather", "—") if has_weather else "Weather info unavailable"
                    st.markdown(f"### Day {d_num} — {d_date}")
                    if has_weather:
                        st.caption(f"🌤️ {d_weather}")
                    else:
                        st.caption(f"🌤️ {d_weather}")

                    flight = day.get("flight")
                    if flight:
                        st.markdown(
                            f"**✈️ Flight:** {flight.get('airline')} · "
                            f"{flight.get('from')} → {flight.get('to')} · "
                            f"{flight.get('departure_time')} → {flight.get('arrival_time')}"
                        )

                    hotel = day.get("hotel")
                    if hotel:
                        st.markdown(
                            f"**🏨 Stay:** {hotel.get('name')} · "
                            f"{fmt_money(hotel.get('price_per_night'))} / night"
                        )

                    acts = day.get("activities") or []
                    if acts:
                        st.markdown("**🎯 Plan:**")
                        for a in acts:
                            st.markdown(
                                f"- `{a.get('time', '—')}` — **{a.get('activity', '—')}** "
                                f"({fmt_money(a.get('cost', 0))})"
                            )
                    else:
                        st.caption("Free / flex day.")

                    st.markdown(
                        f"**Estimated day cost:** {fmt_money(day.get('estimated_day_cost', 0))}"
                    )

            # Download buttons
            st.markdown("---")
            st.markdown("##### Download")
            itinerary_json = json.dumps(itinerary, indent=2, ensure_ascii=False)

            # Plain-text summary
            txt_lines = [
                f"TravelGenie itinerary — {inputs['destination']}",
                f"From {inputs['origin']} · {inputs['duration']} nights · {inputs['travelers']} travelers",
                "",
            ]
            for day in itinerary:
                txt_lines.append(f"Day {day.get('day')} — {day.get('date')} ({day.get('weather')})")
                f = day.get("flight")
                if f:
                    txt_lines.append(
                        f"  ✈️ {f.get('airline')} {f.get('from')}→{f.get('to')} "
                        f"{f.get('departure_time')}–{f.get('arrival_time')}"
                    )
                h = day.get("hotel")
                if h:
                    txt_lines.append(f"  🏨 {h.get('name')}")
                for a in day.get("activities") or []:
                    txt_lines.append(f"  • {a.get('time')} — {a.get('activity')}")
                txt_lines.append("")
            itinerary_txt = "\n".join(txt_lines)

            dl1, dl2 = st.columns(2)
            with dl1:
                st.download_button(
                    "⬇️ Itinerary (JSON)",
                    data=itinerary_json,
                    file_name=f"travelgenie_itinerary_{inputs['destination'].replace(' ', '_')}.json",
                    mime="application/json",
                    use_container_width=True,
                )
            with dl2:
                st.download_button(
                    "⬇️ Itinerary (TXT)",
                    data=itinerary_txt,
                    file_name=f"travelgenie_itinerary_{inputs['destination'].replace(' ', '_')}.txt",
                    mime="text/plain",
                    use_container_width=True,
                )
        else:
            st.warning("No itinerary returned.")

else:
    # Empty state
    st.info("👈  Fill in your trip details in the sidebar and hit **Plan my trip** to get started.")

    st.markdown(
        """
### What each agent does

| Agent | Job |
|---|---|
| ✈️ **Flights** | Suggests 5 realistic flight options from origin → destination. |
| 🏨 **Hotels** | Suggests 5 hotels at varied price points in the destination. |
| 🎯 **Activities** | Suggests 8 things to do, balanced across categories you pick. |
| 🌤️ **Weather** | Real Open-Meteo forecast — only shown when the whole trip fits inside the 16-day window. |
| 💰 **Budget** | Picks the best flight + hotel + activities that fit your budget. |
| 🗓️ **Itinerary** | Arranges it all into a day-by-day plan with weather-aware ordering. |
"""
    )
