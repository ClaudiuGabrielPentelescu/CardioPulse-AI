
# Monitor Puls + Respirație (v10)

Aplicație Python pentru măsurarea pulsului și ritmului respirator folosind camera web și tehnica PPG (Photoplethysmography).

## **Noutăți v10**
- Oprire automată când pulsul devine stabil (ca un pulsoximetru).
- ROI exclusiv pe frunte pentru puls și zona inferioară pentru respirație.
- Corecție automată gamma (lumina slabă/naturală/puternică).
- Export Excel: fiecare măsurare salvează un fișier nou cu timestamp.
- Monitorizare **ritm respirator (RPM)** la efort ridicat.

## **Fișiere importante**
- `pulse_breath_monitor_v10.py` – scriptul principal.
- `config.json` – setările aplicației.
- `CHEAT_SHEET.txt` și `CHEAT_SHEET.pdf` – ghid rapid.
- `QUICK_START.txt` – pași rapizi de utilizare.
- `build_v10.bat` – script pentru generarea executabilului.
- `setup_v10.iss` – script Inno Setup.

## **Module necesare**
- Python 3.10+
- opencv-python, numpy, pillow, scipy, matplotlib, openpyxl

## **Cum rulezi aplicația**
```bash
pip install opencv-python numpy pillow scipy matplotlib openpyxl
python pulse_breath_monitor_v10.py
```

## **Build Executabil**
```bash
pip install pyinstaller
build_v10.bat
```

## **Licență**
Open-source, pentru scopuri educaționale.
