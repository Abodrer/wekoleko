import json
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

# 1. تحميل البيانات من ملف JSON
with open('Training_resources.json', 'r', encoding='utf-8') as file:
    data = json.load(file)

texts = [item["text"] for item in data]

# 2. تحميل DialoGPT
tokenizer = AutoTokenizer.from_pretrained("microsoft/DialoGPT-large")
model = AutoModelForCausalLM.from_pretrained("microsoft/DialoGPT-large")

# 3. تحسين النموذج باستخدام البيانات
def generate_response(input_text):
    # ترميز النص المدخل
    input_ids = tokenizer.encode(input_text + tokenizer.eos_token, return_tensors='pt')

    # توليد الاستجابة
    response_ids = model.generate(input_ids, max_length=1000, pad_token_id=tokenizer.eos_token_id)

    # فك تشفير الاستجابة
    response = tokenizer.decode(response_ids[:, input_ids.shape[-1]:][0], skip_special_tokens=True)
    return response

# 4. اختبار النموذج
for text in texts:
    response = generate_response(text)
    print(f"Input: {text}")
    print(f"Response: {response}\n")