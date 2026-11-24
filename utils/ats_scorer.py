import re

ROLE_SKILLS = {
    "Full Stack Developer": [
        "python", "javascript", "html", "css", "react", "node.js", "flask",
        "django", "sql", "mongodb", "git", "rest api", "docker", "typescript"
    ],
    "Data Analyst": [
        "python", "sql", "excel", "power bi", "tableau", "pandas", "numpy",
        "statistics", "data visualization", "etl", "r", "machine learning", "mysql"
    ],
    "Cloud & DevOps Engineer": [
        "aws", "azure", "docker", "kubernetes", "linux", "ci/cd", "terraform",
        "git", "python", "bash", "networking", "jenkins", "ansible", "cloud"
    ],
    "IoT & Embedded Engineer": [
        "c", "c++", "python", "embedded c", "arduino", "raspberry pi", "esp32",
        "mqtt", "sensors", "iot", "rtos", "linux", "pcb", "uart", "spi", "i2c"
    ],
    "AI / ML Engineer": [
        "python", "machine learning", "deep learning", "tensorflow", "pytorch",
        "scikit-learn", "nlp", "computer vision", "pandas", "numpy", "sql", "llm"
    ],
}

GENERAL_TECH_SKILLS = sorted(list({skill for skills in ROLE_SKILLS.values() for skill in skills}))

ACTION_VERBS = [
    "developed", "built", "designed", "implemented", "engineered", "optimized",
    "automated", "deployed", "analyzed", "created", "improved", "reduced",
    "led", "integrated", "architected", "tested", "collaborated", "delivered"
]

SECTIONS = {
    "Education": ["education", "b.tech", "bachelor", "university", "college", "cgpa", "gpa"],
    "Skills": ["skills", "technical skills", "technologies", "tools", "programming"],
    "Projects": ["projects", "academic projects", "personal projects", "capstone"],
    "Experience": ["experience", "internship", "intern", "work history", "employment"],
    "Certifications": ["certifications", "certificates", "achievements", "awards", "nptel", "coursera"]
}


def analyze_resume_text(text, target_role="Full Stack Developer"):
    clean_text = (text or "").strip()
    lower_text = clean_text.lower()
    word_count = len(clean_text.split())

    if word_count < 15:
        return {
            "ats_score": 25,
            "readiness_score": 20,
            "word_count": word_count,
            "matched_skills": [],
            "missing_skills": ROLE_SKILLS.get(target_role, ROLE_SKILLS["Full Stack Developer"])[:6],
            "detected_sections": [],
            "missing_sections": list(SECTIONS.keys()),
            "suggestions": [
                "Uploaded resume has very little readable text. Ensure your PDF is text-based (not a scanned image).",
                "Include clear sections: Contact Info, Education, Technical Skills, Projects, and Internships.",
                f"Add core keywords for {target_role} roles."
            ]
        }

    # 1. Contact & Links Check (15 pts)
    has_email = bool(re.search(r"[\w\.-]+@[\w\.-]+\.\w+", clean_text))
    has_phone = bool(re.search(r"(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}", clean_text))
    has_links = any(k in lower_text for k in ["github.com", "linkedin.com", "portfolio", "leetcode"])
    contact_score = (6 if has_email else 0) + (5 if has_phone else 0) + (4 if has_links else 0)

    # 2. Section Completeness (25 pts)
    detected_sections = []
    missing_sections = []
    for sec_name, keywords in SECTIONS.items():
        if any(kw in lower_text for kw in keywords):
            detected_sections.append(sec_name)
        else:
            missing_sections.append(sec_name)
    section_score = int((len(detected_sections) / len(SECTIONS)) * 25)

    # 3. Role-Specific Skills & General Skills Match (35 pts)
    target_keywords = ROLE_SKILLS.get(target_role, ROLE_SKILLS["Full Stack Developer"])
    matched_role_skills = [s for s in target_keywords if re.search(r"\b" + re.escape(s) + r"\b", lower_text)]
    matched_general = [s for s in GENERAL_TECH_SKILLS if re.search(r"\b" + re.escape(s) + r"\b", lower_text)]
    all_matched = sorted(list(set(matched_role_skills + matched_general)))
    missing_role_skills = [s for s in target_keywords if s not in matched_role_skills]

    role_ratio = len(matched_role_skills) / max(len(target_keywords), 1)
    skill_score = min(35, int(role_ratio * 30) + min(5, len(all_matched)))

    # 4. Impact, Action Verbs & Length (25 pts)
    verbs_found = [v for v in ACTION_VERBS if re.search(r"\b" + v + r"\b", lower_text)]
    has_metrics = bool(re.search(r"(\d+%|\d+\+|\d+x|\b\d{2,}\b)", clean_text))
    verb_score = min(12, len(verbs_found) * 2)
    metric_score = 7 if has_metrics else 2
    length_score = 6 if 180 <= word_count <= 950 else 3
    impact_score = verb_score + metric_score + length_score

    ats_score = max(32, min(98, contact_score + section_score + skill_score + impact_score))
    readiness_score = max(30, min(96, int(ats_score * 0.85 + (len(detected_sections) * 2.5))))

    suggestions = []
    if not has_email or not has_phone:
        suggestions.append("Add a professional email address and reachable phone number at the top of your resume.")
    if not has_links:
        suggestions.append("Include clickable GitHub and LinkedIn profile URLs to boost recruiter trust.")
    if missing_sections:
        suggestions.append(f"Add missing standard sections: {', '.join(missing_sections)}.")
    if missing_role_skills:
        suggestions.append(f"Strengthen {target_role} alignment by adding projects/skills in: {', '.join(missing_role_skills[:5])}.")
    if not has_metrics:
        suggestions.append("Quantify your project achievements using numbers (e.g., 'Improved API response speed by 35%').")
    if len(verbs_found) < 4:
        suggestions.append("Start project bullet points with strong action verbs like Developed, Engineered, Automated, or Optimized.")
    if not suggestions:
        suggestions.append("Great structure! Tailor your top 3 project bullets specifically to each Job Description before applying.")

    return {
        "ats_score": ats_score,
        "readiness_score": readiness_score,
        "word_count": word_count,
        "matched_skills": [s.upper() if len(s) <= 3 else s.title() for s in all_matched],
        "missing_skills": [s.upper() if len(s) <= 3 else s.title() for s in missing_role_skills[:7]],
        "detected_sections": detected_sections,
        "missing_sections": missing_sections,
        "suggestions": suggestions
    }


def match_job_description(resume_text, jd_text):
    r_lower = (resume_text or "").lower()
    j_lower = (jd_text or "").lower()

    jd_skills = [s for s in GENERAL_TECH_SKILLS if re.search(r"\b" + re.escape(s) + r"\b", j_lower)]

    stopwords = {
        "with", "that", "have", "from", "this", "will", "your", "team", "work",
        "experience", "skills", "knowledge", "strong", "good", "ability", "role",
        "years", "using", "develop", "development", "software", "engineer", "looking",
        "required", "preferred", "responsibilities", "requirements", "candidate", "must"
    }
    jd_words = set(re.findall(r"\b[a-z][a-z0-9+#.-]{2,}\b", j_lower)) - stopwords

    if not jd_skills and not jd_words:
        return {"match_percent": 0, "matched": [], "missing": [], "advice": "Paste a detailed Job Description to compare."}

    if jd_skills:
        matched = [s for s in jd_skills if re.search(r"\b" + re.escape(s) + r"\b", r_lower)]
        missing = [s for s in jd_skills if s not in matched]
        ratio = len(matched) / len(jd_skills)
    else:
        matched = sorted([w for w in jd_words if w in r_lower])[:12]
        missing = sorted([w for w in jd_words if w not in r_lower])[:10]
        ratio = len(matched) / max(len(matched) + len(missing), 1)

    overlap = len([w for w in jd_words if w in r_lower]) / max(len(jd_words), 1)
    match_percent = max(18, min(97, int((ratio * 0.75 + overlap * 0.25) * 100)))

    if match_percent >= 75:
        advice = "Strong Match! Your resume covers most core requirements. Highlight these matching skills in your summary."
    elif match_percent >= 50:
        advice = "Moderate Match. Add the missing keywords below into your Skills and Project descriptions before applying."
    else:
        advice = "Low Match. Customize your resume projects and technical skills section to align with this specific JD."

    return {
        "match_percent": match_percent,
        "matched": [m.upper() if len(m) <= 3 else m.title() for m in matched],
        "missing": [m.upper() if len(m) <= 3 else m.title() for m in missing],
        "advice": advice
    }
