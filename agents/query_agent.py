"""
agents/query_agent.py
=====================
The Query Agent - the first step in the SmartLogix pipeline.

Job: read a plain-English delivery request from a customer, e.g.

    "Send a fridge from Colombo to Kandy at the lowest cost"

and return a clean Python dictionary the Inventory Agent can use:

    {"origin": "Colombo", "destination": "Kandy",
     "item": "fridge", "need": "cheapest"}

It uses two tools:
  * spaCy (en_core_web_sm) - runs offline, instantly. Spots "named entities"
    such as place names in a sentence. Used here as a hint for the LLM and
    as a backup if the LLM call fails.
  * Groq (a Llama model) - a Large Language Model in the cloud. It reads the
    whole sentence and returns the four structured fields as JSON.

Run it on its own to test:
    python agents/query_agent.py

First time only, download the spaCy model:
    python -m spacy download en_core_web_sm
"""

import json
import os

from dotenv import load_dotenv
import spacy
from groq import Groq

# Load the .env file first, so every os.getenv() call below can see its values.
load_dotenv()


# --- Settings --------------------------------------------------------------
SPACY_MODEL = "en_core_web_sm"
# Model list: https://console.groq.com/docs/models  (change via .env if needed)
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

# Every result from this agent must have exactly these keys, in this order.
REQUIRED_KEYS = ("origin", "destination", "item", "need")
VALID_NEEDS = ("cheapest", "fastest", "standard")

# Words that hint at what the customer cares about. Used as a backup when the
# LLM does not give a clear "need" value.
CHEAP_WORDS = ("cheap", "cheapest", "low cost", "lowest cost", "least cost",
               "budget", "economy", "economical", "affordable", "save money")
FAST_WORDS = ("fast", "fastest", "quick", "quickest", "urgent", "urgently",
              "express", "asap", "immediately", "today", "same day",
              "same-day", "rush", "priority", "overnight")


# --- Initialize the tools once, when this file is first imported -----------
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

try:
    nlp = spacy.load(SPACY_MODEL)
except OSError as exc:
    raise RuntimeError(
        f"spaCy model '{SPACY_MODEL}' is not installed.\n"
        f"Fix it by running:  python -m spacy download {SPACY_MODEL}"
    ) from exc

if not GROQ_API_KEY:
    raise RuntimeError(
        "GROQ_API_KEY not found. Open the .env file in the project root and "
        "add a line like:  GROQ_API_KEY=gsk_your_key_here"
    )
groq_client = Groq(api_key=GROQ_API_KEY)


# --- Small helper ---------------------------------------------------------
def _dedupe(items):
    """Remove duplicates from a list but keep the first-seen order."""
    return list(dict.fromkeys(items))


# --- Step 1: spaCy entity check ------------------------------------------------
def extract_entities(text: str) -> dict:
    """Use spaCy to pull out named entities as *hints*.

    Returns e.g. {"places": ["Colombo", "Kandy"], "products": ["fridge"]}.
    spaCy's small model is not trained on Sri Lankan city names, so this is
    a helpful guess only - never the final answer.
    """
    doc = nlp(text)
    places, products = [], []
    for ent in doc.ents:
        if ent.label_ in ("GPE", "LOC"):        # GPE = country / city / state
            places.append(ent.text)
        elif ent.label_ in ("PRODUCT", "ORG"):  # items sometimes land here
            products.append(ent.text)

    return {"places": _dedupe(places), "products": _dedupe(products)}


# --- Step 2: ask the Groq LLM -----------------------------------------------
SYSTEM_PROMPT = (
    "You extract structured shipping details for SmartLogix, a Sri Lankan "
    "logistics company. Read the customer's request and reply with ONLY a "
    "JSON object that has EXACTLY these four keys:\n"
    '  "origin"      - the city the item is sent FROM (string)\n'
    '  "destination" - the city the item is sent TO (string)\n'
    '  "item"        - the product being shipped (short, singular, lowercase)\n'
    '  "need"        - exactly one of: "cheapest", "fastest", "standard"\n'
    "\n"
    "Guidance:\n"
    '- cost / cheap / budget / "lowest price"      -> need = "cheapest"\n'
    '- urgent / fast / express / today / same-day  -> need = "fastest"\n'
    '- nothing specific about speed or price       -> need = "standard"\n'
    '- If a city or item is missing, use an empty string "".\n'
    "- Write city names with a capital letter (Colombo, Kandy, Jaffna).\n"
    "- Return only the JSON object. No comments, no extra text."
)


def _build_user_prompt(user_request: str, entities: dict) -> str:
    """Combine the raw request with the spaCy hint into one message."""
    prompt = f'Customer request: "{user_request.strip()}"'
    if entities["places"]:
        prompt += (
            f"\n\nA name-detector guessed these might be places: "
            f"{entities['places']}. Check them yourself - they may be wrong."
        )
    return prompt


def _ask_groq(user_request: str, entities: dict) -> dict:
    """Send the prompt to Groq and return the parsed JSON as a dict.

    May raise a network error, or json.JSONDecodeError if the reply is not
    valid JSON. The caller (process_query) handles those.
    """
    completion = groq_client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": _build_user_prompt(user_request, entities)},
        ],
        temperature=0,                            # 0 = stable, repeatable output
        response_format={"type": "json_object"},  # force a valid JSON reply
    )
    reply_text = completion.choices[0].message.content or "{}"
    return json.loads(reply_text)


# --- Step 3: clean up and guarantee the 4 keys ----------------------------
def _keyword_need(text: str) -> str:
    """Backup guess for 'need', taken straight from the customer's words."""
    low = text.lower()
    if any(word in low for word in CHEAP_WORDS):
        return "cheapest"
    if any(word in low for word in FAST_WORDS):
        return "fastest"
    return "standard"


def _clean_result(data: dict, user_request: str, entities: dict) -> dict:
    """Return a dict with EXACTLY origin, destination, item, need."""
    # Start from a safe backup built from spaCy + keyword guessing.
    places = entities.get("places", [])
    products = entities.get("products", [])
    result = {
        "origin": places[0] if len(places) >= 1 else "",
        "destination": places[1] if len(places) >= 2 else "",
        "item": products[0].lower() if products else "",
        "need": _keyword_need(user_request),
    }

    # Override with the LLM's answer wherever it gave a non-empty string.
    if isinstance(data, dict):
        for key in REQUIRED_KEYS:
            value = data.get(key)
            if isinstance(value, str) and value.strip():
                result[key] = value.strip()

    # Final check on 'need': it must be one of the three allowed words.
    if result["need"] not in VALID_NEEDS:
        result["need"] = _keyword_need(user_request)

    # Return the keys in a fixed order, with nothing extra attached.
    return {key: result[key] for key in REQUIRED_KEYS}


# --- The public function the rest of SmartLogix calls --------------------
def process_query(user_request: str) -> dict:
    """Turn a plain-English delivery request into a structured dict.

    Always returns: {"origin": str, "destination": str, "item": str, "need": str}
    Never raises - on any problem it falls back to a best-effort guess so the
    Inventory Agent still receives a usable dictionary.
    """
    if not user_request or not user_request.strip():
        print("[query_agent] Got an empty request.")
        return {"origin": "", "destination": "", "item": "", "need": "standard"}

    # Step 1 - offline entity check with spaCy
    entities = extract_entities(user_request)

    # Step 2 - main extraction with the Groq LLM
    llm_data: dict = {}
    try:
        llm_data = _ask_groq(user_request, entities)
    except json.JSONDecodeError as exc:
        print(f"[query_agent] Groq reply was not valid JSON: {exc}")
    except Exception as exc:  # no internet, bad key, wrong model name, etc.
        print(f"[query_agent] Groq request failed ({type(exc).__name__}): {exc}")

    # Step 3 - tidy up and guarantee the 4 keys
    return _clean_result(llm_data, user_request, entities)


# --- Run this file directly to test it -----------------------------------
if __name__ == "__main__":
    sample_queries = [
        "Send a fridge from Colombo to Kandy at the lowest cost",
        "I need to urgently ship a laptop from Galle to Jaffna today",
        "Deliver a box of documents from Negombo to Matara",
        "cheapest way to move a sofa from Kurunegala to Anuradhapura",
    ]

    print("SmartLogix Query Agent - test run")
    print("=" * 45)
    for query in sample_queries:
        print(f"\nRequest : {query}")
        print(f"Result  : {process_query(query)}")
