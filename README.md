# SachCheck — "Ye sach hai... ya banaya gaya hai?"

Ek hi jagah chaar jaanch: Kaagaz (document/photo), Chehra (deepfake photo),
Awaaz (voice clone) aur Video. Har jaanch deti hai Trust Score (0-100),
saboot (ELA map + kaaran) aur Hinglish salah.

## Problem
WhatsApp aur social media par har roz fake documents, morphed photos, cloned
awaaz aur edited video share hote hain — aur aam aadmi ke paas ye jaanchne ka
koi asaan tareeka nahi hota ki file asli hai ya banayi gayi. Ek galat file par
bharosa matlab fraud, galatfehmi ya nuksan. SachCheck isi problem ke liye hai:
ek upload, chaar jaanch, aur saboot ke saath saaf jawab.

## 🔴 Live Demo
**[sachcheck-dht4.vercel.app](https://sachcheck-dht4.vercel.app)** — bina install kiye,
seedha browser me chala ke dekho. (Kaagaz aur Awaaz jaanch turant chalti hai;
Chehra/Video ke liye server par Gemini key chahiye.)

## 🏆 Achievement
**3rd Position — Hacktoberfest '26 Hack Day** (Abhyudaya Club × MLH),
GL Bajaj Institute of Technology and Management, 24 October 2026.
Team DHT — 17 finalist teams ke beech.

![Hacktoberfest '26 Certificate — Ritik Raj](certificate.jpg)

## Chalane ka tareeka
1. pip install -r requirements.txt
2. Apni Gemini API key set karo (PowerShell: $env:GEMINI_API_KEY = "key";
   Linux/macOS: export GEMINI_API_KEY="key")
3. python app.py — phir browser me http://127.0.0.1:5000

## Kaise kaam karta hai
- Kaagaz: ELA (Error Level Analysis) + EXIF metadata jaanch (Pillow, piexif, NumPy)
- Chehra/Video: Google Gemini API se vision jaanch; video me poori
  video se bikhre 3 frame, sabse kamzor frame ka score hi video ka score
- Awaaz: WAV ki energy-variation jaanch (wave + NumPy) — flat awaaz = clone ka shak

## Tech Stack / Dependencies
Flask, Pillow, piexif, NumPy, OpenCV, google-generativeai (Gemini API — Google).
Koi bhi hissa kisi doosre project se copy nahi hai.

## Team DHT
- Ritik Raj (CSIT 2F) — poora project build, pitch aur demo
- Aniket Kumar (CSIT 2B) — team member

## Seemayein aur aage ka plan
- Score ek likelihood hai, pakka saboot nahi — duniya ka koi tool 100% sahi nahi hota
- Awaaz jaanch abhi sirf WAV par; MP3 support aage jodege
- Aage ka plan: WhatsApp par seedha check, aur bade paimaane par testing
