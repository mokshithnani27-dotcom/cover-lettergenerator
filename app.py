import os
import time

import streamlit as st
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()



def _setting(name: str, default=None):
    """Read from .env / environment first, then .streamlit/secrets.toml."""
    value = os.getenv(name)
    if value:
        return value
    try:
        return st.secrets.get(name, default)
    except Exception:
        return default


API_KEY = _setting("GEMINI_API_KEY")
MODEL = _setting("GEMINI_MODEL", "gemini-3.8-flash")
MAX_WORDS = 300

# Optional backup models (comma-separated), tried if the main model stays overloaded
FALLBACK_MODELS = [
    m.strip() for m in (_setting("GEMINI_FALLBACK_MODELS", "") or "").split(",") if m.strip()
]
RETRIES_PER_MODEL = 4  # waits 2s, 4s, 8s between attempts

st.set_page_config(page_title="AI Cover Letter Generator", page_icon="✉️", layout="centered")

SYSTEM_PROMPT = f"""You are an expert career coach who writes concise, personalized cover letters
for students and fresh graduates.

Rules:
- Maximum {MAX_WORDS} words (aim for 220-270), including greeting and sign-off.
- Format: greeting, 3 short paragraphs (hook, skills/projects matched to the job, closing call to action), sign-off with the candidate's name.
- Explicitly connect the candidate's skills, projects and internships to requirements in the job description.
- Use only facts the candidate provided. Never invent experience, numbers or employers.
- Professional, confident, warm tone. No cliches like "I am writing to apply".
- Output ONLY the letter text. No subject line, no markdown, no commentary.
"""


def word_count(text: str) -> int:
    return len(text.split())


def get_client():
    if not API_KEY:
        st.error("GEMINI_API_KEY not found. Add it to your .env file and restart the app.")
        st.stop()
    return genai.Client(api_key=API_KEY)


def _is_retryable(err: Exception) -> bool:
    text = str(err)
    return any(code in text for code in ("503", "429", "500", "UNAVAILABLE", "RESOURCE_EXHAUSTED"))


def generate(client, prompt: str) -> str:
    """Call Gemini, retrying with backoff on temporary overload (503/429)."""
    last_err = None
    for model in [MODEL] + FALLBACK_MODELS:
        for attempt in range(RETRIES_PER_MODEL):
            try:
                response = client.models.generate_content(
                    model=model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=SYSTEM_PROMPT,
                        temperature=0.7,
                    ),
                )
                return (response.text or "").strip()
            except Exception as e:
                last_err = e
                if not _is_retryable(e):
                    raise
                time.sleep(2 ** (attempt + 1))
    raise last_err


def build_prompt(d: dict) -> str:
    return f"""Write a cover letter using these details.

CANDIDATE
Name: {d['name']}
Degree: {d['degree']}
Skills: {d['skills']}
Projects / Internship: {d['experience']}

JOB
Company: {d['company']}
Role: {d['role']}
Job description:
{d['jd']}
"""


def make_letter(client, data: dict) -> str:
    letter = generate(client, build_prompt(data))
    # Enforce the word limit: ask the model to shorten if it went over
    attempts = 0
    while word_count(letter) > MAX_WORDS and attempts < 2:
        letter = generate(
            client,
            f"Shorten this cover letter to under {MAX_WORDS} words, keeping the "
            f"structure and key points. Output only the letter.\n\n{letter}",
        )
        attempts += 1
    return letter


# ---------------- UI ----------------
st.title("✉️ AI Cover Letter Generator")
st.caption("Fill in your details and get a tailored cover letter in seconds.")

with st.form("letter_form"):
    st.subheader("About you")
    col1, col2 = st.columns(2)
    name = col1.text_input("Full name *")
    degree = col2.text_input("Degree *", placeholder="B.Tech in Computer Science")
    skills = st.text_area("Skills *", placeholder="Python, SQL, React, Machine Learning...", height=80)
    experience = st.text_area(
        "Projects / Internship *",
        placeholder="e.g. Built a sentiment analysis app using BERT; 2-month internship at XYZ working on...",
        height=120,
    )

    st.subheader("The job")
    col3, col4 = st.columns(2)
    company = col3.text_input("Company name *")
    role = col4.text_input("Job role *")
    jd = st.text_area("Job description *", height=180)

    submitted = st.form_submit_button("Generate cover letter", type="primary", use_container_width=True)

if submitted:
    data = {
        "name": name.strip(),
        "degree": degree.strip(),
        "skills": skills.strip(),
        "experience": experience.strip(),
        "company": company.strip(),
        "role": role.strip(),
        "jd": jd.strip(),
    }
    missing = [k for k, v in data.items() if not v]
    if missing:
        st.warning("Please fill in all fields before generating.")
    else:
        client = get_client()
        with st.spinner("Writing your cover letter..."):
            try:
                st.session_state["letter"] = make_letter(client, data)
                st.session_state["filename"] = (
                    f"cover_letter_{data['company']}_{data['role']}".replace(" ", "_") + ".txt"
                )
            except Exception as e:
                if _is_retryable(e):
                    st.error(
                        "Gemini is busy right now (high demand). I retried several times - "
                        "please wait a minute and click Generate again."
                    )
                else:
                    st.error(f"Something went wrong: {e}")

if "letter" in st.session_state:
    st.divider()
    st.subheader("Your cover letter")
    letter = st.text_area("You can edit it before downloading:", value=st.session_state["letter"], height=380)
    wc = word_count(letter)
    st.caption(f"{wc} words" + ("" if wc <= MAX_WORDS else f" (over the {MAX_WORDS}-word target)"))
    st.download_button(
        "⬇️ Download as .txt",
        data=letter,
        file_name=st.session_state["filename"],
        mime="text/plain",
        use_container_width=True,
    )
