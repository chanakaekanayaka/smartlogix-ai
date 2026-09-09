# SmartLogix

An **Agentic AI logistics system** built as a university project.

SmartLogix uses a team of cooperating AI agents to help with logistics
tasks such as analysing shipment data, answering questions from a
logistics knowledge base, and giving recommendations. It combines:

- **CrewAI / LangChain** – to run the AI agents
- **ChromaDB + sentence-transformers** – a searchable knowledge base
  (retrieval augmented generation)
- **Groq** – the language model that powers the agents
- **Streamlit** – a simple web interface with login
- **spaCy + bcrypt** – input checking and secure passwords

## Project structure

| Folder       | What it holds                                              |
| ------------ | --------------------------------------------------------- |
| `agents/`    | The AI agents (their roles, goals, and tools)             |
| `data/`      | The dataset and knowledge-base documents                  |
| `database/`  | Script that loads the knowledge base into ChromaDB        |
| `ui/`        | The Streamlit web interface                               |
| `security/`  | Login and user-input validation                           |
| `utils/`     | Shared helper functions                                   |

## Setup

```bash
# 1. Create and activate a virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS / Linux

# 2. Install dependencies
pip install -r requirements.txt

# 3. Add your API key
copy .env.example .env       # Windows  (cp on macOS/Linux)
# then edit .env and paste your GROQ_API_KEY

# 4. Load the dataset + knowledge base into ChromaDB
python database/load_data.py

# 5. Run the app
streamlit run ui/app.py
```

## Notes

- `.env` and the ChromaDB folder are Git-ignored and must not be uploaded.
- This project is for educational purposes.
