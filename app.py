"""Streamlit app for validating and analyzing ads.txt-style files."""

import cloudscraper
import streamlit as st

from inspector.analyzer import analyze_text, clean_url
from inspector.render import load_css, render_logs, render_metrics, render_result_header

st.set_page_config(page_title="Ads.txt Inspector", layout="wide")
st.markdown(load_css(), unsafe_allow_html=True)

if "raw_content" not in st.session_state:
    st.session_state.raw_content = None
if "processed_content" not in st.session_state:
    st.session_state.processed_content = None
if "view_mode" not in st.session_state:
    st.session_state.view_mode = "all"

col_input1, col_input2, col_input3 = st.columns([6, 2, 2])
with col_input1:
    url_input = st.text_input("URL", placeholder="https://actu.fr/", label_visibility="collapsed")
with col_input2:
    file_type = st.selectbox("File Type", ["app-ads.txt", "ads.txt"], label_visibility="collapsed")
with col_input3:
    if st.button("Validate", type="primary", use_container_width=True):
        if url_input:
            try:
                domain = clean_url(url_input)
                target_url = f"https://{domain}/{file_type}"
                scraper = cloudscraper.create_scraper(
                    browser={"browser": "chrome", "platform": "windows", "mobile": False}
                )
                response = scraper.get(target_url, timeout=15)
                if response.status_code == 200:
                    st.session_state.raw_content = response.text
                    st.session_state.processed_content = None
                    st.session_state.view_mode = "all"
                    st.session_state.current_domain = domain
                else:
                    st.error(
                        f"Error {response.status_code}: Could not fetch file from {target_url}. "
                        "Access might be blocked."
                    )
            except Exception as exc:
                st.error(f"Failed to fetch {target_url}: {exc}")

content = (
    st.session_state.processed_content
    if st.session_state.processed_content is not None
    else st.session_state.raw_content
)

if content:
    lines_meta, _, stats, logs = analyze_text(content)
    domain_display = st.session_state.get("current_domain", "Local File")

    st.markdown(render_result_header(domain_display), unsafe_allow_html=True)
    st.markdown(render_metrics(stats), unsafe_allow_html=True)

    b1, b2, b3, b4, spacer, b5 = st.columns([2, 2, 2.5, 2.5, 3, 2])

    if b1.button("Show Errors Only", use_container_width=True):
        st.session_state.view_mode = "errors"
    if b2.button("Show All", use_container_width=True):
        st.session_state.view_mode = "all"

    if b3.button("Comment Out Errors", use_container_width=True):
        new_lines = []
        for item in lines_meta:
            if item["status"] == "error" and not item["text"].strip().startswith("#"):
                new_lines.append(f"# {item['text']} (Invalid format)")
            else:
                new_lines.append(item["text"])
        st.session_state.processed_content = "\n".join(new_lines)
        st.rerun()

    if b4.button("Remove Duplicates", use_container_width=True):
        new_lines = [item["text"] for item in lines_meta if item["status"] != "duplicate"]
        st.session_state.processed_content = "\n".join(new_lines)
        st.rerun()

    with b5:
        st.download_button(
            "Download File",
            content,
            file_name="app-ads-optimized.txt",
            use_container_width=True,
        )

    col_code, col_logs = st.columns([7, 4])

    with col_code:
        display_text = content
        if st.session_state.view_mode == "errors":
            error_lines = [item["text"] for item in lines_meta if item["status"] == "error"]
            display_text = "\n".join(error_lines) if error_lines else "No errors to display."
        st.text_area("Code", value=display_text, height=550, label_visibility="collapsed")

    with col_logs:
        st.markdown(render_logs(logs), unsafe_allow_html=True)
else:
    st.info("Please enter a domain above, select file type, and click Validate to start.")
