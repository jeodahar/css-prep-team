import streamlit as st

from config import get_llm
from crew_study import run_question_analysis
from pdf_export import document_pdf
from ui_common import CUSTOM_Q, current_package, question_options, show_error


def render(ctx):
    ss = st.session_state
    subject = ctx["subject"]
    st.subheader("🔍 Question analysis")
    st.caption("Find out what a question is really asking before you write a single line.")

    options = question_options(current_package(subject))
    choice = st.selectbox("Choose a question", options + [CUSTOM_Q], key="qa_choice")
    question = st.text_area("Question", value="" if choice == CUSTOM_Q else choice, height=100, key=f"qa_text_{choice}")

    if st.button("Analyse this question", type="primary", key="qa_btn"):
        if len(question.split()) < 4:
            st.warning("Please choose or type a full question.")
        else:
            try:
                llm = get_llm()
                with st.status("The analyst is reading the question...", expanded=True) as status:
                    text = run_question_analysis(llm, subject, question.strip(), lambda m: st.write(m))
                    status.update(label="Analysis ready", state="complete", expanded=False)
                ss["last_qanalysis"] = {"subject": subject, "question": question.strip(), "text": text}
            except Exception as e:
                show_error(e)

    qa = ss.get("last_qanalysis")
    if qa and qa.get("subject") == subject:
        st.markdown(f"**Question:** {qa['question']}")
        st.markdown(qa["text"])
        try:
            st.download_button(
                "Download analysis (PDF)",
                document_pdf(f"CSS {subject}: Question analysis", [("Question", qa["question"]), ("Analysis", qa["text"])]),
                file_name="css_question_analysis.pdf",
                mime="application/pdf",
                key="dl_qanalysis",
            )
        except Exception as e:
            st.warning(f"Could not create the PDF: {e}")
