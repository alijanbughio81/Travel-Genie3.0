# 🧞 TravelGenie

A multi-agent trip planner. Six AI agents (Flights, Hotels, Activities, Weather, Budget, Itinerary) work together — via Groq's `openai/gpt-oss-120b` — to plan an entire trip from a single form.

Built with **Streamlit**, **Groq**, and **python-dotenv**.

---

## ✨ Features

- 🛫 **Flight agent** — 5 realistic flight options
- 🏨 **Hotel agent** — 5 hotel options across price points
- 🎯 **Activities agent** — 8 things to do, balanced by your preferences
- 🌤️ **Weather agent** — real Open-Meteo forecast; shown **only when the whole trip fits inside the 16-day forecast window** (otherwise the weather tab is hidden)
- 💰 **Budget agent** — picks the best fit for your budget
- 🗓️ **Itinerary agent** — day-by-day plan with weather-aware ordering
- 📥 Downloadable itinerary as **JSON** or **TXT**

---

## 📁 Project layout

```
travelgenie/
├── app.py               # Streamlit UI (run this)
├── flight.py            # ✈️ Flight agent
├── hotel.py             # 🏨 Hotel agent
├── activities.py        # 🎯 Activities agent
├── weather.py           # 🌤️ Weather agent
├── budget.py            # 💰 Budget agent
├── itinerary.py         # 🗓️ Itinerary agent
├── requirements.txt
├── .env.example         # template for your Groq key
└── README.md
```

---

## 🚀 Run locally

1. **Clone the repo**
   ```bash
   git clone https://github.com/<your-username>/travelgenie.git
   cd travelgenie
   ```

2. **Create a virtual env (recommended)**
   ```bash
   python -m venv .venv
   source .venv/bin/activate          # macOS / Linux
   # .venv\Scripts\activate           # Windows
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Add your Groq API key** — get one free at [console.groq.com](https://console.groq.com):
   ```bash
   cp .env.example .env
   # then edit .env and put your real key in GROQ_API_KEY
   ```

5. **Run the app**
   ```bash
   streamlit run app.py
   ```
   Open the URL Streamlit prints (usually `http://localhost:8501`).

---

## ☁️ Deploy to Streamlit Community Cloud

1. Push the project to a GitHub repo (e.g. `yourname/travelgenie`).

2. Go to [share.streamlit.io](https://share.streamlit.io) → **New app**.

3. Pick the repo + branch, set **Main file path** to `app.py`.

4. Click **Advanced settings** → **Secrets**, and paste:
   ```toml
   GROQ_API_KEY = "your_groq_api_key_here"
   ```

5. Hit **Deploy**. Done. The app will rebuild on every `git push` to the chosen branch.

> 💡 **Tip:** Streamlit Cloud reads `secrets.toml` and exposes it as `os.environ`, which is exactly how `app.py` is already reading it — no code changes needed.

---

## 🔁 Switching the model

All six agents default to `openai/gpt-oss-120b`. To use a different Groq model, search for that string in each agent file and replace it. Popular options:

- `llama-3.3-70b-versatile`
- `llama-3.1-8b-instant` (faster, cheaper)
- `mixtral-8x7b-32768`

---

## 💡 Suggestions for next steps

These are easy upgrades you could add:

| Idea | How |
|---|---|
| ~~**Live weather**~~ | ✅ Already done — `weather.py` calls Open-Meteo `/v1/forecast` (real data, no key). Skipped entirely when the trip falls outside the 16-day window. |
| **Live flights / hotels** | Wire in [Tavily](https://tavily.com/) or [SerpAPI](https://serpapi.com/) for real-time search grounding — same pattern. |
| **Currency picker** | Add a sidebar dropdown and convert PKR → user-chosen currency in `app.py`. |
| **Save trips** | Persist results to SQLite / Firebase so users can revisit past plans. |
| **Auth** | Streamlit supports OAuth via `st.user` — restrict the app to a small user list. |
| **Streaming UI** | Use `st.write_stream` to stream each agent's tokens as they're generated. |
| **PDF export** | Add `fpdf2` and render the itinerary as a polished PDF. |

---

## ⚠️ Notes on data accuracy

The Flight / Hotel / Activities agents rely on the LLM's own knowledge of typical prices and attractions, not live booking APIs. Numbers are best-effort estimates, not guaranteed fares.

For a production-grade version, plug each agent into a real search / booking API (Amadeus, Skyscanner, Booking.com, etc.) — the prompt contract in each agent already produces the right structured output, so swapping the data source should be straightforward.

---

## 📜 License

MIT — do whatever you want with it.
