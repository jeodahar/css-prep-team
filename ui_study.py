import streamlit as st

import storage
from config import get_llm
from crew_study import run_explanation
from pdf_export import document_pdf
from progress import topic_names
from ui_common import CUSTOM_T, cloud_on, current_package, show_error
from datetime import datetime


def _key(subject, topic):
    return f"{subject}|{topic.strip().lower()[:80]}"


def render(ctx):
    ss = st.session_state
    subject = ctx["subject"]
    st.subheader(f"📖 Study mode: {subject}")
    st.caption("Pick a topic and get a clear, exam-oriented explanation. Build the package first to get a topic list.")

    pkg = current_package(subject)
    topics = topic_names(pkg["topics"]) if pkg else []
    choice = st.selectbox("Topic", topics + [CUSTOM_T], key="study_choice")
    topic = st.text_input("Topic name", value="" if choice == CUSTOM_T else choice)
    level = st.radio("Level", ["Beginner", "Standard", "Advanced"], index=1, horizontal=True, key="study_level")
    force = st.checkbox("Make a fresh explanation (ignore the saved one)", key="study_force")

    if st.button("Explain this topic", type="primary", key="study_btn"):
        if not topic.strip():
            st.warning("Please choose or type a topic.")
        else:
            try:
                key = _key(subject, topic)
                cached = None
                if cloud_on(ctx) and not force:
                    rows, err = storage.load_items(ctx["user_id"], "explanation", key)
                    if rows and not err:
                        cached = rows[-1]["content"]
                if cached:
                    ss["last_explanation"] = cached
                else:
                    llm = get_llm()
                    with st.status("The tutor is preparing your explanation...", expanded=True) as status:
                        text = run_explanation(llm, subject, topic.strip(), level, lambda m: st.write(m))
                        status.update(label="Explanation ready", state="complete", expanded=False)
                    item = {
                        "subject": subject, "topic": topic.strip(), "level": level, "text": text,
                        "time": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    }
                    ss["last_explanation"] = item
                    if cloud_on(ctx):
                        err = storage.save_replace(ctx["user_id"], "explanation", key, item)
                        st.warning(err) if err else st.success("Explanation saved to your profile.")
            except Exception as e:
                show_error(e)

    exp = ss.get("last_explanation")
    if exp and exp.get("subject") == subject:
        st.markdown(f"### {exp['topic']}")
        st.markdown(exp["text"])
        try:
            st.download_button(
                "Download explanation (PDF)",
                document_pdf(f"CSS {subject}: {exp['topic']}", [("Explanation", exp["text"])]),
                file_name="css_explanation.pdf",
                mime="application/pdf",
                key="dl_explanation",
            )
        except Exception as e:
            st.warning(f"Could not create the PDF: {e}")

    with st.expander("📚 My saved explanations for this subject"):
        if not cloud_on(ctx):
            st.caption("Enter a profile name (with cloud saving on) to keep explanations.")
        else:
            if st.button("Load my saved explanations", key="study_load_saved"):
                rows, err = storage.load_items(ctx["user_id"], "explanation")
                if err:
                    st.warning(err)
                else:
                    ss["saved_expl"] = [r["content"] for r in rows]
            saved = [e for e in ss.get("saved_expl", []) if e.get("subject") == subject]
            if saved:
                pick = st.selectbox("Saved topics", [e["topic"] for e in saved], key="study_saved_pick")
                for e in saved:
                    if e["topic"] == pick:
                        st.markdown(e["text"])
                        break
