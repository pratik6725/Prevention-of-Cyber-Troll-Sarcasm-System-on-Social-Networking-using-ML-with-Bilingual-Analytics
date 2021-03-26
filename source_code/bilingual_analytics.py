# pip install google_trans_new
from google_trans_new import google_translator
import ktrain
from ktrain import text
import os
from keras.models import load_model


def detect_hinglish(text):
    detector = google_translator()
    result = detector.detect(text)
    if(result[1] == 'hindi'):
        return True
    else:
        return False


def hinglish_sentiment(sentence):
    return "Positive"


# def hinglish_sentiment(sentences):
#     p = ktrain.load_predictor("/models/hinglish/")
#     ans = p.predict(sentences)
#     return ans


# if __name__ == '__main__':
#     InputSentence = ["Vo banda mast hai", "The hotel is a bakwas place. bilkul mat jana chutiya",
#                      "pagal hai kya ", "vo banda mast hai "]
#     ans = hinglish_sentiment(InputSentence)
#     print(ans)
