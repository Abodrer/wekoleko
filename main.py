import json
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, BertTokenizer, BertModel

# 1. تحميل البيانات من ملف JSON
with open('Training_resources.json', 'r', encoding='utf-8') as file:
    data = json.load(file)

texts = [item["text"] for item in data if "text" in item]

# 2. تحميل DialoGPT وBERT
tokenizer_dialo = AutoTokenizer.from_pretrained("microsoft/DialoGPT-large")
model_dialo = AutoModelForCausalLM.from_pretrained("microsoft/DialoGPT-large")

tokenizer_bert = BertTokenizer.from_pretrained("bert-base-uncased")
model_bert = BertModel.from_pretrained("bert-base-uncased")

# 3. تحسين النموذج باستخدام البيانات
def generate_response(input_text):
    try:
        # ترميز النص المدخل باستخدام BERT
        inputs_bert = tokenizer_bert(input_text, return_tensors='pt', truncation=True, padding=True)
        outputs_bert = model_bert(**inputs_bert)

        # الحصول على تمثيل BERT للنص المدخل
        bert_embeddings = outputs_bert.last_hidden_state.mean(dim=1)  # استخدام المتوسط لاستخراج الميزات

        # تأكد من تحويل التنسورات إلى LongTensor
        bert_embedding_flattened = bert_embeddings.detach().numpy().flatten()  # جعل التمثيل مسطحاً
        bert_embedding_tensor = torch.tensor(bert_embedding_flattened).unsqueeze(0).long()  # تحويل إلى LongTensor

        # دمج تمثيل BERT مع النص المدخل لـ DialoGPT
        input_ids = tokenizer_dialo.encode(input_text + tokenizer_dialo.eos_token, return_tensors='pt')
        
        # دمج التمثيل BERT مع input_ids
        input_ids_with_bert = torch.cat((input_ids, bert_embedding_tensor), dim=1)

        # توليد الاستجابة
        response_ids = model_dialo.generate(input_ids_with_bert, max_length=150, pad_token_id=tokenizer_dialo.eos_token_id, temperature=0.7, top_k=50, top_p=0.95)

        # فك تشفير الاستجابة
        response = tokenizer_dialo.decode(response_ids[:, input_ids.shape[-1]:][0], skip_special_tokens=True)
        return response
    except Exception as e:
        return f"Error: {e}"

# 4. اختبار النموذج
for text in texts:
    response = generate_response(text)
    print(f"Input: {text}")
    print(f"Response: {response}\n")