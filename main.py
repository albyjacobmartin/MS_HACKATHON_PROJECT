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
You are an experienced career mentor helping a student become industry-ready for the role of {target_role}.

STUDENT PROFILE

Current Skills:
{student_skills}

Missing Skills:
{missing_skills}

YOUR TASK

Create a personalized career guidance report that evaluates the student's readiness and provides a practical roadmap to reach the target role.

GUIDELINES

- Write naturally like a real mentor speaking directly to a student.
- Be encouraging, honest, and practical.
- Explain how the student's current skills help them.
- For every missing skill, explain why it is important in real industry work.
- Prioritize the missing skills from most important to least important.
- Recommend relevant certifications that strengthen employability.
- Recommend portfolio-worthy projects that demonstrate the missing skills.
- Suggest learning resources or topics when appropriate.
- Include a realistic 30-day improvement plan.
- Focus on becoming job-ready rather than collecting certificates.
- Keep the advice actionable and specific.
- Avoid generic motivational statements.

OUTPUT FORMAT

CAREER ASSESSMENT

Evaluate the student's current position and readiness for the target role.

LEARNING ROADMAP

Explain which skills should be learned first, second, and third.
For each skill:
Why it matters
How it is used in industry
What the student should learn

RECOMMENDED CERTIFICATIONS

Recommend 3-5 certifications.
For each certification:
Why it is valuable
When the student should take it

RECOMMENDED PROJECTS

Recommend 3-5 practical projects.
For each project:
Project idea
Skills demonstrated
Expected outcome

30-DAY IMPROVEMENT PLAN

Week 1:
Learning goals and tasks

Week 2:
Learning goals and tasks

Week 3:
Learning goals and tasks

Week 4:
Learning goals and tasks

FINAL ADVICE

End with a short mentor-style message describing the student's next priority and how to continue progressing toward the role.

FORMATTING RULES

- Use plain text only.
- Do NOT use markdown.
- Do NOT use #, ##, ###, *, **, bullet symbols, tables, or code blocks.
- Use section titles in ALL CAPS.
- Keep paragraphs short and readable.
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