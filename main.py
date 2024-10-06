import numpy as np
import tensorflow as tf
from tensorflow.keras.preprocessing.text import Tokenizer
from tensorflow.keras.preprocessing.sequence import pad_sequences
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense, Embedding, LSTM

# 1. إعداد البيانات
data = [
    {"text": "Hi there! I'm Lolly, how are you doing today, my friend?"},
    {"text": "I'm feeling great, thank you for asking! How about you, my dear friend?"},
    {"text": "What fun things do you enjoy doing?"},
    {"text": "I absolutely love reading books and watching amazing movies!"},
    {"text": "Do you have any recommendations for a good book I should read?"},
    {"text": "Oh, absolutely! You should read 'One Hundred Years of Solitude' by Gabriel Garcia Marquez. It's a magical journey!"},
    {"text": "That sounds exciting! Thank you so much for the recommendation!"},
    {"text": "How do you feel about documentaries? They’re like a window to the world, right?"},
    {"text": "I love them! They're so full of information. What documentaries spark your interest?"},
    {"text": "I'm a big fan of the film '13th.' It's such a thought-provoking look at race in America!"}
]

texts = [item["text"] for item in data]

# 2. إعداد Tokenizer
tokenizer = Tokenizer()
tokenizer.fit_on_texts(texts)
sequences = tokenizer.texts_to_sequences(texts)

# 3. إعداد البيانات
max_length = max(len(seq) for seq in sequences)
padded_sequences = pad_sequences(sequences, maxlen=max_length, padding='post')

# 4. إعداد البيانات للتدريب
# هنا سنقوم بإنشاء تصنيفات عشوائية لتدريب النموذج
labels = np.random.randint(2, size=len(texts))  # على سبيل المثال، تصنيفات ثنائية

# 5. بناء النموذج
model = Sequential()
model.add(Embedding(input_dim=len(tokenizer.word_index) + 1, output_dim=8, input_length=max_length))
model.add(LSTM(16))
model.add(Dense(1, activation='sigmoid'))  # تصنيف ثنائي

# 6. تجميع النموذج
model.compile(loss='binary_crossentropy', optimizer='adam', metrics=['accuracy'])

# 7. تدريب النموذج
model.fit(padded_sequences, labels, epochs=10)

# 8. استخدام النموذج
new_texts = ["I enjoy hiking and exploring new places."]
new_sequences = tokenizer.texts_to_sequences(new_texts)
new_padded_sequences = pad_sequences(new_sequences, maxlen=max_length, padding='post')
predictions = model.predict(new_padded_sequences)
print(predictions)