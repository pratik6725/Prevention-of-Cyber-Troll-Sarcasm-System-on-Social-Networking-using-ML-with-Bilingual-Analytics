import nltk
from nltk.corpus import stopwords
import re
# nltk.download('stopwords')


def get_embedding_index():
    MAX_SEQUENCE_LENGTH = 50
    MAX_NUM_WORDS = 10000
    EMBEDDING_DIM = 100
    VALIDATION_SPLIT = 0.2

    embeddings_index = {}

    with open("glove.6B.100d.txt", encoding='utf-8') as f:
        for line in f:
            values = line.split()
            word = values[0]
            coefs = np.asarray(values[1:], dtype='float32')
            embeddings_index[word] = coefs
    print('Found %s word vectors.' % len(embeddings_index))

    return embeddings_index


def text_cleaning(tweet):
    tweet = tweet.lower()
    # Remove urls
    tweet = re.sub('http://\S+|https://\S+', '', tweet)
    # removing special characters and numbers
    tweet = re.sub("[^a-z\s\']", "", tweet)
    # removing stopwords
    tweet = " ".join(word for word in tweet.split()
                     if word not in stopwords.words("english"))
    return tweet
