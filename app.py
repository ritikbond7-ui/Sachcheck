from flask import Flask, request, render_template, send_from_directory
import os
import io
import json
import wave
import numpy as np
from PIL import Image, ImageChops
import piexif

app = Flask(__name__)
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def ela_analysis(path, quality=95):
    original = Image.open(path).convert("RGB")
    buffer = io.BytesIO()
    original.save(buffer, "JPEG", quality=quality)
    buffer.seek(0)
    compressed = Image.open(buffer)
    diff = ImageChops.difference(original, compressed)
    diff = diff.convert("L").point(lambda x: min(255, x * 10))
    arr = np.array(diff, dtype=float)
    h, w = arr.shape
    bh, bw = h // 10, w // 10
    blocks = []
    for i in range(10):
        for j in range(10):
            block = arr[i*bh:(i+1)*bh, j*bw:(j+1)*bw]
            blocks.append(block.mean())
    blocks = np.array(blocks)
    median = np.median(blocks)
    if median == 0:
        median = 1e-6
    anomaly = float(np.max(np.abs(blocks - median)) / median)
    return anomaly, diff

def metadata_flags(path):
    flags = []
    try:
        exif = piexif.load(path)
        meta = {}
        for ifd in ("0th", "Exif", "GPS"):
            for tag, val in exif.get(ifd, {}).items():
                name = piexif.TAGS.get(ifd, {}).get(tag, {}).get("name", str(tag))
                if isinstance(val, bytes):
                    val = val.decode("utf-8", "ignore")
                meta[name] = str(val)[:80]
        software = meta.get("Software", "")
        if any(s in software for s in ("Photoshop", "GIMP", "Canva", "Picsart", "Snapseed")):
            flags.append((f"EDITING SOFTWARE KA NISHAN: '{software}' mila", 25))
        if not meta:
            flags.append(("METADATA GAYAB: photo me koi camera jaankari nahi mili", 10))
    except Exception:
        flags.append(("METADATA PADH NAHI PAYE", 10))
    return flags

def kaagaz_jaanch(path):
    anomaly, diff = ela_analysis(path)
    flags = metadata_flags(path)
    if anomaly > 0.50:
        flags.append(("ELA HOTSPOT: ek hisse ka pattern baaki photo se bahut alag hai", 40))
    elif anomaly > 0.30:
        flags.append(("ELA SHAK: kuch hisso ka pattern alag hai", 20))
    else:
        flags.append(("ELA SAAF: poori photo ka pattern ek jaisa hai", 0))
    score = 100
    for _, penalty in flags:
        score -= penalty
    return max(0, score), flags, anomaly, diff

def band(score):
    if score >= 80:
        return "Bharosa karo"
    if score >= 50:
        return "Dhyaan do, dusre zariye se confirm karo"
    return "Ruko, paise ya jaankari bilkul mat do"

def rang(score):
    if score >= 80:
        return "green"
    if score >= 50:
        return "orange"
    return "red"

def chehra_jaanch(path):
    import google.generativeai as genai
    key = os.environ.get("GEMINI_API_KEY", "")
    if not key:
        return None, "GEMINI_API_KEY set nahi hai — Chehra Jaanch ke liye key chahiye"
    try:
        genai.configure(api_key=key)
        model = genai.GenerativeModel("gemini-3-flash-preview")
        img = Image.open(path).convert("RGB")
        img.thumbnail((1024, 1024))
        prompt = ("Tum ek photo forensic checker ho. Photo ke in 6 signals ko EK-EK karke jaancho, "
                  "aur HAR signal ke baare me ek alag flag likho — chahe wo signal saaf ho ya shak wala ho, "
                  "khaali mat chhodo: "
                  "1) Skin texture — pores, lines dikh rahe hain ya plastic jaisi smooth hai? "
                  "2) Haath aur ungliyaan — ginati, jod, aakaar sahi hai ya bigde hue? "
                  "3) Kaan aur unke kinare — shape, jod, symmetry sahi hai? "
                  "4) Aankhen aur chashma — reflection, frame ka jod, symmetry sahi hai? "
                  "5) Background — warping, distortion, text ya cheezein bigdi hui hain? "
                  "6) Lighting aur shadow — chehre aur background ki roshni match karti hai? "
                  "YAAD RAKHO: webcam ya phone photo me natural noise, halki blur aur JPEG compression NORMAL hai — "
                  "inhe AI ka nishan mat samajhna. Score sirf tab kam karo jab saaf AI artifact dikhe. "
                  "Score ka scale: koi AI nishan nahi mila to 85-95; halka shak ho to 60-84; "
                  "saaf AI nishan dikhe to 40 se neeche; poori tarah AI-generated lage to 20 se neeche. "
                  "Sirf JSON do: {\"score\": 0-100, \"summary\": \"2 line me detail faisla\", "
                  "\"flags\": [\"Signal ka naam: kya dekha, detail me (zyada se zyada 2 chhoti line) — kam se kam 6 flags, har signal ek\"]}")
        resp = model.generate_content([prompt, img],
                                      generation_config={"max_output_tokens": 900},
                                      request_options={"timeout": 60})
        txt = resp.text.replace("```json", "").replace("```", "").strip()
        return json.loads(txt), None
    except Exception as e:
        return None, f"Gemini check fail hua ({type(e).__name__}) — net ya quota check karo"

def video_frames(path, max_frames=3):
    import cv2
    cap = cv2.VideoCapture(path)
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    frames = []
    if total > 0:
        step = max(1, total // max_frames)
        positions = [k * step for k in range(max_frames)]
    else:
        positions = [0, 30, 60]
    for pos in positions:
        cap.set(cv2.CAP_PROP_POS_FRAMES, pos)
        ok, frame = cap.read()
        if not ok:
            break
        fp = os.path.join(UPLOAD_FOLDER, f"frame_{len(frames)}.jpg")
        cv2.imwrite(fp, frame)
        frames.append(fp)
    cap.release()
    return frames

def awaaz_jaanch(path):
    try:
        w = wave.open(path, "rb")
        frames = w.readframes(w.getnframes())
        sr = w.getframerate()
        audio = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
    except Exception:
        return None, "Abhi sirf WAV file chalegi — MP3 ko WAV me badal ke try karo"
    if len(audio) < sr // 2:
        return None, "Audio bahut chhota hai — kam se kam 2-3 second ki awaaz do"
    win = max(1, int(sr * 0.05))
    n = (len(audio) // win) * win
    energies = np.sqrt(np.mean(audio[:n].reshape(-1, win) ** 2, axis=1))
    variation = float(np.std(energies) / (np.mean(energies) + 1e-9))
    score = 100
    if variation < 0.35:
        flags = [("AWAAZ BAHUT FLAT", "Poori awaaz ek hi zor pe hai — clone/synthetic ka pattern")]
        score -= 35
    elif variation < 0.60:
        flags = [("AWAAZ THODI FLAT", "Awaaz me badlaav kam hai — dhyaan se suno")]
        score -= 15
    else:
        flags = [("AWAAZ NATURAL", "Awaaz ke zor me natural badlaav hai")]
    return {"score": max(0, score), "flags": flags}, None

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/uploads/<path:filename>")
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

@app.route("/check", methods=["POST"])
def check():
    file = request.files["file"]
    kind = request.form["kind"]
    path = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(path)
    score = None
    reasons = []
    info = []
    ela_url = None
    summary = None
    error = None
    kind_label = {"document": "Kaagaz Jaanch", "photo": "Chehra Jaanch",
                  "voice": "Awaaz Jaanch", "video": "Video Jaanch"}.get(kind, kind)
    if kind == "document":
        score, flags, anomaly, diff = kaagaz_jaanch(path)
        base, _ = os.path.splitext(file.filename)
        ela_name = "ela_" + base + ".png"
        diff.save(os.path.join(UPLOAD_FOLDER, ela_name))
        ela_url = "/uploads/" + ela_name
        info.append(f"ELA anomaly: {anomaly:.2f}")
        reasons = [(name, "") for name, _ in flags]
    elif kind == "photo":
        data, err = chehra_jaanch(path)
        if err:
            error = err
        else:
            score = data.get("score", 50)
            summary = data.get("summary")
            reasons = [(flag, "") for flag in data.get("flags", [])]
    elif kind == "video":
        frames = video_frames(path)
        if not frames:
            error = "Video se frame nahi nikaale ja sake — MP4 video try karo"
        else:
            from concurrent.futures import ThreadPoolExecutor
            with ThreadPoolExecutor(max_workers=len(frames)) as pool:
                results = list(pool.map(chehra_jaanch, frames))
            scores = []
            all_flags = []
            for data, err in results:
                if err:
                    error = err
                    break
                scores.append(data.get("score", 50))
                all_flags += data.get("flags", [])
            if not error:
                score = min(scores)
                info.append(f"{len(frames)} frame (poori video se bikhre hue) ek saath check kiye — sabse kamzor frame ka score hi video ka score hai")
                reasons = [(flag, "") for flag in all_flags]
    elif kind == "voice":
        data, err = awaaz_jaanch(path)
        if err:
            error = err
        else:
            score = data["score"]
            reasons = data["flags"]
    return render_template("result.html", score=score, band=band(score) if score is not None else "",
                           rang=rang(score) if score is not None else "red", kind_label=kind_label,
                           filename=file.filename, info=info, reasons=reasons,
                           ela_url=ela_url, summary=summary, error=error)

if __name__ == "__main__":
    app.run(debug=True)
