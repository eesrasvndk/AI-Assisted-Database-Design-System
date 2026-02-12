import json

import streamlit as st
from openai import OpenAI

from config import OPENAI_API_KEY


def get_ai_design(domain, entity, constraints, advanced, security, reporting, common_tasks):
    
    # 1. API Key Kontrolü
    if not OPENAI_API_KEY or "sk-" not in OPENAI_API_KEY:
        st.error("The API Key is not defined in the config.py file!")
        return None

    client = OpenAI(api_key=OPENAI_API_KEY)

    # 2.prompt (Crow's Foot & Advanced SQL)
    prompt = f"""
    Act as a Senior Database Architect. Design a complete normalized database for:
    Domain: {domain}
    Primary Entity: {entity}
    Constraints: {constraints}
    Advanced Features: {advanced}
    Security: {security}
    Reporting: {reporting}
    Common Tasks: {common_tasks}

    CRITICAL INSTRUCTION: Output MUST be a valid JSON object. Do not include any text outside the JSON.
    
    To ensure nothing is cut off, generate the JSON keys in THIS EXACT ORDER:
    1. "sql_code"
    2. "graphviz_dot"
    3. "business_rules"
    4. "tables"
    5. "normalization_steps"

    DETAILED REQUIREMENTS FOR EACH KEY:

    1. "sql_code": 
       - Write full CREATE TABLE statements with constraints (PK, FK).
       - INCLUDE at least 1 CREATE TRIGGER (e.g., for logging or checks).
       - INCLUDE at least 1 CREATE VIEW (for reporting).
       - INCLUDE at least 1 CREATE ROLE (for security).
       - INCLUDE at least 3 COMPLEX SELECT QUERIES that satisfy the '{reporting}' requirement (use JOINs, GROUP BY, etc.).
       
    2. "graphviz_dot": 
       - Generate valid Graphviz DOT syntax using Crow's Foot Notation style.
       - Use `rankdir=LR;`
       - Tables must use HTML-like labels to show columns (e.g., <<table...>>).
       - Relationships MUST use Crow's Foot attributes:
         * One-to-Many: `edge [dir=both arrowtail=tee arrowhead=crow];`
         * Many-to-Many: `edge [dir=both arrowtail=crow arrowhead=crow];`
         * One-to-One: `edge [dir=both arrowtail=tee arrowhead=tee];`
       - Label the edges with specific cardinalities (e.g., label="1:N").
       
    3. "business_rules": 
       - Array of objects: {{ "BR_ID": "BR-01", "Type": "Structural", "RuleStatement": "...", "ERComponent": "Entity", "ImplementationTip": "...", "Rationale": "..." }}

    4. "tables": 
       - Array of objects: {{ "TableName": "...", "Description": "...", "Columns": [ {{ "ColumnName": "...", "DataType": "...", "IsPrimaryKey": true, "IsForeignKey": false, "IsNullable": false, "TargetTable": null, "ExtraConstraint": null }} ] }}

    5. "normalization_steps": 
       - Return a SINGLE STRING formatted in MARKDOWN.
       - Be CONCISE.
       - Create a STEP-BY-STEP SCENARIO with DUMMY DATA.
       - Format: 
         ### 0NF
         (Brief explanation + Raw Markdown Table)
         ### 1NF
         (Brief explanation + Atomic Markdown Tables)
         ### 2NF
         (Brief explanation + Thematic Markdown Tables)
         ### 3NF
         (Brief explanation + Final Markdown Tables)
    """

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a JSON generator. Respond ONLY with valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=3500
        )
        content = response.choices[0].message.content
        
        # Temizlik
        content = content.replace("```json", "").replace("```", "").strip()
        
        return json.loads(content)
    except Exception as e:
        st.error(f"AI error: {e}")
        return None