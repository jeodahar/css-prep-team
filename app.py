import re
import shutil
from datetime import datetime

import os
import traceback

import streamlit as st

st.set_page_config(page_title="CSS Prep Team", page_icon="🎓", layout="wide")

try:
    from config import CSS_SUBJECTS, UPLOAD_DIR, get_llm
    from crew_assess import run_assessment
    from crew_prepare import run_preparation
except Exception:
    st.error("Startup failed. Copy the text below and send it to Claude.")
    st.code(traceback.format_exc())
    st.write("Files found in the repo root:", sorted(os.listdir(".")))
    st.stop()

st.title("🎓 CSS Multi-Agent Preparation Team")
st.caption("Topics, past paper trends, notes, practice questions and answer assessment.")

ss = st.session_state
ss.setdefault("package", None)
ss.setdefault("history", [])


def save_uploads(files, kind):
    for f in files or []:
        name = re.sub(r"[^A-Za-z0-9._-]", "_", f.name)
        (UPLOAD_DIR / f"{kind}__{name}").write_bytes(f.getbuffer())


# ---------------- Sidebar ----------------
with st.sidebar:
    st.header("Setup")
    subject = st.selectbox("Subject", CSS_SUBJECTS)
    if subject == "Other":
        subject = st.text_input("Type the subject name") or "General"
    marks = st.number_input("Marks per question", min_value=5, max_value=100, value=20, step=5)
    n_questions = st.slider("Practice questions", 3, 8, 5)

    st.subheader("Optional uploads")
    st.caption("Text-based PDFs work best (scanned images cannot be read).")
    syllabus_files = st.file_uploader("Syllabus", type=["pdf", "txt"], accept_multiple_files=True)
    paper_files = st.file_uploader("Past papers", type=["pdf", "txt"], accept_multiple_files=True)
    save_uploads(syllabus_files, "syllabus")
    save_uploads(paper_files, "paper")

    if st.button("Clear uploaded files"):
        shutil.rmtree(UPLOAD_DIR, ignore_errors=True)
        UPLOAD_DIR.mkdir(exist_ok=True)
        st.success("Uploads cleared.")

tab_prepare, tab_assess, tab_reports = st.tabs(
    ["1️⃣ Prepare", "2️⃣ Practice & Assess", "3️⃣ My Reports"]
)

# ---------------- Tab 1: Prepare ----------------
with tab_prepare:
    focus = st.text_input("Focus topic (optional)", placeholder="e.g. Constitutional development")
    if st.button("Build my preparation package", type="primary"):
        try:
            llm = get_llm()
            with st.spinner("4 agents are working... this can take a few minutes."):
                ss["package"] = run_preparation(llm, subject, focus, n_questions, int(marks))
            ss["package_subject"] = subject
        except Exception as e:
            st.error(f"Something went wrong: {e}")
            st.info("If you see a rate-limit (429) error, wait one minute and try again.")

    pkg = ss.get("package")
    if pkg:
        t1, t2, t3, t4 = st.tabs(["Topics", "Past paper analysis", "Notes", "Questions"])
        t1.markdown(pkg["topics"])
        t2.markdown(pkg["past_papers"])
        t3.markdown(pkg["notes"])
        t4.markdown(pkg["questions"])
        full = (
            f"# CSS {ss.get('package_subject', subject)} - Preparation Package\n\n"
            f"## Topics\n{pkg['topics']}\n\n## Past paper analysis\n{pkg['past_papers']}\n\n"
            f"## Notes\n{pkg['notes']}\n\n## Questions\n{pkg['questions']}"
        )
        st.download_button("Download package (.md)", full, file_name="css_preparation_package.md")

# ---------------- Tab 2: Practice & Assess ----------------
with tab_assess:
    options = []
    if ss.get("package"):
        found = re.findall(r"^[\s*#>-]*(Q\d+[\.\):]?\s.+)$", ss["package"]["questions"], re.M)
        options = [q.replace("**", "").strip() for q in found]
    CUSTOM = "✍️ Type my own question"
    choice = st.selectbox("Choose a question", options + [CUSTOM])
    question = st.text_area("Question", value="" if choice == CUSTOM else choice, height=90)
    answer = st.text_area("Your answer", height=320, placeholder="Type or paste your answer here...")

    if st.button("Assess my answer", type="primary"):
        if not question.strip() or len(answer.split()) < 30:
            st.warning("Please add a question and an answer of at least 30 words.")
        else:
            try:
                llm = get_llm()
                with st.spinner("The assessor is marking your answer..."):
                    report = run_assessment(llm, subject, question, answer, int(marks))
                ss["history"].append(
                    {
                        "time": datetime.now().strftime("%Y-%m-%d %H:%M"),
                        "subject": subject,
                        "question": question,
                        "report": report,
                    }
                )
                st.markdown(report)
            except Exception as e:
                st.error(f"Something went wrong: {e}")
                st.info("If you see a rate-limit (429) error, wait one minute and try again.")

# ---------------- Tab 3: Reports ----------------
with tab_reports:
    if not ss["history"]:
        st.info("No assessments yet in this session.")
    else:
        for item in reversed(ss["history"]):
            with st.expander(f"{item['time']} - {item['subject']}: {item['question'][:70]}"):
                st.markdown(item["report"])
        all_text = "\n\n---\n\n".join(
            f"## {h['time']} - {h['subject']}\n**Question:** {h['question']}\n\n{h['report']}"
            for h in ss["history"]
        )
        st.download_button("Download all reports (.md)", all_text, file_name="css_reports.md")
        st.caption("Reports are kept only while this browser session is open. Download to keep them.")
