from app.config import settings


def get_ai_response(prompt: str, system: str) -> str:
    provider = settings.ai_provider.lower()
    if provider == "groq":
        return _groq(prompt, system)
    elif provider == "gemini":
        return _gemini(prompt, system)
    elif provider == "huggingface":
        return _huggingface(prompt, system)
    raise ValueError(f"Unknown AI_PROVIDER: {provider!r}")


def _groq(prompt: str, system: str) -> str:
    from groq import Groq
    client = Groq(api_key=settings.groq_api_key)
    resp = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
    )
    return resp.choices[0].message.content


def _gemini(prompt: str, system: str) -> str:
    import google.generativeai as genai
    genai.configure(api_key=settings.gemini_api_key)
    model = genai.GenerativeModel("gemini-1.5-flash", system_instruction=system)
    return model.generate_content(prompt).text


def _huggingface(prompt: str, system: str) -> str:
    from huggingface_hub import InferenceClient
    client = InferenceClient(token=settings.huggingface_api_key)
    resp = client.chat_completion(
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        model="mistralai/Mistral-7B-Instruct-v0.3",
    )
    return resp.choices[0].message.content
