import psutil
import matplotlib.pyplot as plt
import time
import os

class SystemMonitor:
    def __init__(self):
        self.pid = os.getpid()
        self.times = []
        self.cpu_usage = []
        self.ram_usage = []

    def monitor(self):
        process = psutil.Process(self.pid)

        self.times.append(time.time())
        self.cpu_usage.append(process.cpu_percent())
        self.ram_usage.append(process.memory_percent())

    def plot(self):
        fig, ax = plt.subplots()
        ax.plot(self.times, self.cpu_usage, label="CPU Usage")
        ax.plot(self.times, self.ram_usage, label="RAM Usage")
        ax.legend()
        ax.set_xlabel("Time")
        ax.set_ylabel("Usage (%)")
        ax.set_title("System Monitor")
        plt.show()