import pandas as pd
import numpy as np
import string

from itertools import chain
import os
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize

from sklearn.model_selection import train_test_split
from sklearn.metrics import recall_score, accuracy_score
from sklearn.preprocessing import MinMaxScaler

from keras.preprocessing.text import Tokenizer
from keras.preprocessing.sequence import pad_sequences
from keras.utils import to_categorical
from keras.layers import Dense, Input, GlobalMaxPooling1D
from keras.layers import GRU, MaxPooling1D, Embedding
from keras.models import Model
from keras import layers, Input
from keras.callbacks import EarlyStopping, ModelCheckpoint
from keras.models import load_model

from hyperopt import Trials, STATUS_OK, tpe
from hyperas import optim
from hyperas.distributions import choice, uniform

import pickle
from vmanager.troll_feature_engineering import preprocessing, prepare_data
from vmanager.preprocessing import get_embedding_index

nltk.download('punkt')
nltk.download('wordnet')
nltk.download('averaged_perceptron_tagger')


class constant_parameters():
    MAX_SEQUENCE_LENGTH = 50
    MAX_NUM_WORDS = 10000
    EMBEDDING_DIM = 100
    VALIDATION_SPLIT = 0.2
    MAX_NB_WORDS = 10000


class troll_model(constant_parameters):
    def __init__(self, df):
        self.df = df

    def train_model(self):
        df = self.df
        df_preprocessed = prepare_data(df['tweet'].tolist())

        X = df_preprocessed
        y = df['label']

        x_train_val, x_test, y_train_val, y_test = train_test_split(
            X, y, test_size=0.3, random_state=123)
        x_train, x_val, y_train, y_val = train_test_split(x_train_val,
                                                          y_train_val, test_size=0.2, random_state=123)

        train_full = pd.concat([x_train, y_train], axis=1)
        train_full.head()

        # get the frequently occuring words
        tokenizer = Tokenizer(num_words=self.MAX_NB_WORDS)
        tokenizer.fit_on_texts(x_train.tweet)
        train_sequences = tokenizer.texts_to_sequences(x_train.tweet)
        val_sequences = tokenizer.texts_to_sequences(x_val.tweet)
        test_sequences = tokenizer.texts_to_sequences(x_test.tweet)

        # dictionary containing words and their index
        word_index = tokenizer.word_index
        train_data = pad_sequences(
            train_sequences, maxlen=self.MAX_SEQUENCE_LENGTH)
        # get only the top frequent words on train
        val_data = pad_sequences(
            val_sequences, maxlen=self.MAX_SEQUENCE_LENGTH)
        # get only the top frequent words on test
        test_data = pad_sequences(
            test_sequences, maxlen=self.MAX_SEQUENCE_LENGTH)

        scaleable_cols = ['words_count', 'adjective_freq',
                          'noun_freq', 'adverb_freq', 'verb_freq']
        scaler_multicol = MinMaxScaler()
        train_multicol_scaled = scaler_multicol.fit_transform(
            x_train[scaleable_cols])
        val_multicol_scaled = scaler_multicol.fit_transform(
            x_val[scaleable_cols])
        test_multicol_scaled = scaler_multicol.fit_transform(
            x_test[scaleable_cols])

        train_data = np.hstack((train_data, train_multicol_scaled))
        val_data = np.hstack((val_data, val_multicol_scaled))
        test_data = np.hstack((test_data, test_multicol_scaled))

        embeddings_index = get_embedding_index()

        num_words = min(self.MAX_NB_WORDS, len(embeddings_index))
        embedding_matrix = np.zeros((num_words, self.EMBEDDING_DIM))
        for word, i in word_index.items():
            if i >= self.MAX_NB_WORDS:
                continue
            embedding_vector = embeddings_index.get(word)
            if embedding_vector is not None:
                # words not found in embedding index will be all-zeros.
                embedding_matrix[i] = embedding_vector
            posts_input = Input(shape=(None,), dtype='int32', name='all_posts')
        embedded_posts = Embedding(input_dim=self.MAX_NB_WORDS,
                                   input_length=self.MAX_SEQUENCE_LENGTH,
                                   output_dim=self.EMBEDDING_DIM,
                                   weights=[embedding_matrix],
                                   trainable=False)(posts_input)

        x = layers.GRU(128, activation='relu',
                       return_sequences=True)(embedded_posts)
        x = layers.BatchNormalization()(x)
        x = layers.Dropout(0.2)(x)
        x = layers.GRU(64, activation='relu')(x)
        x = layers.Dense(16, activation='relu')(x)
        x = layers.Dropout(0.2)(x)

        label_pred = layers.Dense(8, activation='relu', name='label0')(x)
        label_pred = layers.Dropout(0.5)(label_pred)
        label_pred = layers.Dense(
            1, activation='sigmoid', name='label1')(label_pred)

        combined_model = Model(posts_input, [label_pred])
        combined_model.summary()

        callbacks_list = [EarlyStopping(monitor='val_loss', patience=1, ),
                          ModelCheckpoint(filepath='./models/troll/model_multi-feature.h5', monitor='val_loss',
                                          save_best_only=True,)]
        combined_model.compile(optimizer='rmsprop', loss={
                               'label1': 'binary_crossentropy'}, metrics=['acc'])

        epochs = 16
        batch_size = 32

        hist = combined_model.fit(train_data, {'label1': y_train},
                                  epochs=epochs, batch_size=batch_size,
                                  callbacks=callbacks_list,
                                  validation_data=(val_data, {'label1': y_val})).history

        # Save tokenizer
        with open('./models/troll/tokenizer.pickle', 'wb') as handle:
            pickle.dump(tokenizer, handle, protocol=pickle.HIGHEST_PROTOCOL)


class run_model(constant_parameters):
    def __init__(self, comments):
        self.comments = comments

    def classify(self):
        df = prepare_data(self.comments)
        test_data = df
        # preprocessing
        with open('vmanager\models\\troll\\tokenizer.pickle', 'rb') as handle:
            tokenizer = pickle.load(handle)

        test_sequences = tokenizer.texts_to_sequences(test_data.tweet)

        word_index = tokenizer.word_index
        test_data = pad_sequences(
            test_sequences, maxlen=self.MAX_SEQUENCE_LENGTH)

        scaleable_cols = ['words_count', 'adjective_freq',
                          'noun_freq', 'adverb_freq', 'verb_freq']
        scaler_multicol = MinMaxScaler()

        test_multicol_scaled = scaler_multicol.fit_transform(
            df[scaleable_cols])

        test_data = np.hstack((test_data, test_multicol_scaled))

        model = load_model(
            'vmanager\models\\troll\model_multi-feature.h5')
        pred = model.predict(test_data)

        label_list = list(chain.from_iterable(pred))
        label_predict = [1 if x >= 0.05 else 0 for x in label_list]
        return label_predict
