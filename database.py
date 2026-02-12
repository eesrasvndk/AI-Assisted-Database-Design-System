import mysql.connector
import pandas as pd
import streamlit as st

from config import DB_CONFIG


def get_db_connection():
    try:
        return mysql.connector.connect(**DB_CONFIG)
    except mysql.connector.Error as err:
        st.error(f"Database Connection Error: {err}")
        return None

def save_project_init(name, user_info, domain, entity, constraints, advanced, security, reporting, common_tasks):
    conn = get_db_connection()
    if not conn: return None
    cursor = conn.cursor()
    try:
        sql_project = "INSERT INTO Projects (ProjectName, UserInfo) VALUES (%s, %s)"
        cursor.execute(sql_project, (name, user_info))
        project_id = cursor.lastrowid
        
        sql_input = """
            INSERT INTO ProjectInputs
            (ProjectID, Domain, PrimaryEntity, Constraints, AdvancedFeatures, SecurityRequirements, ReportingRequirements, CommonTasks)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        cursor.execute(sql_input, (project_id, domain, entity, constraints, advanced, security, reporting, common_tasks))
        conn.commit()
        return project_id
    except mysql.connector.Error as err:
        st.error(f"Registration Error (Init): {err}")
        return None
    finally:
        cursor.close()
        conn.close()

def save_ai_results_to_db(project_id, design_json):
    conn = get_db_connection()
    if not conn: return
    cursor = conn.cursor()
    try:
        #Business Rules
        if "business_rules" in design_json:
            sql_br = "INSERT INTO BusinessRules (ProjectID, BR_ID, RuleType, RuleStatement, ERComponent, ImplementationTip, Rationale) VALUES (%s, %s, %s, %s, %s, %s, %s)"
            for r in design_json["business_rules"]:
                cursor.execute(sql_br, (project_id, r.get('BR_ID'), r.get('Type'), r.get('RuleStatement'), r.get('ERComponent'), r.get('ImplementationTip'), r.get('Rationale')))

        #Designed Tables
        if "tables" in design_json:
            sql_table = "INSERT INTO DesignedTables (ProjectID, TableName, Description) VALUES (%s, %s, %s)"
            sql_col = "INSERT INTO DesignedColumns (TableID, ColumnName, DataType, IsPrimaryKey, IsForeignKey, IsNullable, TargetTable, ExtraConstraint) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"
            
            for tbl in design_json["tables"]:
                cursor.execute(sql_table, (project_id, tbl.get('TableName'), tbl.get('Description')))
                table_id = cursor.lastrowid
                if "Columns" in tbl:
                    for col in tbl["Columns"]:
                        cursor.execute(sql_col, (table_id, col.get('ColumnName'), col.get('DataType'), col.get('IsPrimaryKey', False), col.get('IsForeignKey', False), col.get('IsNullable', True), col.get('TargetTable', None), col.get('ExtraConstraint', None)))
        conn.commit()
    except mysql.connector.Error as err:
        st.error(f"Registration Error (AI Results): {err}")
    finally:
        cursor.close()
        conn.close()

def fetch_project_history_data(project_id):
    conn = get_db_connection()
    if not conn: return None
    data = {"business_rules": [], "tables": [], "sql_code": "", "graphviz_dot": "", "normalization_steps": ""}
    
    try:
        # 1. Rules
        df_rules = pd.read_sql(f"SELECT BR_ID, RuleType as Type, RuleStatement, ERComponent, ImplementationTip, Rationale FROM BusinessRules WHERE ProjectID = {project_id}", conn)
        data["business_rules"] = df_rules.to_dict('records')
        
        # 2. Tables & Reconstruction
        cursor = conn.cursor(dictionary=True)
        cursor.execute(f"SELECT TableID, TableName, Description FROM DesignedTables WHERE ProjectID = {project_id}")
        tables = cursor.fetchall()
        
        sql_statements = []
        dot_str = 'digraph G {\n  rankdir=LR;\n  node [shape=plaintext fontname="Arial"];\n'
        dot_nodes = []
        dot_edges = []
        
        for tbl in tables:
            t_id = tbl['TableID']
            t_name = tbl['TableName']
            cursor.execute(f"SELECT ColumnName, DataType, IsPrimaryKey, IsForeignKey, IsNullable, TargetTable, ExtraConstraint FROM DesignedColumns WHERE TableID = {t_id}")
            columns = cursor.fetchall()
            
            data["tables"].append({"TableName": t_name, "Description": tbl['Description'], "Columns": columns})
            
            # SQL Generation
            col_defs = []
            label_html = f'<<table border="0" cellborder="1" cellspacing="0"><tr><td bgcolor="lightgrey"><b>{t_name}</b></td></tr>'
            
            for col in columns:
                def_str = f"{col['ColumnName']} {col['DataType']}"
                if col['IsPrimaryKey']: def_str += " PRIMARY KEY"
                if not col['IsNullable']: def_str += " NOT NULL"
                if col['ExtraConstraint']: def_str += f" {col['ExtraConstraint']}"
                col_defs.append(def_str)
                
                port_name = col['ColumnName']
                label_html += f'<tr><td port="{port_name}" align="left">{col["ColumnName"]}</td></tr>'
                if col['IsForeignKey'] and col['TargetTable']:
                    dot_edges.append(f'  {t_name}:{port_name} -> {col["TargetTable"]} [label="FK"];')

            label_html += "</table>>"
            dot_nodes.append(f'  {t_name} [label={label_html}];')
            sql_statements.append(f"CREATE TABLE {t_name} (\n  " + ",\n  ".join(col_defs) + "\n);")

        data["sql_code"] = "\n\n".join(sql_statements)
        data["graphviz_dot"] = dot_str + "\n".join(dot_nodes) + "\n" + "\n".join(dot_edges) + "\n}"
        data["normalization_steps"] = "**Note:** Normalization steps are not stored in history."
        
        return data
    except Exception as e:
        st.error(f"Error: {e}")
        return None
    finally:
        conn.close()

def get_project_list():
    conn = get_db_connection()
    projects = []
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT ProjectID, ProjectName FROM Projects ORDER BY ProjectID DESC")
            projects = cursor.fetchall()
        finally:
            conn.close()
    return projects