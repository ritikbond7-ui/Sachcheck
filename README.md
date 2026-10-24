# SachCheck — "Ye sach hai... ya banaya gaya hai?"

Ek hi jagah chaar jaanch: Kaagaz (document/photo), Chehra (deepfake photo),
Awaaz (voice clone) aur Video. Har jaanch deti hai Trust Score (0-100),
saboot (ELA map + kaaran) aur Hinglish salah.

## Chalane ka tareeka
1. pip install -r requirements.txt
2. Apni Gemini API key set karo (PowerShell: $env:GEMINI_API_KEY = "key")
3. python app.py — phir browser me http://127.0.0.1:5000

## Kaise kaam karta hai
- Kaagaz: ELA (Error Level Analysis) + EXIF metadata jaanch (Pillow, piexif, NumPy)
- Chehra/Video: Google Gemini API se vision jaanch; video me poori
  video se bikhre 3 frame, sabse kamzor frame ka score hi video ka score
- Awaaz: WAV ki energy-variation jaanch (wave + NumPy) — flat awaaz = clone ka shak

## Credits / Dependencies
Flask, Pillow, piexif, NumPy, OpenCV, google-generativeai (Gemini API — Google).
Koi bhi hissa kisi doosre project se copy nahi hai.

## Team DHT
- Ritik Raj (CSIT 2F) — Kaagaz Jaanch, project lead, pitch
- Aniket Kumar (CSIT 2B) — Chehra/Awaaz Jaanch, live demo

## Seemayein aur aage ka plan
- Score ek likelihood hai, pakka saboot nahi — duniya ka koi tool 100% sahi nahi hota
- Awaaz jaanch abhi sirf WAV par; MP3 support aage jodege
- Aage ka plan: WhatsApp par seedha check, aur bade paimaane par testing
