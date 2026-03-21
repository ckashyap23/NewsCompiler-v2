"""
Streamlit app: Research a topic and email the summary to recipients.
"""
import re
import streamlit as st

from send_email import send_email
from topic_research import run_topic_research


def parse_emails(raw: str) -> list[str]:
    """Parse comma- or newline-separated email addresses."""
    addresses = re.split(r"[\s,;]+", raw.strip())
    return [a.strip() for a in addresses if a.strip()]


st.set_page_config(page_title="Topic Research & Email", page_icon="📧")

st.title("Topic Research & Email")
st.markdown("Enter a topic and recipient emails. The app will research the topic and email the summary.")

topic = st.text_input("Topic", placeholder="e.g. tech trends in India")

st.markdown("**Recipient emails** (comma or newline separated)")
emails_raw = st.text_area("Email addresses", placeholder="alice@example.com, bob@example.com", height=100)

if st.button("Research & Send", type="primary"):
    if not topic or not topic.strip():
        st.error("Please enter a topic.")
    elif not emails_raw or not emails_raw.strip():
        st.error("Please enter at least one email address.")
    else:
        recipients = parse_emails(emails_raw)
        invalid = [e for e in recipients if not re.match(r"^[\w\.\-]+@[\w\.\-]+\.\w+$", e)]
        if invalid:
            st.error(f"Invalid email address(es): {', '.join(invalid)}")
        else:
            topic_clean = topic.strip()
            with st.spinner("Researching topic…"):
                try:
                    summary = run_topic_research(topic_clean)
                except Exception as e:
                    st.error(f"Research failed: {e}")
                else:
                    st.divider()
                    st.subheader("Research Summary")
                    st.markdown(summary)

                    with st.spinner("Sending email…"):
                        try:
                            send_email(summary, recipients, subject=f"Topic Research: {topic_clean}")
                            st.success(f"✅ Email sent successfully to {len(recipients)} recipient(s).")
                        except Exception as e:
                            st.error(f"Email failed: {e}. The summary above is available for you to copy.")
