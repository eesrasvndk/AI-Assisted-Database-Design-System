import graphviz
import pandas as pd
import streamlit as st

from ai_services import OpenAI, get_ai_design
#calling function from other files
from database import (fetch_project_history_data, get_project_list,
                      save_ai_results_to_db, save_project_init)

#settings
st.set_page_config(page_title="AI Assisted Database Design System", layout="wide")

st.title("AI Assisted Database Design System")

#Old Projects
st.sidebar.title("🗄️ Project History")
project_options = {p[0]: p[1] for p in get_project_list()}

selected_id = st.sidebar.selectbox("Select Project", options=list(project_options.keys()), format_func=lambda x: project_options[x] if x in project_options else "None")

if st.sidebar.button("Load Project"):
    st.session_state['active_project_id'] = selected_id
    st.session_state['mode'] = 'history'
    st.session_state['ai_data'] = None

#managing state
if 'ai_data' not in st.session_state: st.session_state['ai_data'] = None
if 'mode' not in st.session_state: st.session_state['mode'] = 'new'


#logic of main page
if st.session_state['mode'] == 'history':
    st.info(f"Viewing History: **{project_options.get(st.session_state['active_project_id'])}**")
    if not st.session_state['ai_data']:
        st.session_state['ai_data'] = fetch_project_history_data(st.session_state['active_project_id'])
    
    if st.button("⬅️ Create New Project"):
        st.session_state['mode'] = 'new'
        st.session_state['ai_data'] = None
        st.rerun()

else:
    #new project template
    with st.expander("📝 Project Definition Form", expanded=True):
        c1, c2 = st.columns(2)
        with c1:
            user_info = st.text_input("User Info", " John Doe")
            p_name = st.text_input("Project Name", "Library System")
            domain = st.text_input("Domain", "Library")
            common_tasks = st.text_input("Common Tasks", "Borrowing")
        with c2:
            entity = st.text_input("Primary Entity", "Books, Members")
            reporting = st.text_input("Reporting", "Popular books")
            security = st.text_input("Security", "Admin only")
            advanced = st.text_input("Advanced", "Fine calculation")
        constraints = st.text_area("Constraints", "ISBN must be unique.")
        
        if st.button("Design & Save"):
            with st.spinner("AI is thinking..."):
                pid = save_project_init(p_name, user_info, domain, entity, constraints, advanced, security, reporting, common_tasks)
                if pid:
                    st.success(f"Saved! ID: {pid}")
                    data = get_ai_design(domain, entity, constraints, advanced, security, reporting, common_tasks)
                    if data:
                        save_ai_results_to_db(pid, data)
                        st.session_state['ai_data'] = data
                    else:
                        st.error("AI failed.")

#seeing results
if st.session_state.get('ai_data'):
    data = st.session_state['ai_data']
    t1, t2, t3, t4, t5 = st.tabs(["Rules", "Tables", "Normalization", "ER Diagram", "SQL Code"])
    
    with t1: st.dataframe(pd.DataFrame(data.get("business_rules", [])))
    with t2:
        for t in data.get("tables", []):
            st.markdown(f"**{t['TableName']}**")
            st.dataframe(pd.DataFrame(t['Columns']))
    with t3: st.markdown(data.get("normalization_steps", ""))
    with t4:
        if data.get("graphviz_dot"): st.graphviz_chart(data["graphviz_dot"])
    with t5: st.code(data.get("sql_code", ""), language="sql")