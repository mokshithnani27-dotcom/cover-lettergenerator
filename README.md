# AI Cover Letter Generator (Streamlit + Gemini)

## Setup
1. Get a free API key: https://aistudio.google.com/app/apikey
2. Create a virtual environment
   - Windows: `python -m venv venv` then `venv\Scripts\activate`
   - Mac/Linux: `python3 -m venv venv` then `source venv/bin/activate`
3. Install dependencies: `pip install -r requirements.txt`
4. Copy `.env.example` to `.env` and paste your key in `GEMINI_API_KEY`
5. Run: `streamlit run app.py`

The app opens at http://localhost:8501

## Troubleshooting
- Model not found: change `GEMINI_MODEL` in `.env` (e.g. `gemini-3.8-flash` or `gemini-3.8-pro`).
- API key error: make sure `.env` is in the same folder as `app.py`.
