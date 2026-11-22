# Balochistan Smart Highway & Weather Intelligence System

Streamlit version of the Highway Watch interface.

## Run locally

```bash
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

## Deploy on Streamlit Community Cloud

1. Upload `app.py`, `requirements.txt`, and this README to a public GitHub repository.
2. Open https://share.streamlit.io/ and sign in with GitHub.
3. Select the repository, branch `main`, and main file path `app.py`.
4. Click Deploy.

## Data and safety notes

- Weather observations are fetched from the Open-Meteo forecast API for the listed corridor checkpoints.
- The risk score is an indicative heuristic based on precipitation, wind and weather code. It is not a validated forecast model or an official warning.
- Driver, alert, SOS and road-status records are stored in a local SQLite database. Streamlit Community Cloud storage may be ephemeral; use a managed database for durable multi-user production operation.
- SMS/voice actions are previews and local records only. No messages or emergency dispatches are sent.
- Checkpoint/facility references and alternate route text require field verification. Always follow official NHA, PDMA, police and district administration updates.
