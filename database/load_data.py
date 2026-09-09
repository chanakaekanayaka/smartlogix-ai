"""
database/load_data.py
=====================
Loads SmartLogix data into ChromaDB so the Retrieval Agent can search it.

-------------------------------------------------------------------------
WHAT IS AN EMBEDDING?  (read this if the word is new)
An embedding is a list of numbers (a "vector") that captures the *meaning*
of a piece of text. Texts with similar meaning get similar lists of numbers.
Example: "how are fragile items packed?" and "fragile goods use bubble wrap
and double boxing" would get vectors that sit close together, even though
they barely share any words.

We build these vectors with the "sentence-transformers" library using a
small, fast model called "all-MiniLM-L6-v2". It turns any text into a
vector of 384 numbers.

WHAT IS A VECTOR DATABASE?
A normal database finds rows by exact matches ("WHERE city = 'Kandy'").
A vector database (ChromaDB here) stores the meaning-vectors and, given a
question, returns the entries whose meaning is *closest*. That is how the
system can answer "which deliveries to the north were late?" without you
typing the exact keywords that appear in the data.

We save everything into a folder called "chroma_db/" so it stays on disk
and we do not have to rebuild it every time the app starts. This is called
"persistence".
-------------------------------------------------------------------------

This script creates two collections (think of them as two tables):
  * "deliveries" - one readable sentence per row of the CSV (1200 records)
  * "knowledge"  - the policy / packaging / FAQ text, split into chunks
"""

from pathlib import Path
import re

import pandas as pd
import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions


# --- Where things live --------------------------------------------------------
# __file__ is this script's path. .parent is the "database/" folder and
# .parent.parent is the project root, so these paths work no matter which
# folder you run the script from.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
CHROMA_DIR = PROJECT_ROOT / "chroma_db"

EMBED_MODEL_NAME = "all-MiniLM-L6-v2"
BATCH_SIZE = 100  # how many items we hand to ChromaDB at once


# --- Small helpers ------------------------------------------------------------
def find_file(folder: Path, wanted_name: str) -> Path:
    """Return the data file, tolerating browser-style names like 'name (1).csv'."""
    exact = folder / wanted_name
    if exact.exists():
        return exact
    stem, suffix = Path(wanted_name).stem, Path(wanted_name).suffix
    matches = sorted(folder.glob(f"{stem}*{suffix}"))
    if matches:
        return matches[0]
    raise FileNotFoundError(f"Could not find '{wanted_name}' in {folder}")


def to_int(value, default=0) -> int:
    """Safely turn a value into a whole number."""
    try:
        return int(float(value))
    except (ValueError, TypeError):
        return default


def to_float(value, default=0.0) -> float:
    """Safely turn a value into a decimal number."""
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


# --- Step 1: turn each CSV row into a readable sentence -----------------------
def build_delivery_documents(csv_path: Path):
    df = pd.read_csv(csv_path)
    print(f"  Read {len(df)} delivery rows from {csv_path.name}")

    documents, ids, metadatas = [], [], []
    for _, r in df.iterrows():
        days = to_int(r["Actual_Delivery_Days"])
        day_word = "day" if days == 1 else "days"
        exp_days = to_int(r["Expected_Delivery_Days"])
        exp_word = "day" if exp_days == 1 else "days"
        on_time = "on time" if to_int(r["On_Time"]) == 1 else "late"
        cost = to_int(r["Total_Cost_LKR"])
        pack_cost = to_int(r["Packaging_Cost_LKR"])

        # The sentence is what actually gets embedded and searched.
        sentence = (
            f"Delivery {r['Order_ID']} from {r['Origin_City']} to "
            f"{r['Destination_City']}, {to_int(r['Distance_km'])} km, carrying "
            f"{r['Product_Name']} ({r['Product_Category']}), {r['Weight_kg']} kg, "
            f"shipped from warehouse {r['Warehouse_ID']} ({r['Warehouse_Region']} "
            f"region) by {r['Vehicle_Type']} using {r['Delivery_Mode']} mode in "
            f"{r['Weather']} weather. Packaging: {r['Packaging_Type']} "
            f"(LKR {pack_cost}). Total cost LKR {cost}. Expected "
            f"{exp_days} {exp_word}, delivered in {days} {day_word}. "
            f"Status: {r['Delivery_Status']} ({on_time}). "
            f"Order date {r['Order_Date']}."
        )

        documents.append(sentence)
        ids.append(str(r["Order_ID"]))  # ChromaDB needs a unique id per item

        # Metadata = structured fields kept alongside the sentence. Later you
        # can filter on these, e.g. only search rows where status == "Delayed".
        # ChromaDB only allows text, numbers and true/false here (no lists).
        metadatas.append({
            "order_id": str(r["Order_ID"]),
            "origin": str(r["Origin_City"]),
            "destination": str(r["Destination_City"]),
            "distance_km": to_int(r["Distance_km"]),
            "product": str(r["Product_Name"]),
            "category": str(r["Product_Category"]),
            "weight_kg": to_float(r["Weight_kg"]),
            "vehicle": str(r["Vehicle_Type"]),
            "delivery_mode": str(r["Delivery_Mode"]),
            "weather": str(r["Weather"]),
            "warehouse_id": str(r["Warehouse_ID"]),
            "warehouse_region": str(r["Warehouse_Region"]),
            "status": str(r["Delivery_Status"]),
            "on_time": to_int(r["On_Time"]) == 1,
            "total_cost_lkr": cost,
        })

    return documents, ids, metadatas


# --- Step 2: split the knowledge base into chunks ----------------------------
def build_knowledge_documents(txt_path: Path):
    """Split the text on blank lines and keep the section title with each chunk.

    A search result is more useful when it still says which section it came
    from, so we remember the most recent heading and glue it to the front of
    every chunk, e.g. "[5. PACKAGING GUIDELINES] Documents use padded ...".
    """
    text = txt_path.read_text(encoding="utf-8")
    print(f"  Read {len(text)} characters from {txt_path.name}")

    documents, ids, metadatas = [], [], []
    current_section = "Introduction"
    chunk_number = 0

    def is_dash_underline(line: str) -> bool:
        """True for a section underline like '--------------------'."""
        s = line.strip()
        return bool(s) and set(s) == {"-"}

    def is_any_underline(line: str) -> bool:
        """True for '----' or '====' style lines."""
        s = line.strip()
        return bool(s) and set(s) <= {"-", "="}

    # re.split on a blank line ("\n" then optional spaces then "\n").
    for block in re.split(r"\n\s*\n", text):
        block = block.strip()
        if not block:
            continue

        lines = block.splitlines()

        # If the block starts with "Section title" + "-----", record the new
        # section name and drop those two lines; the rest is real content.
        if len(lines) >= 2 and is_dash_underline(lines[1]):
            current_section = lines[0].strip()
            lines = lines[2:]

        # Drop any leftover underline lines and tidy the whitespace.
        real_lines = [ln for ln in lines if not is_any_underline(ln)]
        content = " ".join(" ".join(real_lines).split())
        if len(content) < 20:  # ignore tiny leftovers
            continue

        documents.append(f"[{current_section}] {content}")
        ids.append(f"kb-{chunk_number}")
        metadatas.append({"section": current_section, "source": txt_path.name})
        chunk_number += 1

    return documents, ids, metadatas


# --- Step 3: load a list of documents into a ChromaDB collection -------------
def load_collection(client, embedding_fn, name, documents, ids, metadatas):
    # Start clean: if this script ran before, delete the old collection so we
    # do not end up with duplicates.
    try:
        client.delete_collection(name)
    except Exception:
        pass

    # The embedding_function tells ChromaDB how to turn text into vectors,
    # both now (when we add data) and later (when you search with text).
    collection = client.create_collection(name=name, embedding_function=embedding_fn)

    total = len(documents)
    for start in range(0, total, BATCH_SIZE):
        end = min(start + BATCH_SIZE, total)
        collection.add(
            documents=documents[start:end],
            ids=ids[start:end],
            metadatas=metadatas[start:end],
        )
        print(f"    {name}: added {end}/{total}")
    return collection


def main():
    print("SmartLogix - loading data into ChromaDB")
    print("=" * 45)

    csv_path = find_file(DATA_DIR, "smartlogix_master.csv")
    txt_path = find_file(DATA_DIR, "knowledge_base.txt")

    # First run downloads the model (~90 MB) and caches it; later runs are fast.
    print(f"\nLoading embedding model '{EMBED_MODEL_NAME}' ...")
    embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name=EMBED_MODEL_NAME
    )

    # PersistentClient writes to disk, so the data is still there next time.
    client = chromadb.PersistentClient(
        path=str(CHROMA_DIR),
        settings=Settings(anonymized_telemetry=False),
    )

    print("\n[1/2] Building delivery sentences ...")
    d_docs, d_ids, d_meta = build_delivery_documents(csv_path)
    print(f"      Example -> {d_docs[0]}")
    load_collection(client, embedding_fn, "deliveries", d_docs, d_ids, d_meta)

    print("\n[2/2] Building knowledge base chunks ...")
    k_docs, k_ids, k_meta = build_knowledge_documents(txt_path)
    print(f"      Example -> {k_docs[0]}")
    load_collection(client, embedding_fn, "knowledge", k_docs, k_ids, k_meta)

    # Peek at what an embedding actually looks like.
    try:
        sample = embedding_fn(["Deliveries to Jaffna that arrived late"])[0]
        print(f"\nEmbedding check: that question became a vector of {len(sample)} numbers.")
    except Exception:
        pass

    print("\n" + "=" * 45)
    print("DONE. ChromaDB is ready.")
    print(f"  deliveries collection : {len(d_docs)} records")
    print(f"  knowledge collection  : {len(k_docs)} chunks")
    print(f"  saved to              : {CHROMA_DIR}")
    print("\nNext: build the Retrieval Agent that queries these collections.")


if __name__ == "__main__":
    main()
