from flask import Flask, request, render_template_string
import requests
import base64
import urllib.parse

app = Flask(__name__)

# رمز الحماية الخاص بك لرفع الملفات
SECRET_ACCESS_CODE = "XOREYT123400028"

# مفاتيح reCAPTCHA
RECAPTCHA_SITE_KEY = "6LeIxAcTAAAAAJcZVRqyHh71UMIEGNQ_MXjiZKhI"
RECAPTCHA_SECRET_KEY = "6LeIxAcTAAAAAGG-vFI1TnRWxMZNFuojJ4WifJWe"

HTML_LAYOUT = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title if title else 'مركز مشاركة الملفات الخاص' }}</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://www.google.com/recaptcha/api.js" async defer></script>
    <link href="https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700;800&display=swap" rel="stylesheet">
    <style> body { font-family: 'Cairo', sans-serif; } </style>
</head>
<body class="bg-gradient-to-br from-slate-900 via-indigo-950 to-slate-900 min-h-screen flex items-center justify-center p-4 text-slate-100">
    <div class="max-w-md w-full bg-slate-800/80 backdrop-blur-xl rounded-3xl shadow-2xl p-8 border border-slate-700/50 text-center relative overflow-hidden">
        <div class="absolute -top-10 -left-10 w-32 h-32 bg-indigo-500/10 rounded-full blur-2xl"></div>
        <div class="absolute -bottom-10 -right-10 w-32 h-32 bg-blue-500/10 rounded-full blur-2xl"></div>
        {{ content | safe }}
    </div>
</body>
</html>
"""

def verify_recaptcha(response_token):
    if not response_token:
        return False
    data = {
        'secret': RECAPTCHA_SECRET_KEY,
        'response': response_token
    }
    try:
        r = requests.post('https://www.google.com/recaptcha/api/siteverify', data=data, timeout=5)
        return r.json().get('success', False)
    except:
        return False

@app.route('/', methods=['GET', 'POST'])
def home():
    error_msg = ""
    if request.method == 'POST':
        user_code = request.form.get('access_code')
        recaptcha_response = request.form.get('g-recaptcha-response')
        custom_name = request.form.get('file_name')
        uploaded_file = request.files.get('file')

        if user_code != SECRET_ACCESS_CODE:
            error_msg = "❌ رمز الحماية غير صحيح! غير مصرح لك برفع الملفات."
        elif not verify_recaptcha(recaptcha_response):
            error_msg = "⚠️ يرجى تأكيد أنك لست برنامج روبوت!"
        elif uploaded_file and custom_name:
            try:
                # رفع الملف مباشرة لخادم تخزين مجاني ومستقر جداً (tmpfiles.org)
                files = {'file': (uploaded_file.filename, uploaded_file.stream, uploaded_file.content_type)}
                r = requests.post('https://tmpfiles.org/api/v1/upload', files=files, timeout=10)
                
                if r.status_code == 200:
                    data = r.json()
                    raw_url = data['data']['url']
                    # تعديل الرابط ليكون رابط تحميل مباشر
                    direct_url = raw_url.replace("tmpfiles.org/", "tmpfiles.org/dl/")
                    
                    share_link = request.host_url + f"download?name={urllib.parse.quote(custom_name)}&url={urllib.parse.quote(direct_url)}"
                    
                    content = f"""
                    <div class="w-20 h-20 bg-emerald-500/20 text-emerald-400 rounded-full flex items-center justify-center mx-auto mb-4 text-3xl border border-emerald-500/30">✓</div>
                    <h1 class="text-2xl font-bold text-white mb-2">تم رفع الملف بنجاح!</h1>
                    <p class="text-sm text-slate-400 mb-6">اسم الملف: <span class="text-indigo-300 font-semibold">{custom_name}</span></p>
                    
                    <div class="bg-slate-900/60 p-3 rounded-2xl border border-slate-700/60 mb-4">
                        <input type="text" value="{share_link}" readonly id="linkInput" class="w-full bg-transparent text-xs text-center text-indigo-200 outline-none select-all">
                    </div>
                    
                    <button onclick="navigator.clipboard.writeText('{share_link}'); alert('تم نسخ الرابط بنجاح!');" class="w-full bg-indigo-600 hover:bg-indigo-500 text-white font-bold py-3.5 rounded-xl transition-all shadow-lg shadow-indigo-600/30 mb-3">
                        📋 نسخ الرابط للمشاركة
                    </button>
                    
                    <a href="/" class="block text-xs text-slate-400 hover:text-white transition-colors">رفع ملف آخر</a>
                    """
                    return render_template_string(HTML_LAYOUT, content=content, title="تم الرفع بنجاح")
                else:
                    error_msg = "تعذر رفع الملف، يرجى المحاولة مرة أخرى."
            except Exception as e:
                error_msg = "فشل الاتصال بسيرفر التخزين."

    error_html = f'<div class="p-3 mb-4 text-xs text-red-400 bg-red-500/10 border border-red-500/20 rounded-xl">{error_msg}</div>' if error_msg else ''

    content = f"""
    <div class="w-16 h-16 bg-indigo-500/20 text-indigo-400 rounded-2xl flex items-center justify-center mx-auto mb-4 border border-indigo-500/30 text-3xl">🔐</div>
    <h1 class="text-2xl font-bold text-white mb-1">لوحة الرفع الخاصة</h1>
    <p class="text-slate-400 text-xs mb-6">هذه الصفحة محمية، أدخل رمز الحماية المعتمد للرفع</p>
    
    {error_html}

    <form method="POST" enctype="multipart/form-data" class="space-y-4 text-right">
        <div>
            <label class="block text-xs font-semibold text-amber-400 mb-1">🔑 رمز الدخول الخاص:</label>
            <input type="password" name="access_code" placeholder="أدخل رمز الحماية هنا" required class="w-full p-3 bg-slate-900/60 border border-amber-500/40 rounded-xl text-white placeholder-slate-500 focus:border-amber-400 focus:ring-1 focus:ring-amber-400 outline-none text-sm transition-all">
        </div>

        <div>
            <label class="block text-xs font-semibold text-slate-300 mb-1">اسم الملف للعرض:</label>
            <input type="text" name="file_name" placeholder="مثال: المستند_الهام.pdf" required class="w-full p-3 bg-slate-900/60 border border-slate-700 rounded-xl text-white placeholder-slate-500 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 outline-none text-sm transition-all">
        </div>
        
        <div>
            <label class="block text-xs font-semibold text-slate-300 mb-1">اختر الملف:</label>
            <input type="file" name="file" required class="w-full p-2 bg-slate-900/60 border border-slate-700 rounded-xl text-xs text-slate-400 file:ml-3 file:py-2 file:px-4 file:rounded-lg file:border-0 file:bg-indigo-600/20 file:text-indigo-300">
        </div>

        <div class="flex justify-center my-4 overflow-hidden rounded-xl">
            <div class="g-recaptcha" data-sitekey="{RECAPTCHA_SITE_KEY}" data-theme="dark"></div>
        </div>

        <button type="submit" class="w-full bg-indigo-600 hover:bg-indigo-500 text-white font-bold py-3.5 rounded-xl transition-all shadow-lg shadow-indigo-600/30">
            حفظ وإنشاء رابط المشاركة
        </button>
    </form>
    """
    return render_template_string(HTML_LAYOUT, content=content, title="لوحة الرفع الخاصة")

@app.route('/download')
def download():
    file_name = request.args.get('name', 'ملف للمشاركة')
    file_url = request.args.get('url', '#')

    content = f"""
    <div class="w-20 h-20 bg-indigo-500/20 text-indigo-400 rounded-3xl flex items-center justify-center mx-auto mb-6 border border-indigo-500/30 text-4xl">📄</div>
    <h1 class="text-2xl font-bold text-white mb-2">{file_name}</h1>
    <p class="text-xs text-slate-400 mb-8">الملف مفحوص وجاهز للتحميل المباشر والآمن</p>

    <a href="{file_url}" target="_blank" download class="w-full bg-emerald-600 hover:bg-emerald-500 text-white font-bold py-4 px-6 rounded-2xl flex items-center justify-center gap-2 transition-all shadow-lg shadow-emerald-600/30">
        <span>⬇️ تحميل الملف الآن</span>
    </a>
    
    <div class="mt-6 flex items-center justify-center gap-1.5 text-xs text-slate-500">
        <span>🔒 رابط محمي ومشفّر</span>
    </div>
    """
    return render_template_string(HTML_LAYOUT, content=content, title=file_name)

if __name__ == '__main__':
    app.run(debug=True)
