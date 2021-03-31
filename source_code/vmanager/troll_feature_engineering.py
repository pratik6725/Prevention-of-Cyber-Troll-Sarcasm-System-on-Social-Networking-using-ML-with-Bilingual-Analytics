import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
import string
import pandas as pd


def preprocessing(comments):
    tokenized_single_posts = [nltk.tokenize.word_tokenize(i) for i in comments]

    leng = []
    for i in range(len(tokenized_single_posts)):
        length = len(tokenized_single_posts[i])
        leng.append(length)

    stp_removed = []
    for i in range(len(tokenized_single_posts)):
        stp = [word for word in tokenized_single_posts[i] if word not in (
            stopwords.words('english')+list(string.punctuation))]
        stp_removed.append(stp)

    words_lemma = []
    lemma = nltk.WordNetLemmatizer()
    for i in range(len(stp_removed)):
        words = [lemma.lemmatize(word) for word in stp_removed[i]]
        words_lemma.append(words)

    words_noNum = []
    for i in range(len(words_lemma)):
        words = [word for word in words_lemma[i] if word.isdigit() == False]
        words_noNum.append(words)

    words_nonSingle = []
    for i in range(len(words_noNum)):
        words = [word for word in words_noNum[i] if len(word) > 1]
        words_nonSingle.append(words)

    words_alpha = []
    for i in range(len(words_nonSingle)):
        words = [word for word in words_nonSingle[i] if word.isalpha()]
        words_alpha.append(words)

    words_count = [len(i) for i in words_alpha]

    noun_freq = []
    verb_freq = []
    adjective_freq = []
    adverb_freq = []
    for i in range(len(words_alpha)):
        word_pos_tag = nltk.pos_tag(words_alpha[i])
        count_noun = 0
        count_verb = 0
        count_adjective = 0
        count_adverb = 0
        for j in range(len(word_pos_tag)):
            if word_pos_tag[j][1] == "NN":
                count_noun += 1
            if word_pos_tag[j][1] == 'VB':
                count_verb += 1
            if word_pos_tag[j][1] == 'JJ':
                count_adjective += 1
            if word_pos_tag[j][1] == 'RB':
                count_adverb += 1
        noun_freq.append(count_noun/(len(words_alpha[i]) + 1))
        verb_freq.append(count_verb/(len(words_alpha[i])+1))
        adjective_freq.append(count_adjective/(len(words_alpha[i])+1))
        adverb_freq.append(count_adverb/(len(words_alpha[i])+1))
    return words_count, noun_freq, verb_freq, adjective_freq, adverb_freq


def prepare_data(comments):

    words_count, noun_freq, verb_freq, adjective_freq, adverb_freq = preprocessing(
        comments)

    df = pd.DataFrame(list(zip(comments, words_count, noun_freq, verb_freq, adjective_freq, adverb_freq)),
                      columns=['tweet', 'words_count', 'noun_freq', 'verb_freq', 'adjective_freq', 'adverb_freq'])

    return df
