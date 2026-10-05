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
# ============================================================
# XORE LINK HOST
# ============================================================
app = Flask(__name__)
# ============================================================
# SETTINGS
# ============================================================
SECRET_ACCESS_CODE = "XOREYT123400028"
# ضع مفاتيح reCAPTCHA الخاصة بك هنا
RECAPTCHA_SITE_KEY = "YOUR_RECAPTCHA_SITE_KEY"
RECAPTCHA_SECRET_KEY = "YOUR_RECAPTCHA_SECRET_KEY"
MAX_FILE_SIZE = 50 * 1024 * 1024
DATA_FILE = "/tmp/xore_links.json"
# ============================================================
# DATABASE
# ============================================================
def load_data():
    if not os.path.exists(DATA_FILE):
        return {}
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}
def save_data():
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(
                LINKS,
                f,
                ensure_ascii=False,
                indent=2
            )
    except Exception:
        pass
LINKS = load_data()
# ============================================================
# HELPERS
# ============================================================
def generate_code(length=7):
    chars = string.ascii_letters + string.digits
    while True:
        code = "".join(
            secrets.choice(chars)
            for _ in range(length)
        )
        if code not in LINKS:
            return code
def clean_name(name):
    name = os.path.basename(
        name or ""
    ).strip()
    name = re.sub(
        r'[<>:"/\\|?*\x00-\x1F]',
        "",
        name
    )
    name = re.sub(
        r"\s+",
        " ",
        name
    )
    if not name:
        name = "XORE"
    return name[:100]
def url_name(name):
    name = clean_name(name)
    name = name.replace(
        " ",
        "-"
    )
    return quote(
        name,
        safe="-_.~"
    )
def short_url(code, name):
    return (
        request.host_url.rstrip("/")
        + "/l/"
        + code
        + "/"
        + url_name(name)
    )
def verify_recaptcha(token):
    # إذا لم يتم وضع مفاتيح حقيقية
    # نتجاوز التحقق أثناء التطوير.
    if (
        not RECAPTCHA_SECRET_KEY
        or
        RECAPTCHA_SECRET_KEY.startswith(
            "YOUR_"
        )
    ):
        return True
    if not token:
        return False
    try:
        r = requests.post(
            "https://www.google.com/recaptcha/api/siteverify",
            data={
                "secret":
                    RECAPTCHA_SECRET_KEY,
                "response":
                    token
            },
            timeout=8
        )
        return r.json().get(
            "success",
            False
        )
    except Exception:
        return False
def valid_target(url):
    url = url.strip()
    allowed = (
        url.startswith("https://")
        or
        url.startswith("http://")
        or
        url.startswith("itms-services://")
    )
    return allowed
def upload_file(file):
    files = {
        "file": (
            file.filename,
            file.stream,
            file.content_type
            or
            "application/octet-stream"
        )
    }
    r = requests.post(
        "https://tmpfiles.org/api/v1/upload",
        files=files,
        timeout=30
    )
    if r.status_code != 200:
        raise Exception(
            "Upload failed"
        )
    data = r.json()
    raw_url = (
        data
        .get("data", {})
        .get("url")
    )
    if not raw_url:
        raise Exception(
            "No URL returned"
        )
    return raw_url.replace(
        "tmpfiles.org/",
        "tmpfiles.org/dl/"
    )
# ============================================================
# DESIGN
# ============================================================
LAYOUT = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport"
      content="width=device-width, initial-scale=1.0">
<title>{{ title }}</title>
<script src="https://cdn.tailwindcss.com"></script>
{% if recaptcha %}
<script
src="https://www.google.com/recaptcha/api.js"
async
defer>
</script>
{% endif %}
<link rel="preconnect"
      href="https://fonts.googleapis.com">
<link rel="preconnect"
      href="https://fonts.gstatic.com"
      crossorigin>
<link
href="https://fonts.googleapis.com/css2?family=Cairo:wght@400;500;600;700;800;900&display=swap"
rel="stylesheet">
<style>
* {
    box-sizing: border-box;
}
body {
    font-family: Cairo, sans-serif;
}
.glass {
    background:
        rgba(15,23,42,.76);
    backdrop-filter:
        blur(22px);
    -webkit-backdrop-filter:
        blur(22px);
}
.glow {
    box-shadow:
        0 20px 80px
        rgba(0,0,0,.35);
}
.input {
    width: 100%;
    background:
        rgba(2,6,23,.72);
    border:
        1px solid
        rgba(100,116,139,.35);
    border-radius:
        17px;
    padding:
        14px 16px;
    color:
        white;
    outline:
        none;
    transition:
        .2s;
}
.input:focus {
    border-color:
        rgb(99,102,241);
    box-shadow:
        0 0 0 3px
        rgba(99,102,241,.10);
}
.card {
    border:
        1px solid
        rgba(100,116,139,.22);
    background:
        rgba(2,6,23,.45);
}
</style>
</head>
<body
class="
min-h-screen
bg-slate-950
text-white
overflow-x-hidden
">
<div
class="
fixed
inset-0
pointer-events-none
overflow-hidden
">
<div
class="
absolute
w-96
h-96
bg-indigo-600/10
rounded-full
blur-3xl
-top-32
-right-32
">
</div>
<div
class="
absolute
w-96
h-96
bg-purple-600/10
rounded-full
blur-3xl
-bottom-32
-left-32
">
</div>
</div>
<div
class="
relative
min-h-screen
flex
items-center
justify-center
p-4
">
<div
class="
w-full
max-w-xl
">
{{ content | safe }}
</div>
</div>
</body>
</html>
"""
# ============================================================
# HOME
# ============================================================
@app.route(
    "/",
    methods=["GET", "POST"]
)
def home():
    error = ""
    if request.method == "POST":
        access = request.form.get(
            "access_code",
            ""
        ).strip()
        if access != SECRET_ACCESS_CODE:
            error = "رمز الحماية غير صحيح."
        else:
            # ================================================
            # FILE UPLOAD
            # ================================================
            if request.form.get(
                "action"
            ) == "file":
                uploaded = request.files.get(
                    "file"
                )
                name = clean_name(
                    request.form.get(
                        "file_name",
                        ""
                    )
                )
                captcha = request.form.get(
                    "g-recaptcha-response"
                )
                if not uploaded:
                    error = "اختر ملفاً."
                elif not verify_recaptcha(
                    captcha
                ):
                    error = (
                        "يرجى إكمال التحقق."
                    )
                else:
                    try:
                        uploaded.stream.seek(
                            0,
                            os.SEEK_END
                        )
                        size = (
                            uploaded.stream.tell()
                        )
                        uploaded.stream.seek(0)
                        if size > MAX_FILE_SIZE:
                            error = (
                                "الملف أكبر من 50MB."
                            )
                        else:
                            file_url = upload_file(
                                uploaded
                            )
                            code = generate_code()
                            LINKS[code] = {
                                "name":
                                    name,
                                "url":
                                    file_url,
                                "type":
                                    "file",
                                "size":
                                    size,
                                "created":
                                    int(
                                        time.time()
                                    ),
                                "views":
                                    0
                            }
                            save_data()
                            link = short_url(
                                code,
                                name
                            )
                            return success_page(
                                link,
                                name,
                                "تم رفع الملف"
                            )
                    except Exception:
                        error = (
                            "تعذر رفع الملف."
                        )
            # ================================================
            # SHORT LINK
            # ================================================
            elif request.form.get(
                "action"
            ) == "link":
                name = clean_name(
                    request.form.get(
                        "link_name",
                        ""
                    )
                )
                target = request.form.get(
                    "target_url",
                    ""
                ).strip()
                if not valid_target(
                    target
                ):
                    error = (
                        "الرابط غير مدعوم. "
                        "استخدم http أو https "
                        "أو itms-services."
                    )
                else:
                    code = generate_code()
                    LINKS[code] = {
                        "name":
                            name,
                        "url":
                            target,
                        "type":
                            "link",
                        "size":
                            0,
                        "created":
                            int(
                                time.time()
                            ),
                        "views":
                            0
                    }
                    save_data()
                    link = short_url(
                        code,
                        name
                    )
                    return success_page(
                        link,
                        name,
                        "تم إنشاء الرابط"
                    )
    # ========================================================
    # ERROR
    # ========================================================
    error_box = ""
    if error:
        error_box = f"""
        <div
        class="
        mb-5
        p-4
        rounded-2xl
        bg-red-500/10
        border
        border-red-500/20
        text-red-300
        text-sm
        ">
            ❌ {html.escape(error)}
        </div>
        """
    # ========================================================
    # HOME UI
    # ========================================================
    content = f"""
    <div
    class="
    glass
    glow
    rounded-[30px]
    border
    border-slate-700/50
    p-6
    sm:p-8
    "
    >
        <div
        class="
        w-20
        h-20
        mx-auto
        mb-5
        rounded-3xl
        bg-gradient-to-br
        from-indigo-500/20
        to-purple-500/10
        border
        border-indigo-500/20
        flex
        items-center
        justify-center
        text-4xl
        "
        >
            🔗
        </div>
        <div class="text-center">
            <h1
            class="
            text-3xl
            font-black
            "
            >
                XORE LINK
            </h1>
            <p
            class="
            text-slate-400
            text-sm
            mt-2
            mb-7
            "
            >
                مركز رفع الملفات وإنشاء الروابط القصيرة
            </p>
        </div>
        {error_box}
        <!-- =============================================
             CREATE SHORT LINK
        ============================================== -->
        <div
        class="
        card
        rounded-3xl
        p-5
        mb-5
        "
        >
            <div class="flex items-center gap-3 mb-5">
                <div
                class="
                w-11
                h-11
                rounded-2xl
                bg-indigo-500/10
                flex
                items-center
                justify-center
                text-xl
                "
                >
                    🔗
                </div>
                <div>
                    <h2
                    class="
                    font-bold
                    "
                    >
                        إنشاء رابط قصير
                    </h2>
                    <p
                    class="
                    text-xs
                    text-slate-500
                    "
                    >
                        يدعم روابط itms-services
                    </p>
                </div>
            </div>
            <form
            method="POST"
            class="space-y-4"
            >
                <input
                    type="hidden"
                    name="action"
                    value="link"
                >
                <input
                    class="input"
                    type="password"
                    name="access_code"
                    placeholder="🔐 رمز الحماية"
                    required
                >
                <input
                    class="input"
                    type="text"
                    name="link_name"
                    placeholder="🏷️ اسم الرابط — مثال: XORE"
                    maxlength="100"
                    required
                >
                <textarea
                    class="input"
                    name="target_url"
                    rows="4"
                    dir="ltr"
                    placeholder="itms-services://?action=download-manifest&url=https://example.com/manifest.plist"
                    required
                ></textarea>
                <button
                type="submit"
                class="
                w-full
                py-4
                rounded-2xl
                bg-indigo-600
                hover:bg-indigo-500
                font-bold
                transition
                shadow-lg
                shadow-indigo-600/20
                "
                >
                    ⚡ إنشاء الرابط القصير
                </button>
            </form>
        </div>
        <!-- =============================================
             FILE UPLOAD
        ============================================== -->
        <div
        class="
        card
        rounded-3xl
        p-5
        "
        >
            <div class="flex items-center gap-3 mb-5">
                <div
                class="
                w-11
                h-11
                rounded-2xl
                bg-emerald-500/10
                flex
                items-center
                justify-center
                text-xl
                "
                >
                    📁
                </div>
                <div>
                    <h2 class="font-bold">
                        رفع ملف
                    </h2>
                    <p class="text-xs text-slate-500">
                        الحد الأقصى 50MB
                    </p>
                </div>
            </div>
            <form
            method="POST"
            enctype="multipart/form-data"
            class="space-y-4"
            >
                <input
                    type="hidden"
                    name="action"
                    value="file"
                >
                <input
                    class="input"
                    type="password"
                    name="access_code"
                    placeholder="🔐 رمز الحماية"
                    required
                >
                <input
                    class="input"
                    type="text"
                    name="file_name"
                    placeholder="🏷️ اسم الملف"
                    maxlength="100"
                    required
                >
                <input
                    class="
                    w-full
                    rounded-2xl
                    bg-slate-950/70
                    border
                    border-slate-700
                    p-3
                    text-sm
                    text-slate-400
                    "
                    type="file"
                    name="file"
                    required
                >
                """
    if not RECAPTCHA_SITE_KEY.startswith(
        "YOUR_"
    ):
        content += f"""
                <div
                class="
                flex
                justify-center
                overflow-hidden
                "
                >
                    <div
                    class="g-recaptcha"
                    data-sitekey="{RECAPTCHA_SITE_KEY}"
                    data-theme="dark"
                    >
                    </div>
                </div>
                """
    content += """
                <button
                type="submit"
                class="
                w-full
                py-4
                rounded-2xl
                bg-emerald-600
                hover:bg-emerald-500
                font-bold
                transition
                shadow-lg
                shadow-emerald-600/20
                "
                >
                    🚀 رفع وإنشاء الرابط
                </button>
            </form>
        </div>
        <!-- FOOTER -->
        <div
        class="
        text-center
        text-[11px]
        text-slate-600
        mt-6
        "
        >
            🔒 XORE LINK HOST
        </div>
    </div>
    """
    return render_template_string(
        LAYOUT,
        content=content,
        title="XORE LINK",
        recaptcha=(
            not RECAPTCHA_SITE_KEY.startswith(
                "YOUR_"
            )
        )
    )
# ============================================================
# SUCCESS
# ============================================================
def success_page(
    link,
    name,
    title
):
    safe_link = html.escape(
        link,
        quote=True
    )
    content = f"""
    <div
    class="
    glass
    glow
    rounded-[30px]
    border
    border-emerald-500/20
    p-7
    text-center
    "
    >
        <div
        class="
        w-24
        h-24
        mx-auto
        mb-6
        rounded-[30px]
        bg-emerald-500/10
        border
        border-emerald-500/20
        flex
        items-center
        justify-center
        text-5xl
        "
        >
            ✓
        </div>
        <div
        class="
        text-emerald-400
        text-sm
        font-bold
        mb-2
        "
        >
            تم بنجاح
        </div>
        <h1
        class="
        text-2xl
        font-black
        mb-2
        "
        >
            {html.escape(title)}
        </h1>
        <p
        class="
        text-slate-400
        text-sm
        mb-7
        break-all
        "
        >
            {html.escape(name)}
        </p>
        <div
        class="
        rounded-2xl
        bg-slate-950/80
        border
        border-indigo-500/20
        p-4
        mb-4
        "
        >
            <div
            class="
            text-[10px]
            text-slate-500
            mb-2
            "
            >
                رابط المشاركة
            </div>
            <input
            id="shortLink"
            value="{safe_link}"
            readonly
            class="
            w-full
            bg-transparent
            text-indigo-300
            text-sm
            text-center
            outline-none
            "
            >
        </div>
        <button
        onclick="copyLink()"
        class="
        w-full
        py-4
        rounded-2xl
        bg-indigo-600
        hover:bg-indigo-500
        font-bold
        transition
        "
        >
            📋 نسخ الرابط
        </button>
        <a
        href="{safe_link}"
        target="_blank"
        class="
        block
        mt-3
        py-3
        rounded-2xl
        bg-slate-800
        hover:bg-slate-700
        text-sm
        "
        >
            🔗 فتح الرابط
        </a>
        <a
        href="/"
        class="
        block
        mt-6
        text-xs
        text-slate-500
        hover:text-white
        "
        >
            ← إنشاء رابط جديد
        </a>
    </div>
    <script>
    function copyLink() {{
        const input =
            document.getElementById(
                "shortLink"
            );
        navigator.clipboard.writeText(
            input.value
        );
        alert(
            "تم نسخ الرابط ✓"
        );
    }}
    </script>
    """
    return render_template_string(
        LAYOUT,
        content=content,
        title=title,
        recaptcha=False
    )
# ============================================================
# SHORT LINK
# ============================================================
@app.route(
    "/l/<code>/<path:name>"
)
def open_link(
    code,
    name
):
    item = LINKS.get(code)
    if not item:
        content = """
        <div
        class="
        glass
        rounded-3xl
        p-8
        text-center
        border
        border-red-500/20
        "
        >
            <div class="text-5xl mb-5">
                🔍
            </div>
            <h1 class="text-2xl font-bold mb-2">
                الرابط غير موجود
            </h1>
            <p class="text-slate-400 text-sm">
                الرابط غير صالح أو غير موجود.
            </p>
            <a
            href="/"
            class="
            block
            mt-6
            bg-indigo-600
            rounded-2xl
            py-3
            font-bold
            "
            >
                الرئيسية
            </a>
        </div>
        """
        return render_template_string(
            LAYOUT,
            content=content,
            title="الرابط غير موجود",
            recaptcha=False
        ), 404
    # زيادة المشاهدات
    item["views"] = (
        item.get(
            "views",
            0
        ) + 1
    )
    save_data()
    # تحويل مباشر
    return redirect(
        item["url"],
        code=302
    )
# ============================================================
# STATS
# ============================================================
@app.route("/stats")
def stats():
    total = len(LINKS)
    files = sum(
        1
        for x in LINKS.values()
        if x.get("type") == "file"
    )
    links = sum(
        1
        for x in LINKS.values()
        if x.get("type") == "link"
    )
    views = sum(
        x.get("views", 0)
        for x in LINKS.values()
    )
    content = f"""
    <div
    class="
    glass
    glow
    rounded-[30px]
    border
    border-slate-700/50
    p-7
    "
    >
        <div class="text-center mb-7">
            <div class="text-4xl mb-3">
                📊
            </div>
            <h1 class="text-2xl font-black">
                إحصائيات XORE
            </h1>
        </div>
        <div
        class="
        grid
        grid-cols-2
        gap-3
        "
        >
            <div class="card rounded-2xl p-5">
                <div class="text-xs text-slate-500">
                    جميع الروابط
                </div>
                <div class="text-2xl font-black mt-2">
                    {total}
                </div>
            </div>
            <div class="card rounded-2xl p-5">
                <div class="text-xs text-slate-500">
                    الملفات
                </div>
                <div class="text-2xl font-black mt-2">
                    {files}
                </div>
            </div>
            <div class="card rounded-2xl p-5">
                <div class="text-xs text-slate-500">
                    الروابط
                </div>
                <div class="text-2xl font-black mt-2">
                    {links}
                </div>
            </div>
            <div class="card rounded-2xl p-5">
                <div class="text-xs text-slate-500">
                    الزيارات
                </div>
                <div class="text-2xl font-black mt-2">
                    {views}
                </div>
            </div>
        </div>
        <a
        href="/"
        class="
        block
        mt-6
        text-center
        py-3
        rounded-2xl
        bg-slate-800
        hover:bg-slate-700
        text-sm
        "
        >
            ← الرئيسية
        </a>
    </div>
    """
    return render_template_string(
        LAYOUT,
        content=content,
        title="الإحصائيات",
        recaptcha=False
    )
# ============================================================
# HEALTH
# ============================================================
@app.route("/health")
def health():
    return {
        "status": "ok",
        "service":
            "XORE LINK",
        "links":
            len(LINKS)
    }
# ============================================================
# START
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
