import streamlit as st

from pdf_export import reports_pdf
from progress import summarize
from ui_common import cloud_on


def render_progress(ctx):
    ss = st.session_state
    st.subheader("📊 Progress")
    history = ss["history"]
    if not history:
        st.info("No assessments yet. Assess an answer in the Answer practice tab and your progress will appear here.")
        return
    if not cloud_on(ctx):
        st.caption("Not saved to the cloud. Enter a profile name (with cloud saving on) so progress survives closing the app.")

    subjects = sorted({h.get("subject", "?") for h in history})
    pick = st.selectbox("Show", ["All subjects"] + subjects, key="progress_subject")
    s = summarize(history, None if pick == "All subjects" else pick)

    c1, c2, c3 = st.columns(3)
    c1.metric("Assessments", s["count"])
    c2.metric("Average", f"{s['avg']:.0f}%" if s["avg"] is not None else "-")
    c3.metric("Latest", f"{s['latest']:.0f}%" if s["latest"] is not None else "-")

    if len(s["trend"]) >= 2:
        import pandas as pd

        st.markdown("**Score trend (% per answer)**")
        st.line_chart(pd.DataFrame({"Score %": [p for _, p in s["trend"]]}, index=range(1, len(s["trend"]) + 1)))

    crit = {v["label"]: round(v["avg"], 1) for v in s["criteria"].values() if v["avg"] is not None}
    if crit:
        import pandas as pd

        st.markdown("**Average by skill (%)**")
        st.bar_chart(pd.DataFrame({"Average %": crit}))

    st.markdown("### Repeated weak areas")
    weak = sorted(
        (v for v in s["criteria"].values() if v["n"] and (v["avg"] < 60 or v["weak_count"] >= 2)),
        key=lambda v: v["avg"],
    )
    if weak:
        for v in weak:
            st.markdown(f"- **{v['label']}**: average {v['avg']:.0f}%, weak in {v['weak_count']} of {v['n']} answers")
    else:
        st.caption("No repeated weak skills yet. Keep practising.")
    if s["topics"]:
        st.markdown("**Weak topics (most repeated first)**")
        for topic, count in s["topics"]:
            st.markdown(f"- {topic} (flagged {count}x)")
    if len(s["subjects"]) > 1:
        st.markdown("**Average by subject**")
        for subj, avg in sorted(s["subjects"].items()):
            st.markdown(f"- {subj}: {avg:.0f}%")


def render_reports(ctx):
    ss = st.session_state
    st.subheader("📁 Reports")
    if not ss["history"]:
        st.info("No assessments yet.")
        return
    for n, item in enumerate(reversed(ss["history"])):
        marks = ""
        if item.get("marks") is not None and item.get("total"):
            marks = f" - {item['marks']:g}/{item['total']}"
        with st.expander(f"{item['time']} - {item['subject']}{marks}: {item['question'][:60]}"):
            st.markdown(item["report"])
            if item.get("answer"):
                st.caption("Your answer" + (" (from photo)" if item.get("source") == "photo" else ""))
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
