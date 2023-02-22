import psutil
import matplotlib.pyplot as plt
import os

class ProcessMonitor:
    def __init__(self):
        self.process_id = os.getpid()
        self.cpu_usage = []
        self.mem_usage = []
        self.start_time = None

    def start(self):
        self.start_time = psutil.Process(self.process_id).create_time()

    def stop(self):
        self.start_time = None

    def _get_process_cpu_usage(self):
        process = psutil.Process(self.process_id)
        return process.cpu_percent()

    def _get_process_memory_usage(self):
        process = psutil.Process(self.process_id)
        return process.memory_info().rss

    def update(self):
        if self.start_time is None:
            return
        elapsed_time = psutil.Process(self.process_id).create_time() - self.start_time
        self.cpu_usage.append(self._get_process_cpu_usage())
        self.mem_usage.append(self._get_process_memory_usage())

        print(self.cpu_usage)

    def plot(self):
        fig, ax = plt.subplots(2, 1, sharex=True)
        ax[0].set_ylabel('CPU Usage (%)')
        ax[1].set_ylabel('Memory Usage (Bytes)')
        ax[1].set_xlabel('Time (seconds)')

        for i in range(60):
            self.update()
            ax[0].plot(self.cpu_usage, 'r-')
            ax[1].plot(self.mem_usage, 'b-')
            plt.pause(1)

        plt.show()

