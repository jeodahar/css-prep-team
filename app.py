import os
import re
import shutil
import traceback

import streamlit as st

st.set_page_config(page_title="CSS Prep Team", page_icon="🎓", layout="wide")

try:
    import storage
    from config import CSS_SUBJECTS, OFFICIAL_PDF, UPLOAD_DIR, get_llm
    from syllabus_loader import ensure_official_syllabus
    from tool_syllabus import set_syllabus_hint
    import ui_plan
    import ui_practice
    import ui_prepare
    import ui_progress
    import ui_question
    import ui_study
except Exception:
    st.error("Startup failed. Copy the text below and send it to Claude.")
    st.code(traceback.format_exc())
    st.write("Files found in the repo root:", sorted(os.listdir(".")))
    st.stop()

st.title("🎓 CSS Multi-Agent Preparation Team")
st.caption("Prepare, study, practise (typed or handwritten), plan and track your progress.")

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
        if storage.setup_error():
            st.caption(storage.setup_error())
    if storage.is_enabled() and st.button("Test cloud saving"):
        ok, msg = storage.check_connection()
        (st.success if ok else st.error)(msg)

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
        rows, err = storage.load_items(user_id, "plan")
        if rows and not err:
            ss["last_plan"] = rows[-1]["content"]
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

ctx = {
    "subject": subject,
    "marks": int(marks),
    "n_questions": n_questions,
    "user_id": user_id,
}

tabs = st.tabs(
    [
        "1️⃣ Prepare",
        "📖 Study",
        "🔍 Question analysis",
        "✍️ Answer practice",
        "📅 Study plan",
        "📊 Progress",
        "📁 Reports",
    ]
)
with tabs[0]:
    ui_prepare.render(ctx)
with tabs[1]:
    ui_study.render(ctx)
with tabs[2]:
    ui_question.render(ctx)
with tabs[3]:
    ui_practice.render(ctx)
with tabs[4]:
    ui_plan.render(ctx)
with tabs[5]:
    ui_progress.render_progress(ctx)
with tabs[6]:
    ui_progress.render_reports(ctx)
