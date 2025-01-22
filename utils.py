import random

def ai_greetings():
    greetings = ["Hello", "Hi there", "Greetings", "Good Day", "Nice to meet you"]
    greeting = random.choice(greetings)
    return greeting

def task2_greeting():
    task2_resps = ["Hi there! Sure, I'd be happy to help with your SQL queries. What do you have in mind?",
                 "Hello! Let’s tackle your SQL questions together. How can I assist you today?",
                 "Hi there! SQL can get tricky sometimes, but I'm here to help. What's the task at hand?"]
    task2_resp = random.choice(task2_resps)
    return task2_resp