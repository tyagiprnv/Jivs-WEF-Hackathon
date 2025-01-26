import random
import re
import sqlglot

def ai_greetings():
    greetings = ["Hello", "Hi there", "Greetings", "Good Day", "Nice to meet you"]
    greeting = random.choice(greetings)
    return greeting

def is_sql_statement(sql_text):
  try:
    parsed = sqlglot.parse_one(sql_text)
    return True
  except Exception:
    return False

custom_css = """
<style>
/* General Background */
body {
    background-color: #F1F3F4;
}

/* Title Styling */
h1 {
    color: #1A73E8;
}

/* Button Styling */
.css-1emrehy.edgvbvh3 {
    background-color: #1A73E8;
    color: #FFFFFF;
}
.css-1emrehy.edgvbvh3:hover {
    background-color: #1669C1;
    color: #FFFFFF;
}

/* Input Box Styling */
.css-1p0ddsc {
    background-color: #FFFFFF;
    color: #202124;
}

/* Chat Messages */
.user-message {
    background-color: #34A853;
    color: #FFFFFF;
    padding: 10px;
    border-radius: 10px;
    margin-bottom: 10px;
}

.assistant-message {
    background-color: #FFFFFF;
    color: #202124;
    padding: 10px;
    border-radius: 10px;
    margin-bottom: 10px;
    border: 1px solid #DADCE0;
}
</style>
"""