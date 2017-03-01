# -*- coding: utf-8 -*-
import matplotlib.pyplot as plt
import numpy as np
import re
import scipy
from scipy.io import wavfile
import sys
from time import time


MAX_INT32 = np.iinfo(np.int32).max
MIN_INT32 = np.iinfo(np.int32).min
#
RE_EXT = r'\.{1}[\w|(0-9)]+$'
#
WINDOW_COUNT = 51  # Odd required
SIDE_COUNT = int(WINDOW_COUNT / 2)
QUARTER_COUNT = int(WINDOW_COUNT / 4)
# ALPHA_SMOOTH = 1.0 / float(SIDE_COUNT)
ALPHA_SMOOTH = 0.25
ALPHA_DECAY = 0.9
#
THRESHOLD_MINIMUM = 10.5
THRESHOLD_MINIMUM_WINDOW = 1.0
THRESHOLD_MINIMUM_REQUIRED_COUNT = 10


# Read
def read_audio(file_name):
    rate, data = wavfile.read(file_name, False)
    return (rate, list(data))


# Write
def write_audio(old_file_name, speech_data, rate):
    ext = re.findall(RE_EXT, old_file_name)[0]
    new_file_name = "{}_slnce_rmvd{}".format(
        re.sub(RE_EXT, '', old_file_name), ext)
    wavfile.write(new_file_name, rate, np.array(speech_data))


def get_envelope(data, repetitions=1):
    avg = 0
    count = len(data)
    samples = list(data)
    envelope = None
    #
    for r in range(max(repetitions, 1)):
        envelope = []
        for i in range(count):
            before_count = QUARTER_COUNT
            after_count = QUARTER_COUNT
            if i < QUARTER_COUNT:
                before_count = i
            if ((count - 1) - i) < QUARTER_COUNT:
                after_count = ((count - 1) - i)
            rng = [0]
            if before_count > -1:
                for s in range(before_count):
                    s_mod = pow(2, s)
                    if s_mod > before_count:
                        break
                    rng = [-1 * (s_mod)] + rng
                    # rng = [-1 * (s + 1)] + rng
            if after_count < count:
                for s in range(after_count):
                    s_mod = pow(2, s)
                    if s_mod > after_count:
                        break
                    rng += [s_mod]
                    # rng += [r + 1]
            # print("{} {}".format(i, rng))
            # envlp_pk = 0
            mx = -1
            avg = 0
            weight_sum = 0
            for j in rng:
                abs_sample = abs(samples[i + j])
                # envlp_pk += abs(samples[i + j])
                # weight = max(1, pow(QUARTER_COUNT - abs(j) + 1, 0.5))
                weight = np.cos(np.pi * j / QUARTER_COUNT) + 1.01
                weight_sum += weight
                avg += (abs_sample * weight)
                mx = max(mx, abs_sample)
            # avg /= len(rng)
            avg /= weight_sum
            # envlp_pk /= WINDOW_COUNT
            '''envlp_pk = (mx + envlp_pk) * 0.5
            avg = (
                envlp_pk * ALPHA_SMOOTH +
                avg * (1 - ALPHA_SMOOTH))
            '''
            abs_sample = abs(samples[i])
            val = (
                mx * ALPHA_SMOOTH +
                avg * (1 - ALPHA_SMOOTH))
            val = val if (val > abs_sample) else abs_sample
            #
            envelope.append(val)
        samples = envelope
    return envelope


# Find time intervals where there is speech
def get_speech_indices(envelope):
    indices = []
    potential_indices = []
    is_appending = False
    #
    count = len(envelope)
    average = THRESHOLD_MINIMUM # Allows first sample inclusion possibility
    decay = THRESHOLD_MINIMUM
    #
    i = 0
    while (i < count):
        before_count = QUARTER_COUNT
        after_count = QUARTER_COUNT
        if i < QUARTER_COUNT:
            before_count = i
        if ((count - 1) - i) < QUARTER_COUNT:
            after_count = ((count - 1) - i)
        rng = [0]
        '''
        if before_count > -1:
            for r in range(before_count):
                rng = [-1 * (r + 1)] + rng
        if after_count < count:
            for r in range(after_count):
                rng += [r + 1]
        '''
        if before_count > -1:
            for s in range(before_count):
                s_mod = pow(2, s)
                if s_mod > before_count:
                    break
                rng = [-1 * (s_mod)] + rng
                # rng = [-1 * (s + 1)] + rng
        if after_count < count:
            for s in range(after_count):
                s_mod = pow(2, s)
                if s_mod > after_count:
                    break
                rng += [s_mod]
        #
        average = (
            envelope[i] * ALPHA_SMOOTH + average * (1 - ALPHA_SMOOTH))
        decay = ALPHA_DECAY * (
            average * ALPHA_SMOOTH + decay * (1 - ALPHA_SMOOTH))
        _max = MIN_INT32
        _min = MAX_INT32
        for j in rng:
            _max = max(_max, envelope[i + j])
            _min = min(_min, envelope[i + j])
        #
        peak = pow((_min + _max + average) * decay, 0.25)
        '''
        if ((i + 1) % (WINDOW_COUNT * 50)) == 0:
            print(("min {:.2f} \t max {:.2f} \t avg {:.2f} \t dcy {:.2f} \t" +
                   "pk {:.2f}").format(
                _min, _max, average, decay, peak))
        '''
        # Within potential voice territory
        if ((peak >= THRESHOLD_MINIMUM) and
            ((peak - THRESHOLD_MINIMUM_WINDOW) < THRESHOLD_MINIMUM)):
            if not is_appending:
                if (len(potential_indices) + 1) >= THRESHOLD_MINIMUM_REQUIRED_COUNT:
                    indices += potential_indices
                    potential_indices = []
                    is_appending = True
                else:
                    potential_indices.append(i)
        # Voice territory
        elif (peak - THRESHOLD_MINIMUM_WINDOW) >= THRESHOLD_MINIMUM:
            is_appending = True
            if len(potential_indices) > 0:
                indices += potential_indices
                potential_indices = []
        # No voice; reset
        else:
            is_appending = False
            if len(potential_indices) > 0:
                potential_indices = []
        #
        if is_appending:
            indices.append(i)
        #
        i += 1
    return indices


#
def get_data_subset(data, indices):
    data_subset = []
    for i in indices:
        data_subset.append(data[i])
    return data_subset


#
def remove_silence(data, envelope):
    speech_indices = get_speech_indices(envelope)
    return get_data_subset(data, speech_indices)


# Graph
def plot_audio(file_name, data, envelope, speech_data):
    # Original data w/ envelope
    fig = plt.figure()
    fig.canvas.set_window_title(
        "File {}\nOriginal Data & Envelope".format(file_name))
    plt.plot(data)
    plt.plot(envelope)
    # Speech data
    fig = plt.figure()
    fig.canvas.set_window_title(
        "File {}\nSpeech Data".format(file_name))
    plt.plot(speech_data)
    # Render
    plt.show()


def output_elapsed_time(func_name, t):
    print("function {} took {:.2f} s".format(func_name, time() - t))
    return time()


#
def handle_file(file_name):
    t = time()
    rate, data = read_audio(file_name)
    t = output_elapsed_time("read_audio", t)
    # For testing
    # count = int(len(data) / 100)
    # data = data[:count]
    #
    envelope = get_envelope(data, 2)
    t = output_elapsed_time("get_envelope", t)
    #
    speech_data = remove_silence(data, envelope)
    t = output_elapsed_time("remove_silence", t)
    #
    # plot_audio(file_name, data, envelope, speech_data)
    # t = output_elapsed_time("plot_audio", t)
    #
    write_audio(file_name, speech_data, rate)
    t = output_elapsed_time("write_audio", t)


if __name__ == "__main__":
    if len(sys.argv) >= 2:
        handle_file(sys.argv[1])
