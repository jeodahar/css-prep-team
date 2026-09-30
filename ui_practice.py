from datetime import datetime

import streamlit as st

import storage
from config import get_llm
from crew_assess import run_assessment
from ocr import extract_text
from pdf_export import reports_pdf
from progress import parse_assessment
from ui_common import CUSTOM_Q, cloud_on, current_package, question_options, show_error


def _assess(ctx, question, answer, source):
    ss = st.session_state
    total = int(ctx["marks"])
    try:
        llm = get_llm()
        with st.status(
            "The assessor is marking your answer (about 2-3 minutes on the free Groq plan)...", expanded=True
        ) as status:
            raw = run_assessment(
                llm, ctx["subject"], question, answer, total,
                progress=lambda m: st.write(m), from_photo=(source == "photo"),
            )
            status.update(label="Assessment ready", state="complete", expanded=False)
        clean, data = parse_assessment(raw, total)
        item = {
            "time": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "subject": ctx["subject"],
            "question": question,
            "answer": answer,
            "report": clean,
            "marks": data["marks"],
            "total": total,
            "criteria": data["criteria"],
            "weak_topics": data["weak_topics"],
            "source": source,
        }
        ss["history"].append(item)
        ss["last_report"] = item
        if cloud_on(ctx):
            err = storage.save_report(ctx["user_id"], ctx["subject"], item)
            st.warning(err) if err else st.success("Report saved to your profile.")
    except Exception as e:
        show_error(e)


def render(ctx):
    ss = st.session_state
    subject = ctx["subject"]
    st.subheader("✍️ Answer practice")

    options = question_options(current_package(subject))
    choice = st.selectbox("Choose a question", options + [CUSTOM_Q], key="practice_choice")
    question = st.text_area("Question", value="" if choice == CUSTOM_Q else choice, height=90, key=f"practice_q_{choice}")

    mode = st.radio(
        "How will you answer?", ["⌨️ Type my answer", "📷 Upload handwritten photo"], horizontal=True, key="practice_mode"
    )

    if mode.startswith("⌨"):
        answer = st.text_area("Your answer", height=320, placeholder="Type or paste your answer here...", key="typed_answer")
        if st.button("Assess my answer", type="primary", key="assess_typed"):
            if not question.strip() or len(answer.split()) < 30:
                st.warning("Please add a question and an answer of at least 30 words.")
            else:
                _assess(ctx, question, answer, "typed")
    else:
        st.caption("Tips: good light, flat page, dark pen, one page per photo (up to 3 photos).")
        photos = st.file_uploader(
            "Photo(s) of your handwritten answer", type=["png", "jpg", "jpeg"], accept_multiple_files=True, key="photos"
        )
        photos = (photos or [])[:3]
        if photos:
            st.image([p.getvalue() for p in photos], width=160)
            if st.button("📷 Extract text (OCR)", key="ocr_btn"):
                texts, notes, method = [], set(), ""
                with st.status("Reading your handwriting...", expanded=True) as status:
                    for i, p in enumerate(photos, 1):
                        st.write(f"Reading photo {i} of {len(photos)}...")
                        text, method, note = extract_text(p.getvalue(), progress=lambda m: st.write(m))
                        if note:
                            notes.add(note)
                        if text:
                            texts.append(text)
                    status.update(label="Text extracted. Please check it below.", state="complete", expanded=False)
                ss["ocr_text_area"] = "\n\n".join(texts)
                ss["ocr_info"] = f"Read with: {method}. " + " ".join(sorted(notes))
        if ss.get("ocr_info"):
            st.caption(ss["ocr_info"])
        answer = st.text_area(
            "Extracted text (fix any mistakes before assessing)", height=320, key="ocr_text_area"
        )
        if st.button("Assess this answer", type="primary", key="assess_photo"):
            if not question.strip() or len(answer.split()) < 30:
                st.warning("Please add a question and extract at least 30 words of text.")
            else:
                _assess(ctx, question, answer, "photo")

    rep = ss.get("last_report")
    if rep:
        st.divider()
        st.subheader("Latest assessment")
        if rep.get("marks") is not None and rep.get("total"):
            st.metric("Marks", f"{rep['marks']:g} / {rep['total']}")
        st.markdown(rep["report"])
        if rep.get("weak_topics"):
            st.info("Weak topics recorded: " + ", ".join(rep["weak_topics"]))
        try:
            st.download_button(
                "Download this report (PDF)",
                reports_pdf([rep]),
                file_name="css_report.pdf",
                mime="application/pdf",
                key="dl_latest",
            )
        except Exception as e:
            st.warning(f"Could not create the PDF: {e}")
