# ============================================================
# XORE FILE HOST
# Short File Links • Upload • Download • Stats
# ============================================================

from flask import Flask, request, render_template_string, redirect
import requests
import secrets
import string
import json
import os
import re
import time
import html
from urllib.parse import quote

app = Flask(__name__)

# ============================================================
# SETTINGS
# ============================================================

SECRET_ACCESS_CODE = "XOREYT123400028"

RECAPTCHA_SITE_KEY = "6LeIxAcTAAAAAJcZVRqyHh71UMIEGNQ_MXjiZKhI"
RECAPTCHA_SECRET_KEY = "6LeIxAcTAAAAAGG-vFI1TnRWxMZNFuojJ4WifJWe"

MAX_FILE_SIZE = 50 * 1024 * 1024

DATA_FILE = "/tmp/xore_files.json"

# ============================================================
# DATA
# ============================================================

def load_data():
    if not os.path.exists(DATA_FILE):
        return {}

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_data(data):
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
    except Exception:
        pass


FILES = load_data()


# ============================================================
# HELPERS
# ============================================================

def generate_code(length=7):
    chars = string.ascii_letters + string.digits

    while True:
        code = "".join(secrets.choice(chars) for _ in range(length))

        if code not in FILES:
            return code


def clean_filename(filename):
    filename = os.path.basename(filename or "").strip()

    # إزالة الأحرف الخطرة
    filename = re.sub(r'[<>:"/\\|?*\x00-\x1F]', "", filename)

    # منع المسافات الزائدة
    filename = re.sub(r"\s+", " ", filename)

    if not filename:
        filename = "file"

    # الحد الأقصى
    filename = filename[:100]

    return filename


def safe_filename_for_url(filename):
    filename = clean_filename(filename)

    # نخلي الرابط أجمل
    filename = filename.replace(" ", "-")

    return quote(filename, safe="-_.~")


def verify_recaptcha(token):
    if not token:
        return False

    try:
        response = requests.post(
            "https://www.google.com/recaptcha/api/siteverify",
            data={
                "secret": RECAPTCHA_SECRET_KEY,
                "response": token
            },
            timeout=8
        )

        return response.json().get("success", False)

    except Exception:
        return False


def upload_to_storage(uploaded_file):

    files = {
        "file": (
            uploaded_file.filename,
            uploaded_file.stream,
            uploaded_file.content_type or "application/octet-stream"
        )
    }

    response = requests.post(
        "https://tmpfiles.org/api/v1/upload",
        files=files,
        timeout=30
    )

    if response.status_code != 200:
        raise Exception("Storage upload failed")

    data = response.json()

    if not data.get("data"):
        raise Exception("Invalid storage response")

    raw_url = data["data"].get("url")

    if not raw_url:
        raise Exception("Storage URL missing")

    # تحويله لرابط تحميل مباشر
    direct_url = raw_url.replace(
        "tmpfiles.org/",
        "tmpfiles.org/dl/"
    )

    return direct_url


def get_file(code):
    return FILES.get(code)


def build_file_url(code, filename):
    host = request.host_url.rstrip("/")

    return f"{host}/f/{code}/{safe_filename_for_url(filename)}"


# ============================================================
# HTML
# ============================================================

HTML_LAYOUT = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">

<head>

<meta charset="UTF-8">

<meta name="viewport"
      content="width=device-width, initial-scale=1.0">

<title>{{ title }}</title>

<script src="https://cdn.tailwindcss.com"></script>

<script src="https://www.google.com/recaptcha/api.js"
        async defer></script>

<link rel="preconnect"
      href="https://fonts.googleapis.com">

<link rel="preconnect"
      href="https://fonts.gstatic.com"
      crossorigin>

<link href="https://fonts.googleapis.com/css2?family=Cairo:wght@400;500;600;700;800&display=swap"
      rel="stylesheet">

<style>

* {
    box-sizing: border-box;
}

body {
    font-family: 'Cairo', sans-serif;
}

.glass {
    background: rgba(15, 23, 42, .82);
    backdrop-filter: blur(20px);
    -webkit-backdrop-filter: blur(20px);
}

.glow {
    box-shadow:
        0 0 40px rgba(99, 102, 241, .12),
        0 20px 70px rgba(0, 0, 0, .35);
}

input[type=file]::file-selector-button {
    cursor: pointer;
}

</style>

</head>

<body class="min-h-screen
             bg-gradient-to-br
             from-slate-950
             via-indigo-950
             to-slate-950
             text-white">

<div class="min-h-screen flex items-center justify-center p-4">

<div class="w-full max-w-lg">

{{ content | safe }}

</div>

</div>

</body>
</html>
"""


# ============================================================
# HOME
# ============================================================

@app.route("/", methods=["GET", "POST"])
def home():

    error_msg = ""

    if request.method == "POST":

        access_code = request.form.get(
            "access_code",
            ""
        ).strip()

        custom_name = clean_filename(
            request.form.get(
                "file_name",
                ""
            )
        )

        uploaded_file = request.files.get("file")

        captcha = request.form.get(
            "g-recaptcha-response"
        )

        # -----------------------------
        # Security
        # -----------------------------

        if access_code != SECRET_ACCESS_CODE:

            error_msg = "رمز الحماية غير صحيح."

        elif not verify_recaptcha(captcha):

            error_msg = "يرجى تأكيد أنك لست روبوتاً."

        elif not uploaded_file:

            error_msg = "اختر ملفاً أولاً."

        elif not uploaded_file.filename:

            error_msg = "اسم الملف غير صالح."

        else:

            try:

                # -----------------------------
                # Size check
                # -----------------------------

                uploaded_file.stream.seek(0, os.SEEK_END)

                file_size = uploaded_file.stream.tell()

                uploaded_file.stream.seek(0)

                if file_size > MAX_FILE_SIZE:

                    error_msg = (
                        "حجم الملف أكبر من الحد المسموح "
                        "(50MB)."
                    )

                else:

                    # -----------------------------
                    # Upload
                    # -----------------------------

                    direct_url = upload_to_storage(
                        uploaded_file
                    )

                    # -----------------------------
                    # Short ID
                    # -----------------------------

                    code = generate_code(7)

                    # -----------------------------
                    # Save metadata
                    # -----------------------------

                    FILES[code] = {

                        "name": custom_name,

                        "url": direct_url,

                        "size": file_size,

                        "created": int(time.time()),

                        "downloads": 0

                    }

                    save_data(FILES)

                    # -----------------------------
                    # Short link
                    # -----------------------------

                    share_link = build_file_url(
                        code,
                        custom_name
                    )

                    escaped_link = html.escape(
                        share_link,
                        quote=True
                    )

                    content = f"""

                    <div class="glass glow
                                rounded-3xl
                                border border-emerald-500/20
                                p-7">

                        <div class="w-20 h-20
                                    mx-auto mb-5
                                    rounded-3xl
                                    bg-emerald-500/10
                                    border border-emerald-500/20
                                    flex items-center justify-center
                                    text-4xl">

                            ✓

                        </div>

                        <h1 class="text-2xl font-extrabold mb-2">
                            تم رفع الملف 🎉
                        </h1>

                        <p class="text-slate-400 text-sm mb-6">
                            رابط المشاركة جاهز
                        </p>


                        <div class="rounded-2xl
                                    bg-slate-950/70
                                    border border-slate-700
                                    p-4
                                    mb-4">

                            <div class="text-xs
                                        text-slate-500
                                        mb-2">

                                اسم الملف

                            </div>

                            <div class="font-bold
                                        text-indigo-300
                                        break-all">

                                {html.escape(custom_name)}

                            </div>

                        </div>


                        <div class="rounded-2xl
                                    bg-slate-950/70
                                    border border-indigo-500/20
                                    p-3
                                    mb-4">

                            <input

                                id="linkInput"

                                value="{escaped_link}"

                                readonly

                                class="w-full
                                       bg-transparent
                                       text-indigo-200
                                       text-sm
                                       text-center
                                       outline-none">

                        </div>


                        <button

                            onclick="copyLink()"

                            class="w-full
                                   bg-indigo-600
                                   hover:bg-indigo-500
                                   py-4
                                   rounded-2xl
                                   font-bold
                                   transition">

                            📋 نسخ الرابط

                        </button>


                        <a

                            href="{escaped_link}"

                            target="_blank"

                            class="block
                                   text-center
                                   mt-3
                                   py-3
                                   rounded-2xl
                                   bg-slate-800
                                   hover:bg-slate-700
                                   transition
                                   text-sm">

                            🔗 فتح الرابط

                        </a>


                        <a

                            href="/"

                            class="block
                                   text-center
                                   mt-5
                                   text-xs
                                   text-slate-500
                                   hover:text-white">

                            رفع ملف آخر

                        </a>

                    </div>


                    <script>

                    function copyLink() {{

                        const input =
                            document.getElementById("linkInput");

                        navigator.clipboard.writeText(
                            input.value
                        );

                        alert("تم نسخ الرابط ✓");

                    }}

                    </script>

                    """

                    return render_template_string(
                        HTML_LAYOUT,
                        content=content,
                        title="تم الرفع"
                    )

            except Exception:

                error_msg = (
                    "حدث خطأ أثناء رفع الملف، "
                    "حاول مرة أخرى."
                )

    # ========================================================
    # Error
    # ========================================================

    error_html = ""

    if error_msg:

        error_html = f"""

        <div class="mb-5
                    p-4
                    rounded-2xl
                    bg-red-500/10
                    border border-red-500/20
                    text-red-300
                    text-sm">

            ❌ {html.escape(error_msg)}

        </div>

        """

    # ========================================================
    # Upload page
    # ========================================================

    content = f"""

    <div class="glass glow
                rounded-3xl
                border border-slate-700/60
                p-7">

        <div class="w-20 h-20
                    mx-auto mb-5
                    rounded-3xl
                    bg-indigo-500/10
                    border border-indigo-500/20
                    flex items-center justify-center
                    text-4xl">

            📁

        </div>


        <h1 class="text-2xl
                   font-extrabold
                   mb-2">

            XORE File Host

        </h1>


        <p class="text-slate-400
                  text-sm
                  mb-7">

            ارفع ملفك واحصل على رابط مشاركة قصير

        </p>


        {error_html}


        <form

            method="POST"

            enctype="multipart/form-data"

            class="space-y-5">


            <div class="text-right">

                <label class="block
                              text-xs
                              font-bold
                              text-slate-300
                              mb-2">

                    🔐 رمز الدخول

                </label>

                <input

                    type="password"

                    name="access_code"

                    required

                    placeholder="أدخل رمز الحماية"

                    class="w-full
                           rounded-2xl
                           bg-slate-950/70
                           border border-slate-700
                           px-4 py-3.5
                           outline-none
                           focus:border-indigo-500
                           transition">

            </div>


            <div class="text-right">

                <label class="block
                              text-xs
                              font-bold
                              text-slate-300
                              mb-2">

                    🏷️ اسم الملف في الرابط

                </label>

                <input

                    type="text"

                    name="file_name"

                    required

                    placeholder="مثال: MyScript.lua"

                    class="w-full
                           rounded-2xl
                           bg-slate-950/70
                           border border-slate-700
                           px-4 py-3.5
                           outline-none
                           focus:border-indigo-500
                           transition">

                <p class="text-[11px]
                          text-slate-500
                          mt-2">

                    سيظهر الاسم في نهاية الرابط.

                </p>

            </div>


            <div class="text-right">

                <label class="block
                              text-xs
                              font-bold
                              text-slate-300
                              mb-2">

                    📤 اختر الملف

                </label>

                <input

                    type="file"

                    name="file"

                    required

                    class="w-full
                           rounded-2xl
                           bg-slate-950/70
                           border border-slate-700
                           p-2
                           text-xs
                           text-slate-400">

            </div>


            <div class="flex justify-center
                        overflow-hidden
                        rounded-xl">

                <div

                    class="g-recaptcha"

                    data-sitekey="{RECAPTCHA_SITE_KEY}"

                    data-theme="dark">

                </div>

            </div>


            <button

                type="submit"

                class="w-full
                       bg-indigo-600
                       hover:bg-indigo-500
                       py-4
                       rounded-2xl
                       font-bold
                       transition
                       shadow-lg
                       shadow-indigo-600/20">

                🚀 رفع وإنشاء رابط قصير

            </button>

        </form>


        <div class="mt-6
                    pt-5
                    border-t
                    border-slate-800
                    text-[11px]
                    text-slate-500">

            🔒 الحد الأقصى للملف: 50MB

        </div>

    </div>

    """

    return render_template_string(
        HTML_LAYOUT,
        content=content,
        title="XORE File Host"
    )


# ============================================================
# SHORT FILE LINK
# ============================================================

@app.route("/f/<code>/<path:filename>")
def file_page(code, filename):

    item = get_file(code)

    if not item:

        content = """

        <div class="glass
                    rounded-3xl
                    border border-red-500/20
                    p-8
                    text-center">

            <div class="text-5xl mb-5">
                🔍
            </div>

            <h1 class="text-2xl font-bold mb-2">
                الملف غير موجود
            </h1>

            <p class="text-slate-400 text-sm">
                الرابط غير صالح أو انتهت صلاحيته.
            </p>

            <a href="/"
               class="block mt-6
                      bg-indigo-600
                      rounded-2xl
                      py-3
                      font-bold">

                العودة للرئيسية

            </a>

        </div>

        """

        return render_template_string(
            HTML_LAYOUT,
            content=content,
            title="الملف غير موجود"
        ), 404


    name = item["name"]

    size_mb = item["size"] / 1024 / 1024

    downloads = item.get(
        "downloads",
        0
    )

    content = f"""

    <div class="glass glow
                rounded-3xl
                border border-indigo-500/20
                p-7">

        <div class="w-24 h-24
                    mx-auto mb-6
                    rounded-3xl
                    bg-indigo-500/10
                    border border-indigo-500/20
                    flex items-center justify-center
                    text-5xl">

            📄

        </div>


        <div class="text-xs
                    text-indigo-400
                    font-bold
                    mb-2">

            FILE

        </div>


        <h1 class="text-2xl
                   font-extrabold
                   break-all
                   mb-3">

            {html.escape(name)}

        </h1>


        <p class="text-slate-400
                  text-sm
                  mb-7">

            الملف جاهز للتحميل

        </p>


        <div class="grid grid-cols-2 gap-3 mb-6">

            <div class="rounded-2xl
                        bg-slate-950/60
                        border border-slate-800
                        p-4">

                <div class="text-xs
                            text-slate-500">

                    الحجم

                </div>

                <div class="font-bold mt-1">

                    {size_mb:.2f} MB

                </div>

            </div>


            <div class="rounded-2xl
                        bg-slate-950/60
                        border border-slate-800
                        p-4">

                <div class="text-xs
                            text-slate-500">

                    التحميلات

                </div>

                <div class="font-bold mt-1">

                    {downloads}

                </div>

            </div>

        </div>


        <a

            href="/download/{code}"

            class="w-full
                   bg-emerald-600
                   hover:bg-emerald-500
                   py-4
                   rounded-2xl
                   font-bold
                   flex items-center
                   justify-center
                   transition">

            ⬇️ تحميل الملف

        </a>


        <div class="mt-6
                    text-[11px]
                    text-slate-500">

            🔒 رابط مشاركة قصير

        </div>

    </div>

    """

    return render_template_string(
        HTML_LAYOUT,
        content=content,
        title=name
    )


# ============================================================
# REAL DOWNLOAD
# ============================================================

@app.route("/download/<code>")
def real_download(code):

    item = get_file(code)

    if not item:
        return "File not found", 404

    # زيادة عدد التحميلات
    item["downloads"] = item.get(
        "downloads",
        0
    ) + 1

    save_data(FILES)

    return redirect(
        item["url"],
        code=302
    )


# ============================================================
# HEALTH CHECK
# ============================================================

@app.route("/health")
def health():

    return {

        "status": "ok",

        "service": "XORE File Host",

        "files": len(FILES)

    }


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=int(
            os.environ.get(
                "PORT",
                5000
            )
        ),
        debug=False
    )
