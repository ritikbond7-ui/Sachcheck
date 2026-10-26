from flask import Flask, request, render_template, send_from_directory
import os
import io
import base64
import json
import wave
import numpy as np
from PIL import Image, ImageChops
import piexif

app = Flask(__name__)
UPLOAD_FOLDER = "/tmp/uploads" if os.environ.get("VERCEL") else "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def ela_analysis(path, quality=95):
    original = Image.open(path).convert("RGB")
    buffer = io.BytesIO()
    original.save(buffer, "JPEG", quality=quality)
    buffer.seek(0)
    compressed = Image.open(buffer)
    diff_img = ImageChops.difference(original, compressed)
    # Stats ke liye RAW fark (bina x10 saturation ke) — text ke kinare
    # saturated map par galat "hotspot" ban jate the.
    raw = np.array(diff_img.convert("L"), dtype=float)
    diff = diff_img.convert("L").point(lambda x: min(255, x * 10))
    h, w = raw.shape
    bh, bw = h // 10, w // 10
    if bh == 0 or bw == 0:
        return {"median": 0.0, "hot_blocks": 0, "max_z": 0.0, "anomaly": 0.0}, diff
    blocks = []
    for i in range(10):
        for j in range(10):
            block = raw[i*bh:(i+1)*bh, j*bw:(j+1)*bw]
            blocks.append(block.mean())
    blocks = np.array(blocks)
    median = float(np.median(blocks))
    mad = float(np.median(np.abs(blocks - median)))
    sigma = 1.4826 * mad
    if sigma < 1e-6:
        sigma = max(median * 0.25, 1e-6)
    zscores = (blocks - median) / sigma
    hot = int(np.sum(zscores > 6.0))
    max_z = float(np.max(zscores)) if zscores.size else 0.0
    safe_median = median if median != 0 else 1e-6
    anomaly = float(np.max(np.abs(blocks - median)) / safe_median)
    stats = {"median": median, "hot_blocks": hot, "max_z": max_z, "anomaly": anomaly}
    return stats, diff

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
            flags.append((f"EDITING SOFTWARE KA NISHAN: '{software}' mila", 20))
        if not meta:
            # Scan, screenshot aur WhatsApp photo me EXIF hota hi nahi —
            # ye aam baat hai, ispar number nahi katna chahiye.
            flags.append(("METADATA NAHI MILA: scan/WhatsApp photo me ye aam hai — ispar number nahi kata", 0))
    except Exception:
        flags.append(("METADATA PADH NAHI PAYE — ispar number nahi kata", 0))
    return flags

def kaagaz_jaanch(path):
    stats, diff = ela_analysis(path)
    flags = metadata_flags(path)
    hot = stats["hot_blocks"]
    max_z = stats["max_z"]
    # Asli forensic fark: BADLA hua hissa aksar CHHOTA aur LOCALIZED hota
    # hai (kuch hi block alag). Text/print ka pattern poori photo me FAILA
    # hota hai — use galti se editing mat samjho (purani galti yahi thi,
    # isiliye asli certificate bhi Suspicious aa jata tha).
    if 1 <= hot <= 10 and max_z > 10:
        flags.append(("ELA HOTSPOT: sirf ek chhote hisse ka compression pattern baaki kagaz se bahut alag hai — wahi hissa badla gaya ho sakta hai", 35))
    elif 1 <= hot <= 10 and max_z > 6:
        flags.append(("ELA SHAK: ek chhote hisse ka pattern thoda alag hai", 15))
    elif hot > 10:
        flags.append(("ELA PATTERN FAILA HUA: poore kagaz me compression ke nishan ghule hue hain — text/print par ye aam baat hai", 5))
    else:
        flags.append(("ELA SAAF: poore kagaz ka pattern ek jaisa hai", 0))
    score = 100
    for _, penalty in flags:
        score -= penalty
    return max(0, score), flags, stats["anomaly"], diff

def band(score):
    if score >= 70:
        return "Bharosa karo — Trustworthy"
    if score >= 50:
        return "Shak hai — Suspicious"
    return "Bharosa mat karo — Not Trustworthy"

def rang(score):
    if score >= 70:
        return "green"
    if score >= 50:
        return "orange"
    return "red"

CHEHRA_MODELS = ["gemini-3-flash-preview", "gemini-3.8-flash", "gemini-3.5-flash-lite"]

def chehra_jaanch(path):
    import time
    import google.generativeai as genai
    key = os.environ.get("GEMINI_API_KEY", "")
    if not key:
        return None, "GEMINI_API_KEY set nahi hai — Chehra Jaanch ke liye key chahiye"
    genai.configure(api_key=key)
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
    # Ek hi model par atke rehna purani galti thi: us model ka free quota
    # khatm hote hi pura Chehra fail ho jata tha. Ab chain hai — ek model
    # quota/busy de to agla apne aap try hota hai, har model 2 baar.
    last_err = ""
    for name in CHEHRA_MODELS:
        for attempt in range(2):
            try:
                model = genai.GenerativeModel(name)
                resp = model.generate_content([prompt, img],
                                              generation_config={"max_output_tokens": 900},
                                              request_options={"timeout": 40})
                txt = resp.text.replace("```json", "").replace("```", "").strip()
                return json.loads(txt), None
            except Exception as e:
                last_err = f"{name}: {type(e).__name__}"
                time.sleep(1.5)
    return None, ("Gemini ke teeno model abhi quota/busy par atke hain — thodi der baad phir try karo "
                  f"(aakhri error: {last_err})")

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
        ela_buffer = io.BytesIO()
        diff.save(ela_buffer, "PNG")
        ela_url = "data:image/png;base64," + base64.b64encode(ela_buffer.getvalue()).decode()
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
            worst = None
            for data, err in results:
                if err:
                    error = err
                    break
                scores.append(data.get("score", 50))
                if worst is None or data.get("score", 50) < worst.get("score", 50):
                    worst = data
            if not error:
                # Ek kharab/blur frame poori video ko na dubaye — score
                # beech wala (median) frame; saboot sabse kamzor frame ke.
                ordered = sorted(scores)
                score = ordered[len(ordered) // 2]
                info.append(f"{len(frames)} frame (poori video se bikhre hue) check kiye — video ka score beech wala (median) frame hai, saboot sabse kamzor frame ke hain")
                reasons = [(flag, "") for flag in worst.get("flags", [])]
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
