import streamlit as st
import pandas as pd
import requests
import io
import json
from urllib.parse import urlparse

# --- Config ---
st.set_page_config(
    page_title="Ads.txt Inspector",
    layout="wide"
)

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
    # Returns structured dict or None if empty
    clean = line.split('#')[0].strip()
    if not clean: return None
    parts = [p.strip() for p in clean.split(',')]
    
    # Basic Validation
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
    seen_keys = set()
    
    warnings = []
    output_lines = []
    
    stats = {'valid': 0, 'errors': 0, 'duplicates': 0, 'direct': 0, 'reseller': 0}

    for idx, line in enumerate(lines, 1):
        parsed = parse_line_data(line)
        
        # Keep comments/empty lines in output but skip analysis
        if not parsed:
            output_lines.append({'num': idx, 'text': line, 'status': 'neutral'})
            continue

        # Check Logic
        unique_key = f"{parsed['domain']}_{parsed['pub_id']}_{parsed['type']}".lower()
        is_dup = unique_key in seen_keys
        
        status = 'valid'
        if parsed['is_error']:
            status = 'error'
            stats['errors'] += 1
            warnings.append(f"Line {idx}: Invalid format (Fields missing or wrong Type)")
        elif is_dup:
            status = 'duplicate'
            stats['duplicates'] += 1
            warnings.append(f"Line {idx}: Duplicate record")
        else:
            stats['valid'] += 1
            if parsed['type'] == 'DIRECT': stats['direct'] += 1
            elif parsed['type'] == 'RESELLER': stats['reseller'] += 1
            seen_keys.add(unique_key)
            
            # Add to structured data for DataFrame
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

# --- UI: Sidebar ---
with st.sidebar:
    st.header("Input Source")
    input_method = st.radio("Choose method:", ["Fetch URL", "Upload File", "Paste Text"])
    
    content_source = None
    
    if input_method == "Fetch URL":
        url = st.text_input("Domain / URL", placeholder="example.com")
        ftype = st.selectbox("File Type", ["app-ads.txt", "ads.txt"])
        if st.button("Fetch", type="primary"):
            try:
                domain = clean_url(url)
                target = f"https://{domain}/{ftype}"
                r = requests.get(target, timeout=10, headers={'User-Agent': 'Mozilla/5.0'})
                if r.status_code == 200:
                    content_source = r.text
                    st.success("Fetched successfully")
                else:
                    st.error(f"Error: {r.status_code}")
            except Exception as e:
                st.error(f"Failed: {e}")

    elif input_method == "Upload File":
        uploaded = st.file_uploader("Choose txt file", type=['txt'])
        if uploaded:
            content_source = uploaded.read().decode("utf-8")

    elif input_method == "Paste Text":
        pasted = st.text_area("Paste content here", height=200)
        if st.button("Analyze Paste"):
            content_source = pasted

    if content_source:
        st.session_state.raw_content = content_source
        st.session_state.processed_content = None # Reset edits

    st.divider()
    st.caption("Supports Ads.txt & App-ads.txt spec 1.0+")

# --- Main Logic ---

content = st.session_state.processed_content if st.session_state.processed_content else st.session_state.raw_content

if content:
    # RUN ANALYSIS
    lines_meta, df_data, stats, logs = analyze_text(content)
    df = pd.DataFrame(df_data)

    st.title("Ads.txt Inspector & Editor")
    
    # 1. METRICS
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Valid Records", stats['valid'])
    m2.metric("Errors", stats['errors'])
    m3.metric("Duplicates", stats['duplicates'])
    m4.metric("Total Lines", len(lines_meta))

    # 2. ACTIONS TOOLBAR
    col_act1, col_act2, col_act3, col_act4 = st.columns([1,1,1,2])
    
    if col_act1.button("Auto-Fix"):
        # Remove dups and comment errors
        new_lines = []
        for item in lines_meta:
            # Logic: If error -> comment. If valid but dup -> skip.
            if item['status'] == 'error' and not item['text'].strip().startswith('#'):
                new_lines.append(f"# {item['text']} (Invalid Format)")
            elif item['status'] == 'duplicate':
                continue # Remove strictly
            else:
                new_lines.append(item['text'])
        st.session_state.processed_content = "\n".join(new_lines)
        st.rerun()

    if col_act2.button("Start Over"):
        st.session_state.processed_content = None
        st.rerun()
        
    with col_act4:
        st.download_button("Download Result (.txt)", content, file_name="ads.txt")

    st.divider()

    # 3. TABS INTERFACE
    tab_view, tab_data, tab_charts = st.tabs(["Code Editor", "Data Grid", "Analytics"])

    # --- TAB 1: CODE VIEW ---
    with tab_view:
        c_code, c_log = st.columns([3, 1])
        with c_code:
            st.text_area("File Content (Read Only View)", value=content, height=600)
        with c_log:
            st.subheader("Issues Log")
            if not logs:
                st.success("No issues found.")
            else:
                with st.container(height=600):
                    for msg in logs:
                        if "Invalid" in msg: st.error(msg)
                        else: st.warning(msg)

    # --- TAB 2: DATA GRID & EXPORT ---
    with tab_data:
        if not df.empty:
            # Search
            search = st.text_input("Search Domain or ID", placeholder="Type to filter...")
            if search:
                mask = df.astype(str).apply(lambda x: x.str.contains(search, case=False)).any(axis=1)
                df_show = df[mask]
            else:
                df_show = df
            
            st.dataframe(df_show, use_container_width=True, hide_index=True)
            
            # Exports
            e1, e2 = st.columns(2)
            csv = df_show.to_csv(index=False).encode('utf-8')
            e1.download_button("Download CSV", csv, "ads_data.csv", "text/csv")
            
            json_str = df_show.to_json(orient="records")
            e2.download_button("Download JSON", json_str, "ads_data.json", "application/json")
        else:
            st.info("No valid data records found to display in table.")

    # --- TAB 3: ANALYTICS ---
    with tab_charts:
        if not df.empty:
            row1_1, row1_2 = st.columns(2)
            
            with row1_1:
                st.subheader("Account Types")
                type_counts = df['Type'].value_counts()
                st.bar_chart(type_counts)
                
            with row1_2:
                st.subheader("Top 10 Ad Systems")
                top_domains = df['Domain'].value_counts().head(10)
                st.bar_chart(top_domains)
                
            st.subheader("Certification Authority Usage")
            auth_counts = df['Authority ID'].replace('', 'Missing').value_counts()
            st.bar_chart(auth_counts)
        else:
            st.write("No data available for analytics.")

else:
    st.markdown("""
    ### Welcome to the Ads.txt Inspector
    Use the sidebar to load your file.
    
    **Features:**
    * **Auto-Fix:** Removes duplicates and comments out syntax errors.
    * **Analytics:** Visualize your Direct vs Reseller split.
    * **Search:** Filter large files instantly.
    * **Export:** Convert your txt file to CSV or JSON.
    """)
