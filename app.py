"""Streamlit app for validating and analyzing ads.txt-style files."""

import streamlit as st
import pandas as pd
import cloudscraper
import io
import json
from urllib.parse import urlparse

# --- Config ---
st.set_page_config(
    page_title="Ads.txt Inspector",
    layout="wide"
)

# --- Custom CSS ---
st.markdown("""
<style>
    .metric-container {
        display: flex;
        justify-content: space-between;
        gap: 20px;
        margin-bottom: 20px;
        margin-top: 10px;
    }
    .box {
        flex: 1;
        padding: 15px 20px;
        border-radius: 5px;
        font-size: 16px;
        border: 1px solid transparent;
    }
    .box-blue {
        background-color: #d9edf7;
        border-color: #bce8f1;
        color: #31708f;
    }
    .box-red {
        background-color: #f2dede;
        border-color: #ebccd1;
        color: #a94442;
    }
    .box-yellow {
        background-color: #fcf8e3;
        border-color: #faebcc;
        color: #8a6d3b;
    }
    .log-container {
        height: 550px;
        overflow-y: auto;
        padding: 10px;
        border: 1px solid #ddd;
        border-radius: 5px;
        background-color: #fff;
    }
    .log-item {
        margin-bottom: 6px;
        font-size: 14px;
    }
    .log-error { color: #cc0000; }
    .log-warning { color: #b38600; }
    .icon-red { color: #cc0000; font-weight: bold; margin-right: 5px; }
    .icon-yellow { color: #b38600; font-weight: bold; margin-right: 5px; }
</style>
""", unsafe_allow_html=True)


# --- Helper Functions ---
def clean_url(url):
    if not url: return None
    if not url.startswith(('http://', 'https://')): url = 'https://' + url
    try:
        parsed = urlparse(url)
        return parsed.netloc if parsed.netloc else parsed.path
    except:
        return url

def parse_line_data(line):
    clean = line.split('#')[0].strip()
    if not clean: return None
    parts = [p.strip() for p in clean.split(',')]
    
    is_valid_fmt = len(parts) >= 3
    is_valid_type = False
    if is_valid_fmt:
        is_valid_type = parts[2].upper() in ['DIRECT', 'RESELLER']

    return {
        'domain': parts[0] if len(parts) > 0 else '',
        'pub_id': parts[1] if len(parts) > 1 else '',
        'type': parts[2].upper() if len(parts) > 2 else '',
        'auth_id': parts[3] if len(parts) > 3 else '',
        'raw': line,
        'clean': clean,
        'is_error': not (is_valid_fmt and is_valid_type)
    }

def analyze_text(content):
    lines = content.splitlines()
    data_objects = []
    seen_keys = {} # Dict to track line numbers of original records
    
    warnings = []
    output_lines = []
    
    stats = {'valid': 0, 'errors': 0, 'duplicates': 0, 'unique': 0}

    for idx, line in enumerate(lines, 1):
        parsed = parse_line_data(line)
        
        if not parsed:
            output_lines.append({'num': idx, 'text': line, 'status': 'neutral'})
            continue

        unique_key = f"{parsed['domain']}_{parsed['pub_id']}_{parsed['type']}".lower()
        is_dup = unique_key in seen_keys
        
        status = 'valid'
        if parsed['is_error']:
            status = 'error'
            stats['errors'] += 1
            warnings.append({'type': 'error', 'msg': f"Line {idx}: Invalid syntax"})
        elif is_dup:
            status = 'duplicate'
            stats['duplicates'] += 1
            orig_line = seen_keys[unique_key]
            warnings.append({'type': 'warning', 'msg': f"Line {idx}: Duplicated record, already in line {orig_line}"})
        else:
            stats['valid'] += 1
            stats['unique'] += 1
            seen_keys[unique_key] = idx
            
            data_objects.append({
                'Line': idx,
                'Domain': parsed['domain'],
                'Publisher ID': parsed['pub_id'],
                'Type': parsed['type'],
                'Authority ID': parsed['auth_id']
            })

        output_lines.append({'num': idx, 'text': line, 'status': status})

    return output_lines, data_objects, stats, warnings


# --- Session Management ---
if 'raw_content' not in st.session_state: st.session_state.raw_content = None
if 'processed_content' not in st.session_state: st.session_state.processed_content = None
if 'view_mode' not in st.session_state: st.session_state.view_mode = 'all'


# --- Main UI ---
# 1. Top Input Bar
col_input1, col_input2 = st.columns([8, 1])
with col_input1:
    url = st.text_input("URL", placeholder="https://actu.fr/app-ads.txt", label_visibility="collapsed")
with col_input2:
    if st.button("Validate", type="primary", use_container_width=True):
        if url:
            try:
                # Use cloudscraper to bypass WAF/Cloudflare
                scraper = cloudscraper.create_scraper(
                    browser={'browser': 'chrome', 'platform': 'windows', 'mobile': False}
                )
                r = scraper.get(url, timeout=15)
                if r.status_code == 200:
                    st.session_state.raw_content = r.text
                    st.session_state.processed_content = None
                    st.session_state.view_mode = 'all'
                else:
                    st.error(f"Error {r.status_code}: Could not fetch file. Access might be blocked.")
            except Exception as e:
                st.error(f"Failed to fetch: {str(e)}")


# 2. Results Section
content = st.session_state.processed_content if st.session_state.processed_content is not None else st.session_state.raw_content

if content:
    lines_meta, df_data, stats, logs = analyze_text(content)
    domain_display = clean_url(url) if url else "Local File"

    st.markdown(f"<h3 style='text-align: center; margin-top: 30px;'>Results for {domain_display}</h3>", unsafe_allow_html=True)

    # Custom HTML Metrics
    metrics_html = f"""
    <div class="metric-container">
        <div class="box box-blue">Valid Records: <b>{stats['valid']}</b>, (without duplicates: <b>{stats['unique']}</b>)</div>
        <div class="box box-red">Errors: <b>{stats['errors']}</b></div>
        <div class="box box-yellow">Duplicates: <b>{stats['duplicates']}</b></div>
    </div>
    """
    st.markdown(metrics_html, unsafe_allow_html=True)

    # 3. Action Buttons
    b1, b2, b3, b4, spacer, b5 = st.columns([2, 2, 2.5, 2.5, 3, 2])
    
    if b1.button("Show Errors Only", use_container_width=True):
        st.session_state.view_mode = 'errors'
    if b2.button("Show All", use_container_width=True):
        st.session_state.view_mode = 'all'
        
    if b3.button("Comment Out Errors", use_container_width=True):
        new_lines = []
        for item in lines_meta:
            if item['status'] == 'error' and not item['text'].strip().startswith('#'):
                new_lines.append(f"# {item['text']} (Invalid format)")
            else:
                new_lines.append(item['text'])
        st.session_state.processed_content = "\n".join(new_lines)
        st.rerun()
        
    if b4.button("Remove Duplicates", use_container_width=True):
        new_lines = []
        for item in lines_meta:
            if item['status'] != 'duplicate':
                new_lines.append(item['text'])
        st.session_state.processed_content = "\n".join(new_lines)
        st.rerun()

    with b5:
        st.download_button("Download File", content, file_name="app-ads-optimized.txt", use_container_width=True)

    # 4. Code and Logs View
    col_code, col_logs = st.columns([7, 4])
    
    with col_code:
        display_text = content
        if st.session_state.view_mode == 'errors':
            error_lines = [item['text'] for item in lines_meta if item['status'] == 'error']
            display_text = "\n".join(error_lines) if error_lines else "No errors to display."
            
        st.text_area("Code", value=display_text, height=550, label_visibility="collapsed")
        
    with col_logs:
        log_html = "<div class='log-container'>"
        for log in logs:
            if log['type'] == 'error':
                log_html += f"<div class='log-item log-error'><span class='icon-red'>●</span>{log['msg']}</div>"
            else:
                log_html += f"<div class='log-item log-warning'><span class='icon-yellow'>▲</span>{log['msg']}</div>"
        
        if not logs:
            log_html += "<div style='color: green; font-weight: bold;'>No issues found.</div>"
            
        log_html += "</div>"
        st.markdown(log_html, unsafe_allow_html=True)

else:
    st.info("Please enter a URL above and click Validate to start.")
