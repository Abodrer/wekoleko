import numpy as np
import tensorflow as tf
from tensorflow.keras.preprocessing.text import Tokenizer
from tensorflow.keras.preprocessing.sequence import pad_sequences
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Embedding, LSTM, Dense, Bidirectional, Dropout
from tensorflow.keras.callbacks import ReduceLROnPlateau, EarlyStopping
from tensorflow.keras.initializers import Constant

# 1. تحميل البيانات النصية للتدريب
data = open('stories.txt').read().lower().split("\n")

# 2. تجهيز بيانات النصوص
tokenizer = Tokenizer()
tokenizer.fit_on_texts(data)
total_words = len(tokenizer.word_index) + 1

input_sequences = []
for line in data:
    token_list = tokenizer.texts_to_sequences([line])[0]
    for i in range(1, len(token_list)):
        n_gram_sequence = token_list[:i+1]
        input_sequences.append(n_gram_sequence)

max_sequence_len = max([len(x) for x in input_sequences])
input_sequences = pad_sequences(input_sequences, maxlen=max_sequence_len, padding='pre')

X, y = input_sequences[:,:-1], input_sequences[:,-1]
y = tf.keras.utils.to_categorical(y, num_classes=total_words)

# 3. تحميل تمثيلات GloVe
embeddings_index = {}
with open('glove.6B.100d.txt', encoding='utf-8') as f:
    for line in f:
        values = line.split()
        word = values[0]
        coefs = np.asarray(values[1:], dtype='float32')
        embeddings_index[word] = coefs

embedding_dim = 100
embedding_matrix = np.zeros((total_words, embedding_dim))
for word, i in tokenizer.word_index.items():
    embedding_vector = embeddings_index.get(word)
    if embedding_vector is not None:
        embedding_matrix[i] = embedding_vector

# 4. بناء النموذج باستخدام Bidirectional LSTM و Dropout
model = Sequential()
model.add(Embedding(total_words, embedding_dim, embeddings_initializer=Constant(embedding_matrix), input_length=max_sequence_len-1, trainable=False))
model.add(Bidirectional(LSTM(150, return_sequences=True)))
model.add(Dropout(0.2))
model.add(Bidirectional(LSTM(100)))
model.add(Dense(total_words, activation='softmax'))

model.compile(loss='categorical_crossentropy', optimizer='adam', metrics=['accuracy'])

# 5. ضبط معلمات التدريب (التنشيط المبكر وتقليل معدل التعلم)
reduce_lr = ReduceLROnPlateau(monitor='loss', factor=0.2, patience=5, min_lr=0.001)
early_stop = EarlyStopping(monitor='loss', patience=10)

# 6. تدريب النموذج
model.fit(X, y, epochs=100, batch_size=64, callbacks=[reduce_lr, early_stop], verbose=1)

# 7. توليد النصوص باستخدام Sampling
def generate_story(seed_text, next_words, temperature=1.0):
    for _ in range(next_words):
        token_list = tokenizer.texts_to_sequences([seed_text])[0]
        token_list = pad_sequences([token_list], maxlen=max_sequence_len-1, padding='pre')
        predictions = model.predict(token_list, verbose=0)[0]

        # استخدام Sampling بدلاً من اختيار الكلمة الأعلى احتمالية دائماً
        predictions = np.asarray(predictions).astype('float64')
        predictions = np.log(predictions) / temperature
        exp_preds = np.exp(predictions)
        predictions = exp_preds / np.sum(exp_preds)

        probas = np.random.multinomial(1, predictions, 1)
        predicted_word_index = np.argmax(probas)

        output_word = tokenizer.index_word[predicted_word_index]
        seed_text += " " + output_word
    return seed_text

# 8. تجربة إنشاء قصة
print(generate_story("كان هناك يوم مشرق", 50, temperature=1.0))