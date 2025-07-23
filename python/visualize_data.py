# visualize_data.py
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation

def animate(i):
    try:
        data = pd.read_csv("data.csv")
        x = data["Timestamp"][-20:]  # show last 20
        y = data["SensorValue"][-20:]

        ax.clear()
        ax.plot(x, y, marker='o')
        ax.set_title("Live Sensor Data")
        ax.set_xlabel("Time")
        ax.set_ylabel("Value")
        plt.xticks(rotation=45)
        plt.tight_layout()
    except Exception as e:
        print("Error reading data:", e)

fig, ax = plt.subplots()
ani = FuncAnimation(fig, animate, interval=1000)  # every 1 second
plt.show()












