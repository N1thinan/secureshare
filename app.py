import os
import uuid
import io
from flask import Flask, request, send_file, render_template_string

# สร้างแอปพลิเคชัน Flask
app = Flask(__name__)

# สร้างโฟลเดอร์สำหรับเก็บไฟล์ชั่วคราว (ถ้ายังไม่มี)
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ฐานข้อมูลจำลอง (เก็บไว้ในหน่วยความจำชั่วคราวเพื่อความง่ายตอน Demo)
# รูปแบบ: { 'รหัส_uuid': {'filename': 'ชื่อไฟล์เดิม.txt', 'filepath': 'uploads/รหัส_ชื่อไฟล์.txt'} }
DATABASE = {}

# ==========================================
# ส่วนของหน้าเว็บ (Frontend UI)
# ใช้ Tailwind CSS เพื่อความสวยงามแบบสาย Dark/Cyber
# ==========================================
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="th">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SecureShare | Zero Persistence</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <style>
        body { background-color: #0f172a; color: #f8fafc; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
    </style>
</head>
<body class="min-h-screen flex items-center justify-center p-4">

    <div class="max-w-md w-full bg-slate-800 rounded-xl shadow-2xl overflow-hidden border border-slate-700">
        <div class="bg-slate-900 p-6 border-b border-slate-700 text-center">
            <h1 class="text-3xl font-bold text-green-500"><i class="fas fa-shield-halved mr-2"></i>SecureShare</h1>
            <p class="text-slate-400 text-sm mt-2">อัปโหลดไฟล์ลับ โหลดได้ครั้งเดียว ลบทิ้งทันที</p>
        </div>

        <div class="p-6">
            {% if share_url %}
            <!-- ส่วนแสดงลิงก์เมื่ออัปโหลดเสร็จ -->
            <div class="bg-green-900/30 border border-green-500/50 rounded-lg p-4 text-center mb-6">
                <p class="text-green-400 font-semibold mb-2"><i class="fas fa-check-circle mr-2"></i>ไฟล์พร้อมส่งแล้ว!</p>
                <input type="text" id="shareLink" value="{{ share_url }}" readonly 
                       class="w-full bg-slate-900 border border-slate-600 rounded p-2 text-slate-300 text-sm mb-3">
                <button onclick="copyToClipboard()" class="w-full bg-green-600 hover:bg-green-500 text-white font-bold py-2 px-4 rounded transition">
                    <i class="fas fa-copy mr-2"></i>คัดลอกลิงก์
                </button>
                <p class="text-xs text-red-400 mt-3"><i class="fas fa-exclamation-triangle mr-1"></i>คำเตือน: ลิงก์นี้จะใช้ได้แค่ 1 ครั้งเท่านั้น</p>
            </div>
            <div class="text-center">
                <a href="/" class="text-slate-400 hover:text-white text-sm underline">อัปโหลดไฟล์อื่น</a>
            </div>

            <script>
                function copyToClipboard() {
                    var copyText = document.getElementById("shareLink");
                    copyText.select();
                    document.execCommand("copy");
                    alert("คัดลอกลิงก์แล้ว! ส่งให้เพื่อนได้เลย");
                }
            </script>

            {% else %}
            <!-- ส่วนฟอร์มอัปโหลดไฟล์ -->
            <form action="/" method="POST" enctype="multipart/form-data" class="space-y-4">
                <div class="border-2 border-dashed border-slate-600 rounded-lg p-8 text-center hover:border-green-500 transition cursor-pointer relative">
                    <input type="file" name="file" required class="absolute inset-0 w-full h-full opacity-0 cursor-pointer" onchange="document.getElementById('fileName').innerText = this.files[0].name">
                    <i class="fas fa-cloud-upload-alt text-4xl text-slate-400 mb-3"></i>
                    <p class="text-slate-300 font-medium">คลิกหรือลากไฟล์มาวางที่นี่</p>
                    <p id="fileName" class="text-green-400 text-sm mt-2 font-mono"></p>
                </div>
                <button type="submit" class="w-full bg-blue-600 hover:bg-blue-500 text-white font-bold py-3 px-4 rounded-lg transition flex justify-center items-center">
                    <i class="fas fa-lock mr-2"></i> เข้ารหัสและสร้างลิงก์
                </button>
            </form>
            {% endif %}
        </div>
    </div>

</body>
</html>
"""

# ==========================================
# 1. Route สำหรับหน้าแรก (อัปโหลดไฟล์)
# ==========================================
@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        # ตรวจสอบว่ามีการส่งไฟล์มาหรือไม่
        if 'file' not in request.files:
            return "ไม่พบไฟล์", 400
        
        file = request.files['file']
        if file.filename == '':
            return "ไม่ได้เลือกไฟล์", 400

        # สร้าง UUID แบบสุ่มเพื่อใช้เป็น URL ที่เดาไม่ได้
        file_id = str(uuid.uuid4())
        
        # ตั้งชื่อไฟล์ใหม่เพื่อป้องกันชื่อซ้ำ และบันทึกลงเครื่อง
        safe_filename = f"{file_id}_{file.filename}"
        filepath = os.path.join(UPLOAD_FOLDER, safe_filename)
        file.save(filepath)

        # เก็บข้อมูลลง Database จำลอง
        DATABASE[file_id] = {
            'filename': file.filename, # ชื่อไฟล์ดั้งเดิมที่ผู้ใช้จะเห็นตอนโหลด
            'filepath': filepath       # ที่อยู่ไฟล์จริงๆ ในเครื่อง
        }

        # สร้าง URL สำหรับส่งให้เพื่อน
        share_url = request.host_url + 'download/' + file_id
        
        return render_template_string(HTML_TEMPLATE, share_url=share_url)

    # ถ้าเป็น GET Request ให้แสดงหน้าฟอร์มปกติ
    return render_template_string(HTML_TEMPLATE, share_url=None)

# ==========================================
# 2. Route สำหรับดาวน์โหลด (หัวใจหลักของโปรเจกต์)
# ==========================================
@app.route('/download/<file_id>')
def download(file_id):
    # 1. ตรวจสอบว่ามีไฟล์นี้ในระบบหรือไม่
    if file_id not in DATABASE:
        return """
        <h1 style='color:red; text-align:center; margin-top:50px; font-family:sans-serif;'>
            404 Not Found<br>ไฟล์นี้ถูกทำลายไปแล้ว หรือไม่มีอยู่จริง
        </h1>
        """, 404

    # 2. ดึงข้อมูลไฟล์
    file_info = DATABASE[file_id]
    filepath = file_info['filepath']
    original_filename = file_info['filename']

    # 3. โหลดไฟล์เข้าสู่หน่วยความจำ (RAM) ของ Server
    # สาเหตุที่ต้องทำแบบนี้เพราะถ้าเราสั่งส่งไฟล์(send_file) แล้วสั่งลบทันที มันจะ Error เพราะไฟล์กำลังถูกอ่านอยู่
    return_data = io.BytesIO()
    with open(filepath, 'rb') as fo:
        return_data.write(fo.read())
    return_data.seek(0)

    # 4. **ทำลายไฟล์ทันที! (Self-Destruct)**
    os.remove(filepath) # ลบไฟล์ออกจาก Harddisk ของ Server
    del DATABASE[file_id] # ลบข้อมูลออกจากฐานข้อมูล

    # 5. ส่งไฟล์ที่อยู่ในหน่วยความจำให้ผู้ใช้ดาวน์โหลด
    return send_file(
        return_data, 
        as_attachment=True, 
        download_name=original_filename
    )

if __name__ == '__main__':
    # สั่งรัน Server (เข้าดูได้ที่ http://localhost:5000)
    print("🚀 ระบบ SecureShare เปิดทำงานแล้วที่ http://localhost:5000")
    app.run(debug=True, port=5000)