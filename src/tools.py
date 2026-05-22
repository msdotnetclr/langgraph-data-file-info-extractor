from langchain_core.tools import tool

@tool
def get_weather(location: str) -> str:
    """Get the current weather for a given location. Use this to find out weather info."""
    loc = location.lower()
    if "london" in loc:
        return "It's 15°C and raining in London."
    elif "new york" in loc:
        return "It's 22°C and sunny in New York."
    elif "tokyo" in loc:
        return "It's 18°C and cloudy in Tokyo."
    else:
        return f"The weather in {location} is 20°C and partly cloudy."

# List of tools to export
tools = [get_weather]
