"""
Trimite fiecare anunț agentului `ubb-news-agent` din Microsoft Foundry.
Instrucțiunile agentului sunt salvate in Foundry, nu in cod.
Autentificare: Microsoft Entra ID (local: `az login`; in GitHub Actions: OIDC).
"""
import json
import os
import re

from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv

from fetch_feed import fetch_announcements, format_for_agent

load_dotenv()

PROJECT_ENDPOINT = os.environ["FOUNDRY_PROJECT_ENDPOINT"]
AGENT_NAME = os.environ.get("FOUNDRY_AGENT_NAME", "ubb-news-agent")
AGENT_VERSION = os.environ.get("FOUNDRY_AGENT_VERSION")

AGENT_REF = {"name": AGENT_NAME, "type": "agent_reference"}
if AGENT_VERSION:
    AGENT_REF["version"] = AGENT_VERSION

project = AIProjectClient(endpoint=PROJECT_ENDPOINT, credential=DefaultAzureCredential())
openai_client = project.get_openai_client()


def parse_json(text: str) -> dict:
    text = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.MULTILINE).strip()
    return json.loads(text)


def classify(announcement: dict) -> tuple[dict, int]:
    try:
        response = openai_client.responses.create(
            input=[{"role": "user", "content": format_for_agent(announcement)}],
            extra_body={"agent_reference": AGENT_REF},
        )
        result = parse_json(response.output_text)
        tokens = response.usage.total_tokens if response.usage else 0
    except Exception as e:
        result = {"relevant": None, "motiv": f"Eroare la clasificare: {e}", "rezumat": ""}
        tokens = 0

    result["link"] = announcement["link"]
    result["data"] = announcement["data"]
    return result, tokens


if __name__ == "__main__":
    total_tokens = 0
    for a in fetch_announcements():
        verdict, tokens = classify(a)
        total_tokens += tokens
        mark = {True: "RELEVANT", False: "IRELEVANT", None: "EROARE"}[verdict.get("relevant")]
        print(f"{mark} | {a['titlu']}")
        print(f"   motiv:   {verdict.get('motiv')}")
        print(f"   rezumat: {verdict.get('rezumat')}")
        print(f"   link:    {verdict['link']}\n")
    print(f"Total tokeni folosiți: {total_tokens}")
