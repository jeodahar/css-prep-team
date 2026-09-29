import os
import re
import shutil
import traceback
from datetime import datetime

import streamlit as st

st.set_page_config(page_title="CSS Prep Team", page_icon="🎓", layout="wide")

try:
    import storage
    from config import CSS_SUBJECTS, OFFICIAL_PDF, UPLOAD_DIR, get_llm
    from pdf_export import package_pdf, reports_pdf
    from syllabus_loader import ensure_official_syllabus
    from tool_syllabus import preview_section, set_syllabus_hint
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
    st.header("Your profile")
    raw_id = st.text_input(
        "Profile name / secret code",
        help="Your saved work is stored under this name. Use something hard to guess.",
    )
    user_id = re.sub(r"[^a-z0-9_-]", "", raw_id.strip().lower().replace(" ", "-"))
    if storage.is_enabled():
        st.caption("💾 Cloud saving is ON" if user_id else "Enter a profile name to save your work.")
    else:
        st.caption("⚠️ Cloud saving is OFF (work is kept only while this tab is open).")

    st.header("Official syllabus")
    if OFFICIAL_PDF.exists():
        ss["syllabus_ok"] = True
    elif not ss.get("syllabus_tried"):
        with st.spinner("Downloading the official CSS syllabus..."):
            ss["syllabus_ok"], ss["syllabus_msg"] = ensure_official_syllabus()
        ss["syllabus_tried"] = True
    if ss.get("syllabus_ok"):
        st.caption("📘 Official CSS syllabus is loaded.")
    else:
        st.caption("⚠️ " + ss.get("syllabus_msg", "Syllabus not loaded."))
        if st.button("Retry syllabus download"):
            ss["syllabus_tried"] = False
            st.rerun()

    st.header("Setup")
    subject = st.selectbox("Subject", CSS_SUBJECTS)
    if subject == "Other":
        subject = st.text_input("Type the subject name") or "General"
    marks = st.number_input("Marks per question", min_value=5, max_value=100, value=20, step=5)
    n_questions = st.slider("Practice questions", 3, 8, 5)
    syllabus_hint = st.text_input(
        "Syllabus heading (only if the preview looks wrong)",
        help="Type words from the subject's heading in the syllabus, e.g. 'Islamic Studies'.",
    )
    set_syllabus_hint(syllabus_hint)

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

# ---------------- Load saved data ----------------
if user_id and storage.is_enabled():
    if ss.get("loaded_user") != user_id:
        rows, err = storage.load_items(user_id, "report")
        if err:
            st.warning(err)
        else:
            ss["history"] = [r["content"] for r in rows]
        ss["loaded_user"] = user_id
        ss["pkg_key"] = None
    pkg_key = f"{user_id}|{subject}"
    if ss.get("pkg_key") != pkg_key:
        rows, err = storage.load_items(user_id, "package", subject)
        if err:
            st.warning(err)
        elif rows:
            ss["package"] = rows[-1]["content"]
            ss["package_subject"] = subject
        elif ss.get("package_subject") != subject:
            ss["package"] = None
        ss["pkg_key"] = pkg_key

tab_prepare, tab_assess, tab_reports = st.tabs(
    ["1️⃣ Prepare", "2️⃣ Practice & Assess", "3️⃣ My Reports"]
)

# ---------------- Tab 1: Prepare ----------------
with tab_prepare:
    focus = st.text_input("Focus topic (optional)", placeholder="e.g. Constitutional development")
    if ss.get("syllabus_ok"):
        with st.expander("Check: official syllabus text the agents will read for this subject"):
            st.text(preview_section(subject))
    if st.button("Build my preparation package", type="primary"):
        try:
            llm = get_llm()
            partial = ss.setdefault("partial", {})
            sig = (subject, focus, n_questions, int(marks))
            if ss.get("partial_sig") != sig:
                partial.clear()
                ss["partial_sig"] = sig
            with st.status("4 agents are working (free Groq limits make this take ~5-8 minutes)...", expanded=True) as status:
                pkg_new = run_preparation(
                    llm, subject, focus, n_questions, int(marks), partial, lambda m: st.write(m)
                )
                status.update(label="Package ready", state="complete", expanded=False)
            ss["package"] = pkg_new
            partial.clear()
            ss["package_subject"] = subject
            if user_id and storage.is_enabled():
                err = storage.save_package(user_id, subject, ss["package"])
                if err:
                    st.warning(err)
                else:
                    st.success("Package saved to your profile.")
        except Exception as e:
            st.error(f"Something went wrong: {e}")
            if ss.get("partial"):
                st.info("Finished steps are kept. Click the button again to continue from where it stopped.")
            else:
                st.info("If you see a rate-limit (429) error, wait one minute and try again.")

    pkg = ss.get("package")
    if pkg:
        t1, t2, t3, t4 = st.tabs(["Topics", "Past paper analysis", "Notes", "Questions"])
        t1.markdown(pkg["topics"])
        t2.markdown(pkg["past_papers"])
        t3.markdown(pkg["notes"])
        t4.markdown(pkg["questions"])
        try:
            st.download_button(
                "Download package (PDF)",
                package_pdf(ss.get("package_subject", subject), pkg),
                file_name="css_preparation_package.pdf",
                mime="application/pdf",
            )
        except Exception as e:
            st.warning(f"Could not create the PDF: {e}")

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
                item = {
                    "time": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "subject": subject,
                    "question": question,
                    "answer": answer,
                    "report": report,
                }
                ss["history"].append(item)
                st.markdown(report)
                try:
                    st.download_button(
                        "Download this report (PDF)",
                        reports_pdf([item]),
                        file_name="css_report.pdf",
                        mime="application/pdf",
                        key="dl_latest",
                    )
                except Exception as e:
                    st.warning(f"Could not create the PDF: {e}")
                if user_id and storage.is_enabled():
                    err = storage.save_report(user_id, subject, item)
                    if err:
                        st.warning(err)
                    else:
                        st.success("Report saved to your profile.")
            except Exception as e:
                st.error(f"Something went wrong: {e}")
                st.info("If you see a rate-limit (429) error, wait one minute and try again.")

# ---------------- Tab 3: Reports ----------------
with tab_reports:
    if not ss["history"]:
        st.info("No assessments yet.")
    else:
        for n, item in enumerate(reversed(ss["history"])):
            with st.expander(f"{item['time']} - {item['subject']}: {item['question'][:70]}"):
                st.markdown(item["report"])
                if item.get("answer"):
                    st.caption("Your answer")
                    st.write(item["answer"])
                try:
                    st.download_button(
                        "Download this report (PDF)",
                        reports_pdf([item]),
                        file_name="css_report.pdf",
                        mime="application/pdf",
                        key=f"dl_report_{n}",
                    )
                except Exception as e:
                    st.warning(f"Could not create the PDF: {e}")
        try:
            st.download_button(
                "Download all reports (PDF)",
                reports_pdf(ss["history"]),
                file_name="css_reports.pdf",
                mime="application/pdf",
                key="dl_all",
            )
        except Exception as e:
            st.warning(f"Could not create the PDF: {e}")
        if not (user_id and storage.is_enabled()):
            st.caption("Not saved to the cloud. Enter a profile name (and set up saving) to keep reports.")
