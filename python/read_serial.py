# read_serial.py
import serial
import csv
import time

ser = serial.Serial('/dev/ttyUSB0', 9600)
time.sleep(2)  # wait for Arduino to reset

print("Connected to Arduino")

with open("data.csv", "w", newline="") as file:
    writer = csv.writer(file)
    writer.writerow(["Timestamp", "SensorValue"])  # header

    while True:
        try:
            line = ser.readline().decode('utf-8').strip()
            print("Received:", line)

            if line:  # Optional: add further validation
                timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
                writer.writerow([timestamp, line])
                file.flush()

        except Exception as e:
            print("Error:", e)
            break
