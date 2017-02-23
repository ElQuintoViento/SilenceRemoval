# -*- coding: utf-8 -*-
import matplotlib.pyplot as plt
import numpy
import scipy
from scipy.io import wavfile
import sys

# Read
def read_in_audio(file_name):
    print("here")
    rate, data = wavfile.read(file_name, False)
    return data

# Write
#

# Graph
def plot_audio(file_name, samples):
    fig = plt.figure()
    fig.canvas.set_window_title(file_name)
    plt.plot(samples)
    plt.show()

#
def handle_file(file_name):
    data = read_in_audio(file_name)
    plot_audio(file_name, data)


if __name__ == "__main__":
    if len(sys.argv) >= 2:
        handle_file(sys.argv[1])