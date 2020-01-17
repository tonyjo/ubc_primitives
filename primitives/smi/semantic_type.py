from d3m import container
from d3m.primitive_interfaces import base, transformer
from d3m.metadata import hyperparams

# Import Config File
from primitives.config_files import config

# Import relevant libraries
import os
import math
import string
import random
import numpy as np
import pandas as pd
import tensorflow as tf

import nltk
from collections import OrderedDict
from scipy.stats import skew, kurtosis

from gensim.models.doc2vec import Doc2Vec, TaggedDocument

from sklearn.metrics import f1_score
from sklearn.preprocessing import LabelEncoder

__all__ = ('SemanticTypeInfer',)

Inputs = container.DataFrame
Outputs = container.DataFrame

class Hyperparams(hyperparams.Hyperparams):
    """
    No hyper-parameters for this primitive.
    """
    pass

class SemanticTypeInfer(transformer.TransformerPrimitiveBase[Inputs, Outputs, Hyperparams]):
    """
    A primitive for detecting the semantic type of inputed column data.
    Currently Supported: 78 Types
    """
    __author__ = 'UBC DARPA D3M Team, Tony Joseph <tonyjos@cs.ubc.ca>'
    metadata = hyperparams.base.PrimitiveMetadata({
        "id": "Semantic-type-infer",
        "version": config.VERSION,
        "name": "UBC semantic type",
        "description": "A primitive which detects semantic type of data",
        "python_path": "d3m.primitives.classification.semantic_type.UBC",
        "primitive_family": "DATA_CLEANING",
        "algorithm_types": ["DATA_MAPPING"],
        "source": {
            "name": config.D3M_PERFORMER_TEAM,
            "contact": config.D3M_CONTACT,
            "uris": [config.REPOSITORY]
        },
        "keywords": ['semantic type inference"', "data type detection"],
        "installation": [config.INSTALLATION],
    })

    def __init__(self, *, hyperparams: Hyperparams) -> None:
        super().__init__(hyperparams=hyperparams)
        self.hyperparams = hyperparams

    def produce(self, *, inputs: Inputs, timeout: float = None, iterations: int = None) -> base.CallResult[Outputs]:
        ### User Variables ###
        nn_id = 'sherlock'
        vec_dim = 400
        n_samples = 1000

        ### Build Features ###
        print('Building Features in progress......')
        df_char = pd.DataFrame()
        df_word = pd.DataFrame()
        df_par  = pd.DataFrame()
        df_stat = pd.DataFrame()

        counter = 0
        for raw_sample in inputs.iterrows():
            print(raw_sample)
            if counter % 1000 == 0:
                print('Completion {}/{}'.format(counter, len(inputs)))

            n_values = len(raw_sample)

            if n_samples > n_values:
                n_samples = n_values

            # Sample n_samples from data column, and convert cell values to string values
            raw_sample = pd.Series(random.choices(raw_sample, k=n_samples)).astype(str)

            df_char = df_char.append(self._extract_bag_of_characters_features(raw_sample), ignore_index=True)
            df_word = df_word.append(self._extract_word_embeddings_features(raw_sample), ignore_index=True)
            df_par  = df_par.append(self._infer_paragraph_embeddings_features(raw_sample), ignore_index=True)
            df_stat = df_stat.append(self._extract_bag_of_words_features(raw_sample), ignore_index=True)

            # Increment the progress counter
            counter += 1

        df_char.fillna(df_char.mean(), inplace=True)
        df_word.fillna(df_word.mean(), inplace=True)
        df_par.fillna(df_par.mean(), inplace=True)
        df_stat.fillna(df_stat.mean(), inplace=True)

        print('Completion {}/{}'.format(len(inputs), len(inputs)))
        print('----------Feature Extraction Complete!-------------')

        ### Load Sherlock model ###
        file = open('./weights/{}_model.json'.format(nn_id), 'r')
        sherlock_file = file.read()
        sherlock = tf.keras.models.model_from_json(sherlock_file)
        file.close()

        # Load weights into new model
        sherlock.load_weights('./weights/{}_weights.h5'.format(nn_id))

        # Compile model
        sherlock.compile(optimizer='adam',
                         loss='categorical_crossentropy',
                         metrics=['categorical_accuracy'])
        print(sherlock.summary())
        print('------Sherlock Model Loaded Successfully!--------')

        ### Run Prediction ###
        y_pred = sherlock.predict(feature_vectors)
        print('Prediction Completed!')
        y_pred_int = np.argmax(y_pred, axis=1)

        encoder = LabelEncoder()
        encoder.classes_ = np.load('./weights/classes_{}.npy'.format(nn_id), allow_pickle=True)
        y_pred = encoder.inverse_transform(y_pred_int)
        print('Completed!')

        ### Convert Output to DataFrame ###
        outputs = pandas.DataFrame((y), generate_metadata=True)

        return base.CallResult(outputs)

    def _extract_word_embeddings_features(self, values: pd.DataFrame):
        """
        :param Data: (pandas series) A single column.
        # Output: Ordered dictionary holding bag of words features
        """
        # Load word vectors
        path = './weights/glove.6B.50d.txt'
        word_vectors_f = open(path, encoding='utf-8')
        print('Word vector loaded from: ', path)

        num_embeddings = 50
        f = OrderedDict()
        embeddings = []


        word_to_embedding = {}

        for w in word_vectors_f:
            term, vector = w.strip().split(' ', 1)
            vector = np.array(vector.split(' '), dtype=float)
            word_to_embedding[term] = vector

        values = values.dropna()

        for v in values:
            v = str(v).lower()

            if v in word_to_embedding:
                embeddings.append(word_to_embedding.get(v))
            else:
                words = v.split(' ')
                embeddings_to_all_words = []

                for w in words:
                    if w in word_to_embedding:
                        embeddings_to_all_words.append(word_to_embedding.get(w))
                if embeddings_to_all_words:
                    mean_of_word_embeddings = np.nanmean(embeddings_to_all_words, axis=0)
                    embeddings.append(mean_of_word_embeddings)

        if len(embeddings) == 0:
            for i in range(num_embeddings): f['word_embedding_avg_{}'.format(i)] = np.nan
            for i in range(num_embeddings): f['word_embedding_std_{}'.format(i)] = np.nan
            for i in range(num_embeddings): f['word_embedding_med_{}'.format(i)] = np.nan
            for i in range(num_embeddings): f['word_embedding_mode_{}'.format(i)] = np.nan

            f['word_embedding_feature'] = 0

            return f

        else:
            mean_embeddings = np.nanmean(embeddings, axis=0)
            med_embeddings = np.nanmedian(embeddings, axis=0)
            std_embeddings = np.nanstd(embeddings, axis=0)
            mode_embeddings = stats.mode(embeddings, axis=0, nan_policy='omit')[0].flatten()

            for i, e in enumerate(mean_embeddings): f['word_embedding_avg_{}'.format(i)] = e
            for i, e in enumerate(std_embeddings): f['word_embedding_std_{}'.format(i)] = e
            for i, e in enumerate(med_embeddings): f['word_embedding_med_{}'.format(i)] = e
            for i, e in enumerate(mode_embeddings): f['word_embedding_mode_{}'.format(i)] = e

            f['word_embedding_feature'] = 1

            return f

    def _infer_paragraph_embeddings_features(self, data:pd.DataFrame):
        """
        :param Data: (pandas series) A single column.
        # Output: Ordered dictionary holding bag of words features
        """
        # Load pretrained paragraph vector model
        path  = './weights/par_vec_trained_400.pkl'
        model = Doc2Vec.load(path)
        print('Pre-trained paragraph vector loaded from: ', path)

        f = pd.DataFrame()

        if len(data) > 1000:
            vec = random.sample(data, 1000)
        else:
            vec = data

        # Infer paragraph vector for data sample
        f = f.append(pd.Series(model.infer_vector(vec, steps=20,
                                                  alpha=0.025)), ignore_index=True)

        col_names = []
        for i, col in enumerate(f):
            col_names.append('par_vec_{}'.format(i))

        f.columns = col_names

        return f

    def _extract_bag_of_characters_features(self, data:pd.DataFrame):
        """
        :param Data: (pandas series) A single column.
        # Output: Ordered dictionary holding bag of character features
        """
        characters_to_check = [ '['+ c + ']' for c in string.printable if c not in ( '\n', '\\', '\v', '\r', '\t', '^' )] + ['[\\\\]', '[\^]']

        f = OrderedDict()

        data_no_null = data.dropna()
        all_value_features = OrderedDict()

        for c in characters_to_check:
            all_value_features['n_{}'.format(c)] = data_no_null.str.count(c)

        for value_feature_name, value_features in all_value_features.items():
            f['{}-agg-any'.format(value_feature_name)] = any(value_features)
            f['{}-agg-all'.format(value_feature_name)] = all(value_features)
            f['{}-agg-mean'.format(value_feature_name)] = np.mean(value_features)
            f['{}-agg-var'.format(value_feature_name)] = np.var(value_features)
            f['{}-agg-min'.format(value_feature_name)] = np.min(value_features)
            f['{}-agg-max'.format(value_feature_name)] = np.max(value_features)
            f['{}-agg-median'.format(value_feature_name)] = np.median(value_features)
            f['{}-agg-sum'.format(value_feature_name)] = np.sum(value_features)
            f['{}-agg-kurtosis'.format(value_feature_name)] = kurtosis(value_features)
            f['{}-agg-skewness'.format(value_feature_name)] = skew(value_features)

        return f

    def _extract_bag_of_words_features(self, data:pd.DataFrame):
        """
        :param Data: (pandas series) A single column.
        # Output: Ordered dictionary holding bag of words features
        """
        f = OrderedDict()
        data = data.dropna()

        n_val = data.size

        if not n_val: return

        # Entropy of column
        freq_dist = nltk.FreqDist(data)
        probs = [freq_dist.freq(l) for l in freq_dist]
        f['col_entropy'] = -sum(p * math.log(p,2) for p in probs)

        # Fraction of cells with unique content
        num_unique = data.nunique()
        f['frac_unique'] = num_unique / n_val

        # Fraction of cells with numeric content -> frac text cells doesn't add information
        num_cells = np.sum(data.str.contains('[0-9]', regex=True))
        text_cells = np.sum(data.str.contains('[a-z]|[A-Z]', regex=True))
        f['frac_numcells']  = num_cells / n_val
        f['frac_textcells'] = text_cells / n_val

        # Average + std number of numeric tokens in cells
        num_reg = '[0-9]'
        f['avg_num_cells'] = np.mean(data.str.count(num_reg))
        f['std_num_cells'] = np.std(data.str.count(num_reg))

        # Average + std number of textual tokens in cells
        text_reg = '[a-z]|[A-Z]'
        f['avg_text_cells'] = np.mean(data.str.count(text_reg))
        f['std_text_cells'] = np.std(data.str.count(text_reg))

        # Average + std number of special characters in each cell
        spec_reg = '[[!@#$%^&*(),.?":{}|<>]]'
        f['avg_spec_cells'] = np.mean(data.str.count(spec_reg))
        f['std_spec_cells'] = np.std(data.str.count(spec_reg))

        # Average number of words in each cell
        space_reg = '[" "]'
        f['avg_word_cells'] = np.mean(data.str.count(space_reg) + 1)
        f['std_word_cells'] = np.std(data.str.count(space_reg) + 1)

        all_value_features = OrderedDict()

        data_no_null = data.dropna()

        f['n_values'] = n_val

        all_value_features['length'] = data_no_null.apply(len)

        for value_feature_name, value_features in all_value_features.items():
            f['{}-agg-any'.format(value_feature_name)] = any(value_features)
            f['{}-agg-all'.format(value_feature_name)] = all(value_features)
            f['{}-agg-mean'.format(value_feature_name)] = np.mean(value_features)
            f['{}-agg-var'.format(value_feature_name)] = np.var(value_features)
            f['{}-agg-min'.format(value_feature_name)] = np.min(value_features)
            f['{}-agg-max'.format(value_feature_name)] = np.max(value_features)
            f['{}-agg-median'.format(value_feature_name)] = np.median(value_features)
            f['{}-agg-sum'.format(value_feature_name)] = np.sum(value_features)
            f['{}-agg-kurtosis'.format(value_feature_name)] = kurtosis(value_features)
            f['{}-agg-skewness'.format(value_feature_name)] = skew(value_features)

        n_none = data.size - data_no_null.size - len([ e for e in data if e == ''])
        f['none-agg-has'] = n_none > 0
        f['none-agg-percent'] = n_none / len(data)
        f['none-agg-num'] = n_none
        f['none-agg-all'] = (n_none == len(data))

        return f
