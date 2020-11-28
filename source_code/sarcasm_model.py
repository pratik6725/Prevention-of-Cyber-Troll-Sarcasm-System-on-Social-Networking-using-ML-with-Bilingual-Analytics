import json
import tensorflow as tf
import requests
import numpy as np
from tensorflow.keras.preprocessing.text import Tokenizer
from tensorflow.keras.preprocessing.sequence import pad_sequences
import preprocessing
import pickle


class preprocessing_parameters():
    vocab_size = 10000
    oov_tok = "<oov>"
    max_length = 100
    trunc_type = 'post'
    padding_type = 'post'


class sarcasm_model(preprocessing_parameters):

    def __init__(self, df):
        self.df = df

    def df_to_list(self):
        self.df['clean_tweets'] = self.df['tweets'].apply(
            lambda x: preprocessing.text_cleaning(x))
        sentences = self.df['clean_tweets'].tolist()
        labels = self.df['label'].tolist()
        return sentences, labels

    def train_model(self):
        sentences, labels = self.df_to_list()
        # Splitting the dataset into Train and Test
        training_size = round(len(sentences) * .75)
        training_sentences = sentences[0:training_size]
        testing_sentences = sentences[training_size:]
        training_labels = labels[0:training_size]
        testing_labels = labels[training_size:]
        # Setting tokenizer properties
        vocab_size = self.vocab_size
        oov_tok = self.oov_tok
        # Fit the tokenizer on Training data
        tokenizer = Tokenizer(num_words=vocab_size, oov_token=oov_tok)
        tokenizer.fit_on_texts(training_sentences)
        word_index = tokenizer.word_index
        # Setting the padding properties
        max_length = self.max_length
        trunc_type = self.trunc_type
        padding_type = self.padding_type
        # Creating padded sequences from train and test data
        training_sequences = tokenizer.texts_to_sequences(training_sentences)
        training_padded = pad_sequences(
            training_sequences, maxlen=max_length, padding=padding_type, truncating=trunc_type)
        testing_sequences = tokenizer.texts_to_sequences(testing_sentences)
        testing_padded = pad_sequences(
            testing_sequences, maxlen=max_length, padding=padding_type, truncating=trunc_type)

        # Setting the model parameters
        embedding_dim = 16
        model = tf.keras.Sequential([
            tf.keras.layers.Embedding(
                vocab_size, embedding_dim, input_length=max_length),
            tf.keras.layers.GlobalAveragePooling1D(),
            tf.keras.layers.Dense(24, activation='relu'),
            tf.keras.layers.Dense(1, activation='sigmoid')
        ])
        model.compile(loss='binary_crossentropy',
                      optimizer='adam', metrics=['accuracy'])
        model.summary()

        # Converting the lists to numpy arrays for Tensorflow 2.x
        training_padded = np.array(training_padded)
        training_labels = np.array(training_labels)
        testing_padded = np.array(testing_padded)
        testing_labels = np.array(testing_labels)
        # Training the model
        num_epochs = 30
        history = model.fit(training_padded, training_labels, epochs=num_epochs,
                            validation_data=(testing_padded, testing_labels), verbose=2)

        # Save model
        model.save('./models/sarcasm/model')

        # Save tokenizer
        with open('./models/sarcasm/tokenizer.pickle', 'wb') as handle:
            pickle.dump(tokenizer, handle, protocol=pickle.HIGHEST_PROTOCOL)


class run_model(preprocessing_parameters):
    # all sentences with val > _threshold will be classified as sarcastic
    __threshold = 0.55

    def __init__(self, sentences):
        # sentences is a list of comments
        self.sentences = sentences

    def classify(self):
        with open('./models/sarcasm/tokenizer.pickle', 'rb') as handle:
            tokenizer = pickle.load(handle)
        model = tf.keras.models.load_model('./models/sarcasm/model')

        sequences = tokenizer.texts_to_sequences(self.sentences)
        padded = pad_sequences(sequences, maxlen=self.max_length,
                               padding=self.padding_type, truncating=self.trunc_type)
        probabilities = model.predict(padded)
        classes = [1 if p >= self.__threshold else 0 for p in probabilities]
        return classes
