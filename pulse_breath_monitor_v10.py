
import cv2
import numpy as np
import time
import json
import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk
from scipy.signal import butter, filtfilt, savgol_filter
from scipy.fft import fft, fftfreq
import threading
from datetime import datetime
from openpyxl import Workbook
from openpyxl.chart import LineChart, Reference
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

def load_config(path="config.json"):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {
            "fps": 30,
            "gamma": {"low_light": 1.8, "medium_light": 1.4, "high_light": 0.8},
            "bpm_thresholds": {"relax": 80, "moderate": 120},
            "roi": {"height_fraction": 0.3}
        }

CONFIG = load_config("config.json")
MEASUREMENT_TIME = 30
STABLE_WINDOW = 10
STABLE_THRESHOLD = 2.5

def auto_gamma_correction(image):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    mean_brightness = np.mean(gray)
    gamma = 1.0
    if mean_brightness < 60:
        gamma = CONFIG["gamma"]["low_light"]
    elif mean_brightness < 100:
        gamma = CONFIG["gamma"]["medium_light"]
    elif mean_brightness > 180:
        gamma = CONFIG["gamma"]["high_light"]
    inv_gamma = 1.0 / gamma
    table = np.array([(i / 255.0) ** inv_gamma * 255 for i in range(256)]).astype("uint8")
    return cv2.LUT(image, table)

def bandpass_filter(signal, fs, low, high, order=2):
    nyq = 0.5 * fs
    b, a = butter(order, [low / nyq, high / nyq], btype='band')
    return filtfilt(b, a, signal)

def lowpass_filter(signal, fs, cutoff=0.5, order=2):
    nyq = 0.5 * fs
    b, a = butter(order, cutoff / nyq, btype='low')
    return filtfilt(b, a, signal)

class PulseBreathMonitorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Monitor Puls & Respirație (v10)")
        self.root.geometry("950x850")
        self.root.configure(bg="#fff8e1")

        self.video_frame = tk.Frame(root, bg="#fff8e1")
        self.video_frame.place(x=80, y=20, width=640, height=480)
        self.canvas = tk.Canvas(self.video_frame, width=640, height=480, bg="black")
        self.canvas.pack()

        self.button_frame = tk.Frame(root, bg="#fff8e1")
        self.button_frame.place(x=0, y=520, width=950, height=50)
        self.start_button = ttk.Button(self.button_frame, text="Start Măsurare", command=self.toggle_measurement)
        self.start_button.place(x=30, y=5, width=150, height=40)
        self.save_button = ttk.Button(self.button_frame, text="Salvează Ritmul", command=self.save_pulse, state=tk.DISABLED)
        self.save_button.place(x=200, y=5, width=150, height=40)
        self.graph_button = ttk.Button(self.button_frame, text="Grafic Puls", command=self.show_graph, state=tk.DISABLED)
        self.graph_button.place(x=370, y=5, width=150, height=40)
        self.excel_button = ttk.Button(self.button_frame, text="Export Excel", command=self.save_to_excel, state=tk.DISABLED)
        self.excel_button.place(x=540, y=5, width=150, height=40)

        self.pulse_label = tk.Label(root, text="Puls: N/A", font=("Arial", 20, "bold"), bg="#fff8e1")
        self.pulse_label.place(x=350, y=600)
        self.breath_label = tk.Label(root, text="Respirație: N/A", font=("Arial", 16), bg="#fff8e1")
        self.breath_label.place(x=350, y=640)
        self.status_label = tk.Label(root, text="Stare: N/A", font=("Arial", 14), bg="#fff8e1")
        self.status_label.place(x=350, y=680)
        self.feedback_label = tk.Label(root, text="Recomandări: N/A", font=("Arial", 12), bg="#fff8e1", wraplength=700, justify="center")
        self.feedback_label.place(x=120, y=720)

        self.is_measuring = False
        self.cap = None
        self.photo = None
        self.ppg_values = []
        self.breath_values = []
        self.pulse_values = []
        self.time_values = []
        self.start_time = None
        self.fps = CONFIG["fps"]
        self.final_pulse = None
        self.final_breath = None

        self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
        self.graph_window = None
        self.fig, self.ax = plt.subplots(figsize=(6, 3))
        self.canvas_widget = None

    def try_open_camera(self):
        for i in range(3):
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                return cap
            cap.release()
        return None

    def toggle_measurement(self):
        if not self.is_measuring:
            self.start_measurement()
        else:
            self.stop_measurement()

    def start_measurement(self):
        self.cap = self.try_open_camera()
        if not self.cap:
            messagebox.showerror("Eroare", "Nu pot accesa nicio cameră (index 0-2)!")
            return
        self.is_measuring = True
        self.final_pulse = None
        self.final_breath = None
        self.start_button.config(text="Stop Măsurare")
        self.save_button.config(state=tk.DISABLED)
        self.graph_button.config(state=tk.DISABLED)
        self.excel_button.config(state=tk.DISABLED)
        self.ppg_values = []
        self.breath_values = []
        self.pulse_values = []
        self.time_values = []
        self.start_time = time.time()
        threading.Thread(target=self.process_video, daemon=True).start()

    def stop_measurement(self):
        self.is_measuring = False
        if self.cap:
            self.cap.release()
        self.start_button.config(text="Start Măsurare")
        if self.pulse_values:
            self.save_button.config(state=tk.NORMAL)
            self.graph_button.config(state=tk.NORMAL)
            self.excel_button.config(state=tk.NORMAL)

    def process_video(self):
        while self.is_measuring:
            ret, frame = self.cap.read()
            if not ret:
                continue
            elapsed_time = time.time() - self.start_time

            frame = auto_gamma_correction(frame)
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = self.face_cascade.detectMultiScale(gray, 1.1, 5)
            roi_forehead = None
            roi_lower = None

            for (x, y, w, h) in faces:
                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                forehead_y_end = y + int(h * 0.15)
                roi_forehead = frame[y:forehead_y_end, x:x + w]
                cv2.rectangle(frame, (x, y), (x + w, forehead_y_end), (255, 0, 0), 2)
                lower_y_start = y + int(h * 0.7)
                roi_lower = frame[lower_y_start:y + h, x:x + w]
                break

            if roi_forehead is not None:
                green_mean = np.mean(roi_forehead[:, :, 1])
                self.ppg_values.append(green_mean)
                if len(self.ppg_values) > 300:
                    self.ppg_values.pop(0)

                if len(self.ppg_values) >= 128:
                    pulse = self.compute_pulse()
                    current_time = elapsed_time
                    self.pulse_values.append(pulse)
                    self.time_values.append(current_time)
                    self.root.after(0, lambda p=pulse: self.pulse_label.config(text=f"Puls: {p:.1f} BPM"))
                    self.root.after(0, lambda p=pulse: self.update_status_label(p))

                    if pulse > CONFIG["bpm_thresholds"]["moderate"] and roi_lower is not None:
                        breath_signal = np.mean(cv2.cvtColor(roi_lower, cv2.COLOR_BGR2GRAY))
                        self.breath_values.append(breath_signal)
                        if len(self.breath_values) > 256:
                            self.breath_values.pop(0)
                        if len(self.breath_values) > 64:
                            breath_rate = self.compute_breath()
                            self.root.after(0, lambda br=breath_rate: self.breath_label.config(text=f"Respirație: {br:.1f} RPM"))
                            self.final_breath = breath_rate

                    if len(self.pulse_values) >= STABLE_WINDOW:
                        window = np.array(self.pulse_values[-STABLE_WINDOW:])
                        if np.ptp(window) < STABLE_THRESHOLD:
                            self.final_pulse = np.median(window)
                            self.root.after(0, lambda: self.pulse_label.config(text=f"Puls Final: {self.final_pulse:.1f} BPM"))
                            self.stop_measurement()
                            break

            if elapsed_time >= MEASUREMENT_TIME and self.final_pulse is None:
                self.final_pulse = np.median(self.pulse_values) if self.pulse_values else 0
                self.root.after(0, lambda: self.pulse_label.config(text=f"Puls Final: {self.final_pulse:.1f} BPM"))
                if self.final_breath:
                    self.root.after(0, lambda: self.breath_label.config(text=f"Respirație Final: {self.final_breath:.1f} RPM"))
                self.stop_measurement()
                break

            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            self.photo = ImageTk.PhotoImage(image=Image.fromarray(rgb_frame))
            self.root.after(0, self.update_canvas)

    def compute_pulse(self):
        signal = np.array(self.ppg_values) - np.mean(self.ppg_values)
        signal = savgol_filter(signal, 11, 3)
        filtered = bandpass_filter(signal, self.fps, 0.7, 3.0)
        fft_result = fft(filtered)
        freqs = fftfreq(len(filtered), 1 / self.fps)
        idx = np.argmax(np.abs(fft_result[:len(freqs)//2]))
        bpm = freqs[idx] * 60
        return bpm if bpm > 0 else 0

    def compute_breath(self):
        signal = np.array(self.breath_values) - np.mean(self.breath_values)
        filtered = lowpass_filter(signal, self.fps, cutoff=0.5)
        fft_result = fft(filtered)
        freqs = fftfreq(len(filtered), 1 / self.fps)
        idx = np.argmax(np.abs(fft_result[:len(freqs)//2]))
        rpm = freqs[idx] * 60
        return rpm if rpm > 0 else 0

    def update_status_label(self, bpm):
        if bpm < CONFIG["bpm_thresholds"]["relax"]:
            state = "Relaxat"
            feedback = "Stare normală. Puls în limite normale de repaus."
        elif bpm <= CONFIG["bpm_thresholds"]["moderate"]:
            state = "Efort moderat"
            feedback = "Puls crescut, indică activitate fizică ușoară sau stres."
        else:
            state = "Efort ridicat"
            feedback = "Puls ridicat și respirație monitorizată."
        self.status_label.config(text=f"Stare: {state}")
        self.feedback_label.config(text=f"Recomandări: {feedback}")

    def update_canvas(self):
        if self.photo:
            self.canvas.create_image(0, 0, image=self.photo, anchor=tk.NW)

    def save_pulse(self):
        if self.final_pulse is not None:
            with open("istoric_puls.txt", "a") as f:
                f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - Puls final: {self.final_pulse:.1f} BPM")
                if self.final_breath:
                    f.write(f" | Respirație: {self.final_breath:.1f} RPM")
                f.write("\n")
            messagebox.showinfo("Salvat", "Ritmul cardiac a fost salvat!")

    def save_to_excel(self):
        if not self.pulse_values or not self.time_values:
            messagebox.showwarning("Atenție", "Nu există date pentru export!")
            return
        wb = Workbook()
        ws = wb.active
        ws.title = "Date Puls"
        ws.append(["Timp (s)", "Puls (BPM)"])
        for t, p in zip(self.time_values, self.pulse_values):
            ws.append([t, p])
        chart = LineChart()
        chart.title = "Evoluția Pulsului"
        chart.x_axis.title = "Timp (s)"
        chart.y_axis.title = "Puls (BPM)"
        data = Reference(ws, min_col=2, min_row=1, max_row=len(self.pulse_values)+1)
        categories = Reference(ws, min_col=1, min_row=2, max_row=len(self.pulse_values)+1)
        chart.add_data(data, titles_from_data=True)
        chart.set_categories(categories)
        ws.add_chart(chart, "E5")
        filename = f"raport_puls_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.xlsx"
        wb.save(filename)
        messagebox.showinfo("Export Excel", f"Datele au fost salvate în {filename}")

    def show_graph(self):
        if not self.pulse_values or not self.time_values:
            messagebox.showwarning("Atenție", "Nu există date pentru grafic!")
            return
        if self.graph_window is None or not tk.Toplevel.winfo_exists(self.graph_window):
            self.graph_window = tk.Toplevel(self.root)
            self.graph_window.title("Evoluția Pulsului")
            self.graph_window.geometry("700x400")
            self.graph_window.configure(bg="#fff8e1")
            self.fig.clf()
            self.ax = self.fig.add_subplot(111)
            self.canvas_widget = FigureCanvasTkAgg(self.fig, master=self.graph_window)
            self.canvas_widget.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        self.ax.clear()
        self.ax.plot(self.time_values, self.pulse_values, marker='o', linestyle='-', color='blue')
        self.ax.set_xlabel("Timp (s)")
        self.ax.set_ylabel("Puls (BPM)")
        self.ax.set_title("Evoluția Pulsului în Timp")
        self.ax.grid(True)
        self.canvas_widget.draw()
        self.graph_window.lift()

    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    root = tk.Tk()
    app = PulseBreathMonitorApp(root)
    app.run()
