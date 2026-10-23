"""Flight lookup tool backed by the Aviationstack API."""
import os

import requests
from langchain_core.tools import tool


@tool
def search_flights(dep_iata: str, arr_iata: str, limit: int = 8) -> str:
    """Look up flights between two airports using Aviationstack.

    Args:
        dep_iata: 3-letter IATA code of the departure airport (e.g. "JNB").
        arr_iata: 3-letter IATA code of the arrival airport (e.g. "CPT").
        limit: Maximum number of flights to return (default 8).

    Returns a text list with airline, flight number, status, scheduled
    departure/arrival times and terminals. Aviationstack returns real-time and
    recent schedule data, so treat times as indicative for future dates.
    """
    api_key = os.getenv("AVIATIONSTACK_API_KEY")
    if not api_key:
        return "Error: AVIATIONSTACK_API_KEY is not set."

    base_url = os.getenv("AVIATIONSTACK_BASE_URL", "http://api.aviationstack.com/v1")
    params = {
        "access_key": api_key,
        "dep_iata": dep_iata.strip().upper(),
        "arr_iata": arr_iata.strip().upper(),
        "limit": limit,
    }

    try:
        resp = requests.get(f"{base_url}/flights", params=params, timeout=20)
        resp.raise_for_status()
        payload = resp.json()
    except requests.RequestException as exc:
        return f"Error calling Aviationstack: {exc}"

    if "error" in payload:
        err = payload["error"]
        return f"Aviationstack error: {err.get('message', err)}"

    flights = payload.get("data") or []
    if not flights:
        return (
            f"No flights found from {params['dep_iata']} to {params['arr_iata']}. "
            "Try a web search for airlines serving this route instead."
        )

    lines = []
    for f in flights[:limit]:
        airline = (f.get("airline") or {}).get("name", "Unknown airline")
        number = (f.get("flight") or {}).get("iata", "N/A")
        dep = f.get("departure") or {}
        arr = f.get("arrival") or {}
        lines.append(
            f"- {airline} {number} | status: {f.get('flight_status', 'n/a')} | "
            f"dep {dep.get('airport', params['dep_iata'])} "
            f"{dep.get('scheduled', 'n/a')} (terminal {dep.get('terminal') or 'n/a'}) | "
            f"arr {arr.get('airport', params['arr_iata'])} "
            f"{arr.get('scheduled', 'n/a')} (terminal {arr.get('terminal') or 'n/a'})"
        )
    return "\n".join(lines)
