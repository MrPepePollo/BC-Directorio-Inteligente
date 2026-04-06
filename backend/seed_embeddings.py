"""
Seed script: Generate OpenAI embeddings for all providers and update the database.
Run from backend/: python seed_embeddings.py
"""
import asyncio
import os
import sys

import openai
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_SERVICE_KEY = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]
EMBEDDING_MODEL = "text-embedding-3-small"

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
oai = openai.OpenAI(api_key=OPENAI_API_KEY)


def main():
    # Fetch all providers without embeddings
    result = (
        supabase.table("providers")
        .select("id, name, description")
        .is_("embedding", "null")
        .is_("deleted_at", "null")
        .execute()
    )
    providers = result.data
    if not providers:
        print("All providers already have embeddings.")
        return

    print(f"Generating embeddings for {len(providers)} providers...")

    # Batch embed all descriptions at once
    descriptions = [p["description"] for p in providers]
    response = oai.embeddings.create(model=EMBEDDING_MODEL, input=descriptions)

    for provider, emb_data in zip(providers, response.data):
        embedding = emb_data.embedding
        supabase.table("providers").update(
            {"embedding": embedding}
        ).eq("id", provider["id"]).execute()
        print(f"  ✓ {provider['name']}")

    print(f"\nDone! {len(providers)} embeddings generated and stored.")


if __name__ == "__main__":
    main()
