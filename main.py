# استيراد المكتبات اللازمة
import logging
import json
from transformers import AutoModelForCausalLM, AutoTokenizer, Trainer, TrainingArguments
import torch
from google.colab import files
from torch.utils.data import Dataset

# إعدادات السجل
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# تحميل النماذج والـ Tokenizer لـ DialoGPT
def load_models():
    # DialoGPT لتحليل السياق
    dialoGPT_tokenizer = AutoTokenizer.from_pretrained("microsoft/DialoGPT-large")
    dialoGPT_model = AutoModelForCausalLM.from_pretrained("microsoft/DialoGPT-large")
    return dialoGPT_tokenizer, dialoGPT_model

dialoGPT_tokenizer, dialoGPT_model = load_models()

# فتح ملف JSON وقراءة البيانات
def load_training_data(json_file):
    with open(json_file, 'r', encoding='utf-8') as file:
        data = json.load(file)
    return [item['text'] for item in data]

# استبدال "data.json" باسم ملف JSON الذي يحتوي على بيانات التدريب
training_data = load_training_data('Training_resourcesresources.json')

# تحضير البيانات باستخدام Dataset مخصص
class ChatDataset(Dataset):
    def __init__(self, texts, tokenizer):
        self.input_ids = []
        self.attention_masks = []
        
        for text in texts:
            encoded = tokenizer(text, return_tensors='pt', padding='max_length', truncation=True, max_length=512)
            self.input_ids.append(encoded['input_ids'][0])
            self.attention_masks.append(encoded['attention_mask'][0])

    def __len__(self):
        return len(self.input_ids)

    def __getitem__(self, idx):
        return {
            'input_ids': self.input_ids[idx],
            'attention_mask': self.attention_masks[idx]
        }

# إنشاء مجموعة البيانات
chat_dataset = ChatDataset(training_data, dialoGPT_tokenizer)

# إعدادات التدريب
training_args = TrainingArguments(
    output_dir='./results',          # حيث سيتم حفظ النتائج
    num_train_epochs=5,              # عدد الحلقات التدريبية
    per_device_train_batch_size=4,   # حجم الدفعة (يمكنك زيادته إذا كان لديك موارد كافية)
    gradient_accumulation_steps=2,    # لتقليل استخدام الذاكرة
    evaluation_strategy="epoch",      # استراتيجية التقييم
    logging_dir='./logs',             # حيث سيتم حفظ سجلات التدريب
    logging_steps=10,
    save_steps=500,                   # حفظ النموذج كل 500 خطوة
    load_best_model_at_end=True,      # تحميل أفضل نموذج في نهاية التدريب
    metric_for_best_model='loss',      # المقياس المستخدم لتحديد أفضل نموذج
)

# إعداد Trainer
trainer = Trainer(
    model=dialoGPT_model,                # النموذج
    args=training_args,                   # إعدادات التدريب
    train_dataset=chat_dataset            # مجموعة بيانات التدريب
)

# بدء التدريب
trainer.train()

# حفظ النموذج
model_filename = 'dialoGPT_model.pth'
torch.save(dialoGPT_model.state_dict(), model_filename)

# تنزيل النموذج
files.download(model_filename)

print("تم حفظ النموذج وتنزيله بنجاح.")
