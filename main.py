import json
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, Trainer, TrainingArguments

# 1. تحميل البيانات من ملف JSON
with open('Training_resources.json', 'r', encoding='utf-8') as file:
    data = json.load(file)

texts = [item["text"] for item in data]

# 2. تحميل DialoGPT-large
tokenizer = AutoTokenizer.from_pretrained("microsoft/DialoGPT-large")
model = AutoModelForCausalLM.from_pretrained("microsoft/DialoGPT-large")

# 3. إعداد بيانات التدريب
# تحويل النصوص إلى تنسيق مناسب
train_encodings = tokenizer(texts, truncation=True, padding=True, return_tensors='pt')

# 4. إعداد بيانات التدريب
class ChatDataset(torch.utils.data.Dataset):
    def __init__(self, encodings):
        self.encodings = encodings

    def __getitem__(self, idx):
        return {key: val[idx] for key, val in self.encodings.items()}

    def __len__(self):
        return len(self.encodings['input_ids'])

train_dataset = ChatDataset(train_encodings)

# 5. إعداد إعدادات التدريب
training_args = TrainingArguments(
    output_dir='./results',          # حيث سيتم تخزين النموذج المدرب
    num_train_epochs=5,              # عدد مرات التكرار
    per_device_train_batch_size=4,   # حجم الدفعة
    gradient_accumulation_steps=8,    # تكديس التدرجات
    learning_rate=5e-5,               # معدل التعلم
    logging_dir='./logs',            # مكان حفظ السجلات
    logging_steps=10,
    save_steps=500,
    evaluation_strategy="steps",
    save_total_limit=2,
)

# 6. إنشاء المدرب
trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=train_dataset,
)

# 7. بدء عملية التدريب
trainer.train()

# 8. حفظ النموذج المدرب
trainer.save_model('./trained_model')

# 9. اختبار النموذج
def generate_response(input_text):
    input_ids = tokenizer.encode(input_text + tokenizer.eos_token, return_tensors='pt')
    response_ids = model.generate(
        input_ids,
        max_length=1000,
        pad_token_id=tokenizer.eos_token_id,
        temperature=0.7,
        top_k=50,
        top_p=0.95,
        num_return_sequences=1
    )
    response = tokenizer.decode(response_ids[:, input_ids.shape[-1]:][0], skip_special_tokens=True)
    return response

# 10. اختبار النموذج
for text in texts:
    response = generate_response(text)
    print(f"Input: {text}")
    print(f"Response: {response}\n")