import json
import tensorflow as tf
from transformers import AutoModelForCausalLM, AutoTokenizer, TFTrainer, TFTrainingArguments

# إعداد TPU
resolver = tf.distribute.cluster_resolver.TPUClusterResolver()
tf.config.experimental_connect_to_cluster(resolver)
tf.tpu.experimental.initialize_tpu_system(resolver)

# إعداد استراتيجية توزيع TPU
strategy = tf.distribute.TPUStrategy(resolver)

# تحميل البيانات من ملف JSON
with open('Training_resources.json', 'r', encoding='utf-8') as file:
    data = json.load(file)

texts = [item["text"] for item in data]

# تحميل DialoGPT-large
tokenizer = AutoTokenizer.from_pretrained("microsoft/DialoGPT-large")

# تعيين pad_token إلى eos_token
tokenizer.pad_token = tokenizer.eos_token

# نموذج التدريب
with strategy.scope():
    model = AutoModelForCausalLM.from_pretrained("microsoft/DialoGPT-large")

    # إعداد بيانات التدريب
    train_encodings = tokenizer(texts, truncation=True, padding=True, return_tensors='tf')

    # إعداد بيانات التدريب
    class ChatDataset(tf.data.Dataset):
        def __init__(self, encodings):
            self.encodings = encodings

        def __getitem__(self, idx):
            return {key: val[idx] for key, val in self.encodings.items()}

        def __len__(self):
            return len(self.encodings['input_ids'])

    train_dataset = ChatDataset(train_encodings)

    # إعداد إعدادات التدريب
    training_args = TFTrainingArguments(
        output_dir='./results',
        num_train_epochs=5,
        per_device_train_batch_size=4,
        logging_dir='./logs',
        logging_steps=10,
        save_steps=500,
        evaluation_strategy="steps",
        save_total_limit=2,
    )

    # إنشاء المدرب
    trainer = TFTrainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
    )

    # بدء عملية التدريب
    trainer.train()

    # حفظ النموذج المدرب
    trainer.save_model('./trained_model')

# اختبار النموذج
def generate_response(input_text):
    input_ids = tokenizer.encode(input_text + tokenizer.eos_token, return_tensors='tf')
    response_ids = model.generate(
        input_ids,
        max_length=1000,
        pad_token_id=tokenizer.eos_token_id,
        temperature=0.7,
        top_k=50,
        top_p=0.95,
        num_return_sequences=1
    )
    response = tokenizer.decode(response_ids.numpy()[0], skip_special_tokens=True)
    return response

# اختبار النموذج
for text in texts:
    response = generate_response(text)
    print(f"Input: {text}")
    print(f"Response: {response}\n")