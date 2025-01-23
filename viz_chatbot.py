from openai import OpenAI
import sqlparse
import os
import matplotlib.pyplot as plt
import pandas as pd
import sqlite3
import streamlit as st

# Mock data setup
def create_mock_database():
    # Create an in-memory SQLite database
    conn = sqlite3.connect(':memory:')
    cursor = conn.cursor()

    # Create a mock table
    cursor.execute('''
        CREATE TABLE sales (
            id INTEGER PRIMARY KEY,
            product TEXT,
            quantity INTEGER,
            price REAL,
            sale_date TEXT
        )
    ''')

    # Insert mock data
    mock_data = [
        (1, 'Laptop', 5, 1200.50, '2023-10-01'),
        (2, 'Smartphone', 10, 800.25, '2023-10-02'),
        (3, 'Tablelaptop', 7, 600.75, '2023-10-03'),
        (4, 'Monitor', 3, 300.00, '2023-10-04'),
        (5, 'Keyboard', 15, 50.00, '2023-10-05'),
    ]
    cursor.executemany('INSERT INTO sales VALUES (?, ?, ?, ?, ?)', mock_data)
    conn.commit()

    return conn

# OpenAI setup
api_key = os.getenv("DEEPSEEK_API_KEY")
client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")

system_prompt_tmp = """
You are a SQL expert. Your task is to generate valid SQL queries based on user requests. You will also validate the request against the following database schema:

Database Schema:
{schema}

Rules:
1. If the user request is unclear or cannot be translated into a valid SQL query, ask clarifying questions.
2. Only generate SQL queries if the request makes sense for the database schema.
3. Format the SQL query properly.
4. Once a valid SQL query is generated, explain the query in simple terms to a non-technical user.
5. If the user requests a plot, generate a SQL query that retrieves data suitable for plotting.

Examples:
- User: "Retrieve all data from the sales table."
  SQL: SELECT * FROM sales;
  Explanation: This query retrieves all the information stored in the sales table.

- User: "Show the total quantity sold for each product."
  SQL: SELECT product, SUM(quantity) AS total_quantity FROM sales GROUP BY product;
  Explanation: This query retrieves the total quantity sold for each product.
"""

# Mock schema
mock_schema = """
Table: sales
- id: INTEGER (Primary Key)
- product: TEXT
- quantity: INTEGER
- price: REAL
- sale_date: TEXT
"""

system_prompt = {"role": "system", "content": system_prompt_tmp.format(schema=mock_schema)}
conversation = [system_prompt]

def generate_sql(user_input):
    message = {"role": "user", "content": user_input}
    conversation.append(message)
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=conversation,
        stream=False
    )
    conversation.append(response.choices[0].message)
    return response.choices[0].message.content

def clean_sql_query(sql_query):
    """
    Remove Markdown syntax (e.g., ```sql and ```) from the SQL query.
    """
    if sql_query.startswith("```sql"):
        sql_query = sql_query[len("```sql"):]
    if sql_query.endswith("```"):
        sql_query = sql_query[:-len("```")]
    return sql_query.strip()

def extract_sql_and_explanation(response):
    """
    Extract the SQL query and explanation from the response.
    """
    if "SQL:" in response and "Explanation:" in response:
        sql_query = response.split("SQL:")[1].split("Explanation:")[0].strip()
        explanation = response.split("Explanation:")[1].strip()
        return sql_query, explanation
    return None, response  # If no SQL query is found, return the entire response as explanation

def validate_sql(sql_query):
    try:
        parsed = sqlparse.parse(sql_query)
        if not parsed:
            return False
        return True
    except Exception as e:
        st.error(f"SQL Validation Error: {e}")
        return False

def execute_sql_and_plot(sql_query, conn, plot_data):
    try:
        # Clean the SQL query to remove Markdown syntax
        sql_query = clean_sql_query(sql_query)

        # Execute the SQL query and fetch data into a DataFrame
        df = pd.read_sql_query(sql_query, conn)

        # Check if the data is suitable for plotting and if the toggle is on
        if plot_data and not df.empty:
            st.write("Plotting data...")  # Debugging statement
            if len(df.columns) == 2:  # Suitable for bar/line plots
                # Create a much smaller figure
                fig, ax = plt.subplots(figsize=(3.5, 3))  # Smaller size (width, height)
                df.plot(kind='bar', x=df.columns[0], y=df.columns[1], legend=False, ax=ax)
                ax.set_xlabel(df.columns[0], fontsize=8)  # Smaller font size for x-label
                ax.set_ylabel(df.columns[1], fontsize=8)  # Smaller font size for y-label
                ax.set_title(f"{df.columns[1]} by {df.columns[0]}", fontsize=10)  # Smaller font size for title
                ax.tick_params(axis='both', labelsize=8)  # Smaller tick labels
                plt.tight_layout()  # Ensure tight layout to avoid overlapping elements
                st.pyplot(fig, use_container_width=False)  # Do not use container width
            else:
                st.write("Data is not suitable for a simple 2D plot. Ensure the query returns exactly 2 columns.")
        elif plot_data and df.empty:
            st.write("No data to plot.")
    except Exception as e:
        st.error(f"Error executing SQL query: {e}")
        st.write("Generated SQL Query:", sql_query)  # Display the problematic query for debugging

def main():

    st.set_page_config(
    initial_sidebar_state = "expanded",
    page_title = "AppName",
    layout = "wide"
    )

    with st.sidebar:
        st.title("AppName")
        # st.image("")
        
        # st.subheader("Select which LLM you want to use:")
        options = ["GPT-4o-Mini", "LLaMa 3.2B (Still in Development)"]
        selected_model_name = st.sidebar.selectbox(
            "Select which LLM to use",
            options,
            key = "selected_model"
        )
        mapping = {
            "GPT-4o-Mini":"gpt-4o-mini",
            "LLaMa 3.2B (Still in Development)": "llama3"
        }
        selected_model = mapping.get(selected_model_name)
        if selected_model == "llama3":
            selected_model = "gpt-4o-mini"
    
    col1, col2, col3 = st.columns([1, 5, 1])
    col3.button("New Chat")

    # Greeting message
    st.write("Hello, I'm J ! How can I help you ?")

    # User input
    user_input = st.text_input("Enter your request:")

    # Toggle switch for plotting
    plot_data = st.checkbox("Plot the data")

    # Create a mock database
    conn = create_mock_database()

    if user_input:
        response = generate_sql(user_input)
        sql_query, explanation = extract_sql_and_explanation(response)

        if sql_query:
            if validate_sql(sql_query):
                st.write("Generated SQL Query:", sql_query)
                st.write("Explanation:", explanation)

                # Execute the SQL query and plot if the toggle is on
                execute_sql_and_plot(sql_query, conn, plot_data)
            else:
                st.write("Generated SQL Query is invalid.")
        else:
            st.write("Clarifying Question:", explanation)

    # Close the database connection
    conn.close()

if __name__ == "__main__":
    main()