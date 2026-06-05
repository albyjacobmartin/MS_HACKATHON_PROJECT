import os
import json

from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, File, Form
from pypdf import PdfReader
import google.generativeai as genai
from fastapi.responses import HTMLResponse

# =========================
# CONFIG
# =========================

load_dotenv()

genai.configure(
    api_key=os.getenv("GEMINI_API_KEY")
)

model = genai.GenerativeModel("gemini-2.5-flash")

app = FastAPI()

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.get("/app", response_class=HTMLResponse)
def app_page():

    with open(
        "templates/index.html",
        "r",
        encoding="utf-8"
    ) as f:
        return f.read()

# =========================
# LOAD ROLES
# =========================

with open("roles.json", "r") as f:
    ROLE_DATA = json.load(f)

# =========================
# AI FUNCTIONS
# =========================

def extract_skills_with_gemini(resume_text):

    prompt = f"""
Return ONLY valid JSON.

No markdown.
No explanation.
No code block.

Schema:

{{
    "skills": [],
    "projects": [],
    "certifications": []
}}

Resume:

{resume_text}
"""

    response = model.generate_content(prompt)

    content = response.text.strip()

    content = content.replace("```json", "")
    content = content.replace("```", "")

    return json.loads(content)


def generate_learning_roadmap(
    target_role,
    student_skills,
    missing_skills
):

    prompt = f"""
You are an expert career mentor.

Target Role:
{target_role}

Current Skills:
{student_skills}

Missing Skills:
{missing_skills}

Generate:

1. Learning roadmap
2. Recommended certifications
3. Recommended projects
4. 30-day improvement plan

Keep response concise and practical.
"""

    response = model.generate_content(prompt)

    return response.text


# =========================
# GAP ANALYSIS
# =========================

def calculate_skill_gap(
    student_skills,
    role_skills
):

    matched = []
    missing = []

    for role_skill in role_skills:

        found = any(
            role_skill.lower() in student.lower()
            or role_skill.lower() in student.lower()
            for student in student_skills
        )

        if found:
            matched.append(role_skill)
        else:
            missing.append(role_skill)

    score = round(
        (len(matched) / len(role_skills)) * 100
    )

    return {
        "score": score,
        "matched": matched,
        "missing": missing
    }

# =========================
# ROUTES
# =========================

@app.get("/")
def home():
    return {
        "status": "working"
    }


@app.post("/upload")
async def upload_resume(
    file: UploadFile = File(...)
):

    filepath = os.path.join(
        UPLOAD_FOLDER,
        file.filename
    )

    with open(filepath, "wb") as f:
        f.write(await file.read())

    reader = PdfReader(filepath)

    text = ""

    for page in reader.pages:
        page_text = page.extract_text()

        if page_text:
            text += page_text + "\n"

    parsed_data = extract_skills_with_gemini(text)

    return {
        "filename": file.filename,
        "parsed_data": parsed_data
    }


@app.post("/analyze")
async def analyze_resume(
    file: UploadFile = File(...),
    target_role: str = Form(...)
):

    filepath = os.path.join(
        UPLOAD_FOLDER,
        file.filename
    )

    with open(filepath, "wb") as f:
        f.write(await file.read())

    reader = PdfReader(filepath)

    text = ""

    for page in reader.pages:
        page_text = page.extract_text()

        if page_text:
            text += page_text + "\n"

    parsed_data = extract_skills_with_gemini(text)

    student_skills = parsed_data["skills"]

    role_skills = ROLE_DATA[target_role]

    gap_analysis = calculate_skill_gap(
        student_skills,
        role_skills
    )

    roadmap = generate_learning_roadmap(
        target_role,
        student_skills,
        gap_analysis["missing"]
    )

    return {
        "target_role": target_role,
        "student_skills": student_skills,
        "gap_analysis": gap_analysis,
        "roadmap": roadmap
    }