from datetime import datetime

import streamlit as st

import storage
from config import CSS_SUBJECTS, get_llm
from crew_study import run_study_plan
from pdf_export import document_pdf
from progress import study_context_text, topic_names
from tool_progress import set_study_context
from ui_common import cloud_on, show_error


def _topics_for(ctx, subj):
    ss = st.session_state
    if ss.get("package") and ss.get("package_subject") == subj:
        return topic_names(ss["package"]["topics"])
    if cloud_on(ctx):
        rows, err = storage.load_items(ctx["user_id"], "package", subj)
        if rows and not err:
            return topic_names(rows[-1]["content"].get("topics", ""))
    return []


def render(ctx):
    ss = st.session_state
    st.subheader("📅 Study plan")
    st.caption("A day-by-day plan that puts your recorded weak areas first. Do a few assessments first for best results.")

    choices = [s for s in CSS_SUBJECTS if s != "Other"]
    default = [ctx["subject"]] if ctx["subject"] in choices else choices[:1]
    subjects = st.multiselect("Subjects to plan", choices, default=default, key="plan_subjects")
    c1, c2 = st.columns(2)
    days = c1.number_input("Days until you want to be ready", min_value=3, max_value=60, value=14, step=1, key="plan_days")
    hours = c2.number_input("Study hours per day", min_value=1.0, max_value=12.0, value=4.0, step=0.5, key="plan_hours")

    if st.button("Create my study plan", type="primary", key="plan_btn"):
        if not subjects:
            st.warning("Please choose at least one subject.")
        else:
            try:
                topics = {s: _topics_for(ctx, s) for s in subjects}
                context = study_context_text(ss["history"], subjects, topics)
                set_study_context(context)
                llm = get_llm()
                with st.status("The planner is building your plan...", expanded=True) as status:
                    text = run_study_plan(llm, subjects, int(days), f"{hours:g}", lambda m: st.write(m))
                    status.update(label="Plan ready", state="complete", expanded=False)
                item = {
                    "subjects": subjects, "days": int(days), "hours": hours, "text": text,
                    "based_on": context, "time": datetime.now().strftime("%Y-%m-%d %H:%M"),
                }
                ss["last_plan"] = item
                if cloud_on(ctx):
                    err = storage.save_replace(ctx["user_id"], "plan", "current", item)
                    st.warning(err) if err else st.success("Plan saved to your profile.")
            except Exception as e:
                show_error(e)

    plan = ss.get("last_plan")
    if plan:
        st.markdown(f"**Plan for:** {', '.join(plan['subjects'])} · {plan['days']} days · {plan['hours']:g} h/day · made {plan['time']}")
        st.markdown(plan["text"])
        with st.expander("Weak areas and topics this plan was based on"):
            st.text(plan.get("based_on") or "No recorded data.")
        try:
            st.download_button(
                "Download plan (PDF)",
                document_pdf("CSS Study Plan", [("Plan", plan["text"]), ("Based on", plan.get("based_on") or "")]),
                file_name="css_study_plan.pdf",
                mime="application/pdf",
                key="dl_plan",
            )
        except Exception as e:
            st.warning(f"Could not create the PDF: {e}")
