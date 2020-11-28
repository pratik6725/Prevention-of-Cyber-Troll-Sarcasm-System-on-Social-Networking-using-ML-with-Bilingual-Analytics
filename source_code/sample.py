import pandas as pd
import sarcasm_model


sentence = ["Coworkers At Bathroom Sink Locked In Tense Standoff Over Who Going To Wash Hands Longer",
            "Spiking U.S. coronavirus cases could force rationing decisions similar to those made in Italy, China.",
            "I love how 2 of the most disrespectful girls on the team are captains ! Just Love It :)",
            "Thirsty Thursday's make going to a Friday morning class so much better",
            "If I ever need a brain transplant I ' d choose yours because I ' d want a brain that had never been used",
            "No really . I can sleep quite well while I'm upset",
            "That 100 degree heat index made that one of my most enjoyable runs to date",
            "Yay for an 8am class on Friday",
            "So happy to just find out uoit decided to reschedule all my lectures and tutorials for me to night classes at the exact same times",
            "Bronchitis , eat infection and a fever . Makes for a great start to my labor day weekend",
            "I love how sick this heat makes me 😅",
            "I love Summit runs ? #not",
            "Can't wait to do a whole lot of nothing today ",
            "So glad i'm losing sleep over someone I barely know ... "
            ]
mod = sarcasm_model.run_model(sentence)
classes = mod.classify()

print(classes)
