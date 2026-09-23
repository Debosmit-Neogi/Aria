from openai import OpenAI
from src.config import GROQ_API_KEY, GROQ_MODEL, BASE_URL, TEMPERATURE

_client = OpenAI(api_key=GROQ_API_KEY, base_url=BASE_URL)

def chat(messages, tools=None, tool_choice="auto", temperature=TEMPERATURE, model=None, max_tokens=400):
    kwargs = {
        "model": model or GROQ_MODEL,
        "messages": messages,
        "temperature": temperature,
    }
    if tools:
        kwargs["tools"] = tools
        kwargs["tool_choice"] = tool_choice
    return _client.chat.completions.create(**kwargs)
