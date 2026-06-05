import google.generativeai as genai
from dotenv import load_dotenv
import os

load_dotenv()

genai.configure(
    api_key=os.getenv("GEMINI_API_KEY")
)

model = genai.GenerativeModel("gemini-2.5-flash")

from fastapi import FastAPI, UploadFile, File
from pypdf import PdfReader
import os

app = FastAPI()

UPLOAD_FOLDER = "uploads"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)


@app.get("/")
def home():
    return {"status": "working"}


@app.post("/upload")
async def upload_resume(file: UploadFile = File(...)):

    filepath = os.path.join(UPLOAD_FOLDER, file.filename)

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

import json

def extract_skills_with_gemini(resume_text):

    prompt = f"""
You are an expert technical recruiter.

Analyze the resume and return ONLY valid JSON.

Required format:

{{
    "skills": [],
    "projects": [],
    "certifications": []
}}

Resume:

{resume_text}
"""

    response = model.generate_content(prompt)

    content = response.text

    content = content.replace("```json", "")
    content = content.replace("```", "")

    return json.loads(content)