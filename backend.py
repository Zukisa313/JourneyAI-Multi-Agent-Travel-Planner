"""LangGraph pipeline: flight agent -> hotel agent -> itinerary agent -> final agent."""
import os
from typing import TypedDict

from langchain_groq import ChatGroq
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import create_react_agent

from tools import search_flights, web_search


class TripState(TypedDict, total=False):
    # user input
    origin: str
    destination: str
    start_date: str
    end_date: str
    travelers: int
    budget: str
    interests: str
    # agent outputs
    flight_info: str
    hotel_info: str
    itinerary: str
    final_response: str


def _llm() -> ChatGroq:
    # Groq's free tier has tight tokens-per-minute limits, so keep outputs
    # modest and let the client retry automatically on 429s.
    return ChatGroq(
        model=os.getenv("MODEL_NAME", "llama-3.3-70b-versatile"),
        temperature=0.3,
        max_tokens=2048,
        max_retries=4,
    )


def _text(content) -> str:
    """Normalise message content (str or list of blocks) to plain text."""
    if isinstance(content, str):
        return content
    return "".join(
        b.get("text", "") if isinstance(b, dict) else str(b) for b in content
    )


def _run_agent(agent, prompt: str) -> str:
    result = agent.invoke({"messages": [("user", prompt)]})
    return _text(result["messages"][-1].content)


def _trip_summary(s: TripState) -> str:
    return (
        f"Origin: {s['origin']}\n"
        f"Destination: {s['destination']}\n"
        f"Dates: {s['start_date']} to {s['end_date']}\n"
        f"Travelers: {s.get('travelers', 1)}\n"
        f"Budget: {s.get('budget') or 'not specified'}\n"
        f"Interests: {s.get('interests') or 'general sightseeing'}"
    )


# ---------------------------------------------------------------- agents
def _build_agents():
    llm = _llm()

    flight_agent = create_react_agent(
        llm,
        tools=[search_flights, web_search],
        prompt=(
            "You are a flight research agent. Work out the IATA codes for the "
            "origin and destination cities, call search_flights for the route, "
            "and use web_search for typical fares and airlines if flight data is "
            "thin. Return 3 concise flight options with airline, flight number, "
            "times and approximate price when known. Be honest about what is "
            "real-time data versus an estimate."
        ),
    )

    hotel_agent = create_react_agent(
        llm,
        tools=[web_search],
        prompt=(
            "You are a hotel research agent. Use web_search to find 3 hotel "
            "options (budget, mid-range, premium unless the budget says "
            "otherwise) in good areas for the traveler's interests. For each give "
            "name, neighbourhood, approximate nightly price, and why it fits."
        ),
    )

    itinerary_agent = create_react_agent(
        llm,
        tools=[web_search],
        prompt=(
            "You are an itinerary planning agent. Use web_search to verify "
            "attractions, restaurants and local transport. Build a realistic "
            "day-by-day plan with morning, afternoon and evening blocks, "
            "grouping nearby places together and leaving time for rest."
        ),
    )
    return flight_agent, hotel_agent, itinerary_agent, llm


flight_agent, hotel_agent, itinerary_agent, final_llm = _build_agents()


# ----------------------------------------------------------------- nodes
def flight_node(state: TripState) -> TripState:
    prompt = f"Find flights for this trip:\n{_trip_summary(state)}"
    return {"flight_info": _run_agent(flight_agent, prompt)}


def hotel_node(state: TripState) -> TripState:
    prompt = (
        f"Find hotels for this trip:\n{_trip_summary(state)}\n\n"
        f"Flight context (for arrival/departure timing):\n{state['flight_info']}"
    )
    return {"hotel_info": _run_agent(hotel_agent, prompt)}


def itinerary_node(state: TripState) -> TripState:
    prompt = (
        f"Create a day-by-day itinerary:\n{_trip_summary(state)}\n\n"
        f"Flights:\n{state['flight_info']}\n\nHotels:\n{state['hotel_info']}"
    )
    return {"itinerary": _run_agent(itinerary_agent, prompt)}


def final_node(state: TripState) -> TripState:
    prompt = (
        "You are the final response agent for a trip planner. Combine the work "
        "of the other agents into one polished Markdown travel plan with these "
        "sections: Trip overview, Flights, Where to stay, Day-by-day itinerary, "
        "Estimated budget, and Practical tips. Keep facts consistent with the "
        "inputs, don't invent prices, and flag anything that should be verified "
        "before booking.\n\n"
        f"TRIP:\n{_trip_summary(state)}\n\n"
        f"FLIGHT AGENT:\n{state['flight_info']}\n\n"
        f"HOTEL AGENT:\n{state['hotel_info']}\n\n"
        f"ITINERARY AGENT:\n{state['itinerary']}"
    )
    reply = final_llm.invoke(prompt)
    return {"final_response": _text(reply.content)}


# ----------------------------------------------------------------- graph
def build_graph():
    g = StateGraph(TripState)
    g.add_node("flight_agent", flight_node)
    g.add_node("hotel_agent", hotel_node)
    g.add_node("itinerary_agent", itinerary_node)
    g.add_node("final_agent", final_node)

    g.add_edge(START, "flight_agent")
    g.add_edge("flight_agent", "hotel_agent")
    g.add_edge("hotel_agent", "itinerary_agent")
    g.add_edge("itinerary_agent", "final_agent")
    g.add_edge("final_agent", END)
    return g.compile()


graph = build_graph()
