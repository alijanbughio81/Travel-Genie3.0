import os
import json
from groq import Groq
from dotenv import load_dotenv

load_dotenv()
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
 
 
def build_itinerary(budget_summary, weather, duration):
    """
    Takes the budget agent's already-decided choices (flight, hotel, activities)
    plus weather, and arranges them into a day-by-day schedule.
    This agent does NOT choose what to include anymore — budget_agent already did that.
    It only organizes timing/order.
 
    Inputs:
        budget_summary: dict from budget_agent.calculate_budget()
                         (contains chosen_flight, chosen_hotel, chosen_activities, etc.)
        weather: list of daily forecast dicts
        duration: number of days in the trip
 
    Returns:
        list of day dicts, e.g.:
        [
          {
            "day": 1,
            "date": "2025-10-12",
            "weather": "Sunny, 28°C",
            "flight": {...} or null,
            "hotel": {...},
            "activities": [{"time": "10:00 AM", "activity": "Faisal Mosque", "cost": 0}],
            "estimated_day_cost": 8500
          },
          ...
        ]
    """
 
    chosen_flight = budget_summary.get("chosen_flight")
    chosen_hotel = budget_summary.get("chosen_hotel")
    chosen_activities = budget_summary.get("chosen_activities", [])
 
    prompt = f"""
You are a travel itinerary planning assistant.
 
Trip length: {duration} days
 
Chosen flight (already decided, use as-is): {json.dumps(chosen_flight)}
Chosen hotel (already decided, use as-is): {json.dumps(chosen_hotel)}
Chosen activities (already decided, use as-is — do not add or remove any): {json.dumps(chosen_activities)}
Weather forecast per day: {json.dumps(weather)}
 
Task:
1. Build a day-by-day plan for all {duration} days using ONLY the flight, hotel, and activities given above.
2. Put the flight on day 1 (arrival), hotel applies across all days.
3. Spread the given activities sensibly across the days — don't invent new ones, don't drop any, just arrange timing and order.
4. Use the weather for each day to decide the best order (e.g. outdoor activities on sunnier days) — add a short note if weather affects a choice.
5. Estimate a total cost per day (share of hotel + that day's activities + flight if applicable that day).
 
Return ONLY valid JSON, no extra text, no markdown, as a JSON array in EXACTLY this format:
[
  {{
    "day": 1,
    "date": "<string, best guess or relative label like 'Day 1'>",
    "weather": "<short string>",
    "flight": <flight object or null>,
    "hotel": <hotel object>,
    "activities": [
      {{"time": "<string>", "activity": "<string>", "cost": <number>}}
    ],
    "estimated_day_cost": <number>
  }}
]
"""
 
    response = client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.4,
    )
 
    raw_text = response.choices[0].message.content.strip()
 
    try:
        return json.loads(raw_text)
    except json.JSONDecodeError:
        start = raw_text.find("[")
        end = raw_text.rfind("]") + 1
        try:
            return json.loads(raw_text[start:end])
        except Exception:
            return [{"day": 1, "date": "N/A", "weather": "N/A", "flight": None,
                      "hotel": None, "activities": [], "estimated_day_cost": 0}]
 
 
# quick manual test — run this file directly to check it works
if __name__ == "__main__":
    fake_budget_summary = {
        "chosen_flight": {"airline": "AirBlue", "price": 18000, "departure_time": "14:00", "arrival_time": "16:30"},
        "chosen_hotel": {"name": "Budget Inn", "price_per_night": 4500, "rating": 3.5},
        "rooms_needed": 2,
        "chosen_activities": [
            {"name": "Faisal Mosque", "estimated_cost": 0},
            {"name": "Lok Virsa Museum", "estimated_cost": 500},
        ],
        "total_estimated_cost": 93500,
        "user_budget": 100000,
        "within_budget": True,
        "breakdown": {"flights": 54000, "hotels": 36000, "activities": 1500, "misc": 2000},
        "suggestions": ["If you want to include Monal Restaurant Dinner, increase the budget by at least 9000 PKR.",
    "Consider allocating a slightly larger misc budget for food and local transport.",
    "You could upgrade to a higher\u2011rated hotel like Hotel Sunrise if the budget allows."],
    }
    fake_weather = [
                {"date": "2025-10-12", "condition": "Sunny", "temp_high": 28, "temp_low": 18},
                {"date": "2025-10-13", "condition": "Cloudy", "temp_high": 25, "temp_low": 17},
                {"date": "2025-10-14", "condition": "Rainy", "temp_high": 22, "temp_low": 15},
                {"date": "2025-10-15", "condition": "Partly Cloudy", "temp_high": 26, "temp_low": 16},
    ]
 
    result = build_itinerary(fake_budget_summary, fake_weather, duration=4)
    print(json.dumps(result, indent=2))