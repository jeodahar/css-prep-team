import streamlit as st

import storage
from config import get_llm
from crew_prepare import run_preparation
from pdf_export import package_pdf
from tool_syllabus import preview_section
from ui_common import cloud_on, current_package, show_error


def render(ctx):
    ss = st.session_state
    subject, marks, n_questions, user_id = ctx["subject"], int(ctx["marks"]), ctx["n_questions"], ctx["user_id"]

    focus = st.text_input("Focus topic (optional)", placeholder="e.g. Constitutional development")
    if ss.get("syllabus_ok"):
        with st.expander("Check: official syllabus text the agents will read for this subject"):
            st.text(preview_section(subject))

    if st.button("Build my preparation package", type="primary"):
        try:
            llm = get_llm()
            partial = ss.setdefault("partial", {})
            sig = (subject, focus, n_questions, marks)
            if ss.get("partial_sig") != sig:
                partial.clear()
                ss["partial_sig"] = sig
            with st.status(
                "4 agents are working (free Groq limits make this take ~5-8 minutes)...", expanded=True
            ) as status:
                pkg_new = run_preparation(
                    llm, subject, focus, n_questions, marks, partial, lambda m: st.write(m)
                )
                status.update(label="Package ready", state="complete", expanded=False)
            ss["package"] = pkg_new
            ss["package_subject"] = subject
            partial.clear()
            if cloud_on(ctx):
                err = storage.save_package(user_id, subject, pkg_new)
                st.warning(err) if err else st.success("Package saved to your profile.")
        except Exception as e:
            show_error(e)
            if ss.get("partial"):
                st.info("Finished steps are kept. Click the button again to continue from where it stopped.")

    pkg = current_package(subject)
    if pkg:
        t1, t2, t3, t4 = st.tabs(["Topics", "Past paper analysis", "Notes", "Questions"])
        t1.markdown(pkg["topics"])
        t2.markdown(pkg["past_papers"])
        t3.markdown(pkg["notes"])
        t4.markdown(pkg["questions"])
        try:
            st.download_button(
                "Download package (PDF)",
                package_pdf(subject, pkg),
                file_name="css_preparation_package.pdf",
                mime="application/pdf",
            )
        except Exception as e:
            st.warning(f"Could not create the PDF: {e}")
