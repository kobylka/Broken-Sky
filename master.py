#!/usr/bin/env python3

import multiprocessing
import ftplib
import time
import os
from datetime import datetime
import psutil
import subprocess
from tkinter import *
import tkinter as tk

class MasterProcess:
    read_num = 250
    if_gain  = 16
    bb_gain  = 16
    spoofing = False
    generating = False

    def __init__(self):
        print("Welcome, System is Active, Detection Mode Engaged")
        self.detector_module = Detector()
        self.hackrf_module   = Hackrf()
        self.spoof_module    = GPS_spoofer()

        self.queue_finish = multiprocessing.Queue()
        self.queue_threshold = multiprocessing.Queue()

        self.start_tool()
        self.start_gui()

    def start_gui(self):
        self.win = tk.Tk()
        self.win.title("Counter Drone System GUI")
        self.win.geometry("600x250")

        self.brdc_text = tk.StringVar()
        if(self.spoof_module.brdc_present is True):
            self.brdc_text.set("BRDC File Present")
        else:
            self.brdc_text.set("No BRDC File Present")

        self.brdc_label = tk.Label(textvariable=self.brdc_text)
        self.brdc_label.pack()
        self.brdc_label.place(bordermode=OUTSIDE, relx=0.06, rely=0.05)
        
        button4 = tk.Button(text="Download BRDC", command=self.download_brdc)
        button4.pack()
        button4.place(bordermode=OUTSIDE, relx=0.075, rely=0.15)
        
        labelLine2 = tk.Label(text="----------------------------------")
        labelLine2.pack()
        labelLine2.place(bordermode=OUTSIDE, relx=0, rely=0.25)

        self.coordinates = tk.StringVar()
        self.coordinates.set("38.8977221,-77.0365938")

        coord_name = tk.Label(text = "Coordinates (lat,long)")
        coord_name.pack()
        coord_name.place(bordermode=OUTSIDE, relx=0.06, rely=0.3)
        
        coord      = tk.Entry(textvariable=self.coordinates)
        coord.pack()
        coord.place(bordermode=OUTSIDE, relx=0.05, rely=0.4)
        
        button5    = tk.Button(text="Generate spoofed GPS file", command=self.generate_gps)
        button5.pack()
        button5.place(bordermode=OUTSIDE, relx=0.03, rely=0.5)

        self.l_gain = tk.IntVar()
        self.l_gain.set(self.if_gain)
        self.g_gain = tk.IntVar()
        self.g_gain.set(self.bb_gain)
        self.debug_level = tk.IntVar()
        self.debug_level.set(0)
        
        #SLIDER/SCALE WIDGETS TO ADJUST THRESHOLD AND GAIN
        #LABELS IN BETWEEN IN ORDER TO IDENTIFY SLIDERS
        label1 = tk.Label(text="IF gain (dB)").pack()
        l = tk.Scale(self.win,orient=tk.HORIZONTAL, from_=0, to=40, resolution=8, variable=self.l_gain).pack()
        labelLine3 = tk.Label(text="----------------------------------").pack()

        label2 = tk.Label(text="Baseband gain (dB)").pack()
        g = tk.Scale(self.win,orient=tk.HORIZONTAL, from_=0, to=62, resolution=2, variable=self.g_gain).pack()

        button4 = tk.Button(text="Adjust gain", command=self.hackrf_adjust).pack()
            
        labelLine5 = tk.Label(text="----------------------------------").pack()
        
        #BUTTONS FOR START, STOP, AND ENGAGE
        button1 = tk.Button(text="Start", command=self.start_tool)
        button1.pack()
        button1.place(bordermode=OUTSIDE, relx=0.35, rely=0.8)
        button2 = tk.Button(text="Stop", command=self.stop_tool)
        button2.pack()
        button2.place(bordermode=OUTSIDE, relx=0.42, rely=0.8)
        button3 = tk.Button(text="Engage Spoof", command=self.hackrf_engage)
        button3.pack()
        button3.place(bordermode=OUTSIDE, relx=0.5, rely=0.8)

        label3 = tk.Label(text="Threshold in % of signals")
        label3.pack()
        label3.place(bordermode=OUTSIDE, relx=0.73, rely=0.05)
        
        threshold_perc = tk.Scale(self.win,orient=tk.HORIZONTAL, from_=1, to=100, command=self.change_threshold_perc)
        threshold_perc.set(20)
        threshold_perc.pack()
        threshold_perc.place(bordermode=OUTSIDE, relx=0.76, rely=0.12)
        
        labelLine6 = tk.Label(text="----------------------------------")
        labelLine6.pack()
        labelLine6.place(bordermode=OUTSIDE, relx=0.7, rely=0.28)

        label4 = tk.Label(text="Threshold level (dB)")
        label4.pack()
        label4.place(bordermode=OUTSIDE, relx=0.76, rely=0.33)
        
        threshold = tk.Scale(self.win, orient=tk.HORIZONTAL, from_=5, to=80, command=self.change_threshold)
        threshold.set(20)
        threshold.pack()
        threshold.place(bordermode=OUTSIDE, relx=0.76, rely=0.4)
        labelLine6 = tk.Label(text="----------------------------------")
        labelLine6.pack()
        labelLine6.place(bordermode=OUTSIDE, relx=0.7, rely=0.55)

        label1 = tk.Label(text="Debug level")
        label1.pack()
        label1.place(bordermode=OUTSIDE, relx=0.77, rely=0.6)
        
        self.debug_level = tk.Spinbox(self.win, from_=0, to=3, command=self.change_debug_level)
        self.debug_level.pack()
        self.debug_level.place(bordermode=OUTSIDE, relx=0.73, rely=0.7)

        self.win.protocol("WM_DELETE_WINDOW", self.close_window)
        self.win.mainloop()

    def close_window(self):
        self.stop_tool()
        self.win.destroy()

    def start_tool(self):
        if(self.queue_finish.empty() is False): # gps file is being generated
            return

        if(self.detector_module.running is False and self.hackrf_module.running is False and self.spoofing is False):
            # delete the previous capture file if it wasn't deleted upon exit
            del_cmd = 'del now.csv > nul 2>&1'
            subprocess.check_call(del_cmd.split(), shell=True)

            #self.hackrf_module.killHackrf()

            self.hackrf_module.start(self.queue_finish, self.if_gain, self.bb_gain)
            self.detector_module.start(self.queue_finish, self.queue_threshold, self.read_num)

        elif(self.detector_module.detectionProcess.is_alive() is False and self.hackrf_module.captureProcess.is_alive() is False and self.spoofing is False):
            self.hackrf_module.start(self.queue_finish)
            self.detector_module.start(self.queue_finish, self.queue_threshold, self.read_num)

    def stop_tool(self):
        if(self.detector_module.detectionProcess.is_alive() is True and self.hackrf_module.captureProcess.is_alive() is True):
            # delete the previous capture file if it wasn't deleted upon exit
            del_cmd = 'del now.csv > nul 2>&1'
            subprocess.check_call(del_cmd.split(), shell=True)

            self.detector_module.stop()
            self.hackrf_module.stop()

            self.detector_module.running = self.hackrf_module.running = False

        elif(self.spoofing is True):
            self.hackrf_module.killHackrf()
            self.spoofing = False
            self.start_tool()

            self.spoof_module.spoofing = False

        elif(self.queue_finish.empty() is False):
            for p in psutil.process_iter():
                if(len(p.name()) > 11):
                    if(p.name()[:11] == "gps-sdr-sim"):
                        p.kill()

    def hackrf_engage(self):
        try:
            if(self.spoofing is False and self.queue_finish.empty() is True):
                #something
                self.stop_tool()

                self.spoofing = True

                self.spoofingProcess = multiprocessing.Process(target=self.spoof_module.spoof)
                self.spoofingProcess.start()
        except:
            print("Hackrf not connected")
            if(self.spoofing is True):
                self.spoofing = False

    def hackrf_adjust(self):
        self.if_gain = self.l_gain.get()
        self.bb_gain = self.g_gain.get()

        self.stop_tool()
        self.start_tool()

    def download_brdc(self):
        if(self.spoof_module.download_brdc() is True):
            self.brdc_text.set("BRDC File Present")

    def generate_gps(self):
        if(self.queue_finish.empty() is True):
            self.stop_tool()
            self.spoof_module.generate_gps_file(self.coordinates.get(), self.queue_finish)

    def change_debug_level(self):
        self.queue_threshold.put(["debug_level", self.debug_level.get()])

    def change_threshold(self, val):
        self.queue_threshold.put(["dB", val])

    def change_threshold_perc(self, val):
        self.queue_threshold.put(["%", val])

class GPS_spoofer:
    spoofing = False
    generating = False

    def __init__(self):
        brdc_file = self.brdc_filename() # in case a date change after midnight, get a new filename

        try:
            with open(brdc_file, 'r') as brdc_archive:
                with open(brdc_file[:-2], 'r') as brdc:
                    self.brdc_present = True

        except IOError:
            self.brdc_present = False

    def generate_gps_file(self, coord, queue):
        self.queue_finish = queue

        if(self.brdc_present is True):
            if(self.generating is False):
                self.coord = coord

                self.generatingProcess = multiprocessing.Process(target=self.generating_process)
                self.generatingProcess.start()

        else:
            print("No BRDC file present")

    def generating_process(self):
        print("Starting generating spoofed GPS transmission file")
        try:
            self.generating = True

            self.queue_finish.put("generating")
            cmd = "binaries\gps-sdr-sim -b 8 -e " + self.brdc_filename(True) + " " + self.coord + ",100"
            subprocess.check_call(cmd.split(), shell=True)
        except:
            print("")
            print("Generating Stopped")

        self.generating = False
        self.queue_finish.get()

    def brdc_filename(self, short=False):
        date = datetime.fromtimestamp(time.time())

        year = str(date.timetuple().tm_year)
        day  = str(date.timetuple().tm_yday)
        year_short = year[2:]

        brdc_file = "brdc0" + day + "0." + year_short + "n"

        if(short is False):
            brdc_file += ".Z"

        return brdc_file

    def spoof(self):
        if(self.spoofing is False):
            print("Starting spoofed GPS transmission")
            try:
                self.spoofing = True
                #cmd = "hackrf_transfer -t white_house.bin -f 1575420000 -s 2600000 -a 1 -x 47 > nul 2>&1"
                cmd = "hackrf_transfer -t white_house.bin -f 1575420000 -s 2600000 -a 1 -x 47"
                subprocess.check_call(cmd.split(), shell=True)
            except:
                if(self.spoofing is False):
                    print("Hackrf not connected")
                else:
                    print("Spoofing finished")

            self.spoofing = False

    def download_brdc(self):
        date = datetime.fromtimestamp(time.time())

        year = str(date.timetuple().tm_year)
        day  = str(date.timetuple().tm_yday)
        year_short = year[2:]

        path = "gnss/data/daily/" + year + "/0" + day + "/" + year_short + "n"
        brdc_file = "brdc0" + day + "0." + year_short + "n.Z"

        print("Downloading BRDC file...")

        try:
            ftp = ftplib.FTP("198.118.242.40")
            ftp.login()
            ftp.cwd(path)
            ftp.retrbinary("RETR " + brdc_file, open(brdc_file, 'wb').write)
            ftp.quit()

            extract_cmd = 'binaries\\7z e ' + brdc_file + ' > nul 2>&1'
            subprocess.check_call(extract_cmd.split(), shell=True)

            self.brdc_present = True

            print("BRDC file downloaded and extracted")

            return True

        except Exception as e:
            print("Cannot download BRDC file")
            return False

class Detector:
    prev_avg = 0
    running = False
    threshold_count_level = 5
    threshold_value = 20
    last_detection  = 0
    prev_timestamp = 0
    debug_level = 0
    filename = "now.csv"

    def start(self, qfin, qthr, read_num):
        if(self.running is False):
            self.read_num = read_num
            self.logger = []
            self.detectionProcess = multiprocessing.Process(target=self.detection, args=(qfin,qthr))
            self.detectionProcess.start()
            self.running = True

    def stop(self):
        if(self.running is True):
            self.detectionProcess.terminate()
            print("Detection stopped")
            self.running = False

    def open_file(self, filename, start, lines):
        rows = []

        with open(filename, 'r') as reader:
            reader.seek(108*start, 0)      # move cursor to starting position
            file_end   = reader.seek(0, 2) # check the position of EOF
            chunk_length = (file_end - 108*start)/108

            if(int(chunk_length) < lines): # not enough data to read in yet
                return []

            i = 0
            while(i < lines):
                row = reader.readline()
                if(len(row) == 108):
                    rows.append(row.split(","))
                    i += 1

        return rows

    def detection(self, qfin, qthr):
        paused = 0
        start_line = 0
        started = False

        self.finish_queue = qfin
        self.threshold_queue = qthr

        i = 0
        while(self.finish_queue.empty()):
            try:
                if(started is False):
                    print("Starting detection")
                    started = True

                s = time.time()
                rows = []
                while(len(rows) < self.read_num):
                    rows = self.open_file(self.filename, start_line, self.read_num)

                paused = 0
                start_line += len(rows)
                self.parse_chunk(rows)

            except Exception as e:
                paused += 1

            if(paused > 100000):
                break

        self.finish_queue.get()

        if(started is True):
            print("Detection stopped")

        self.running = False

    def parse_chunk(self, rows):
        data_freqs = {}

        for row in rows:
            # parse data
            year = int(row[0][:4])
            month = int(row[0][5:7])
            day = int(row[0][8:10])
            hour = int(row[1][1:3])
            minute = int(row[1][4:6])
            second = int(row[1][7:9])
            microsecond = int(row[1][10:16])
            epoch_time = datetime(year,month,day,hour,minute,second,microsecond).timestamp()
            epoch_time = int(epoch_time*1000000)

            #parse frequency and band width
            freq_min = int(row[2])/1000000
            freq_max = int(row[3])/1000000
            step = float(row[4])/1000000
            num_samples = int(row[5])

            # Each row recieved from the hackrf_sweep driver contains 5 columns with 5 frequency bands
            # They are processed separately in the loop below
            if(freq_min < 2485.0): # operating frequency of DJI is 2400-2483
                for i in range(0,5):
                    freq_key = freq_min + step*i # calculate the frequency with offset
                    if(freq_key <= 2483.0): # operating frequency of DJI is 2400-2483
                        datapoint = float(row[6+i][:7])  # get the current row x column float value

                        # Initialize array of datapoints if it doesn't exist
                        if freq_key not in data_freqs:
                            data_freqs[freq_key] = []

                        # Add datapoint to the frequency dictionary
                        data_freqs[freq_key].append(datapoint)

        #exception just because it doesn't show errors in process_data without it (because it runs in a separate process)
        try:
            self.process_data(data_freqs)
        except Exception as e:
            print(e)


        if((time.time() - self.last_detection) > 2):
            print(datetime.fromtimestamp(time.time()).strftime("%H:%M:%S") + ": DETECTION ACTIVE. NO DRONE")

    def process_data(self, data_freqs):
        newline = False
        total_avg = 0
        prev_freq = 0

        start_range_cont = 0
        start_range_int  = 0

        sigcount_cont = 0
        sigcount_int  = 0

        continuous = {}
        interrupted_once = {}

        while(self.threshold_queue.empty() is False):
            command = self.threshold_queue.get()
            if(command[0] == "dB"):
                self.threshold_value = int(command[1])
            elif(command[0] == "%"):
                self.threshold_count_level = int((float(command[1])/100) * (self.read_num/20))
                if(self.threshold_count_level == 0):
                    self.threshold_count_level = 1
            elif(command[0] == "debug_level"):
                self.debug_level = int(command[1])

        for freq in sorted(data_freqs):
            threshold = self.prev_avg + self.threshold_value

            threshold_count = 0
            num_signals = len(data_freqs[freq])
            suma=0
            maximum=-1000
            maximum_sig_num=-1
            i=0
            for sig in data_freqs[freq]:
                suma += sig
                if(sig > maximum):
                    maximum = sig
                    maximum_sig_num = i
                if(sig > threshold):
                    threshold_count += 1
                i += 1

            avg = round(suma/num_signals, 2)
            total_avg += avg

            avg_str = str(avg)
            maximum_str = str(maximum)

            if(len(avg_str) < 6): #padding
                avg_str += "0"
            if(len(maximum_str) < 6):
                maximum_str += "0"

            if(threshold_count >= self.threshold_count_level and avg != 0):
                if(self.debug_level > 1):
                    print("Frequency: " + str(freq) + "; samples: " + str(num_signals) + "; avg: " + avg_str + "dB; max: " + maximum_str + "dB @ " + str(maximum_sig_num) + "; #sig > " + str(threshold) + "dB: " + str(threshold_count) + " noise: " + str(self.prev_avg))
                    newline = True

                diff = freq - prev_freq # get the difference between current frequency band above threshold and the previous one
                if(diff <= 1.0): # count continuous and interrupted transmissions (interrupted should include continuous too)
                    if(start_range_cont == 0.0):
                        start_range_cont = prev_freq
                    sigcount_cont += threshold_count

                    if(start_range_int == 0.0):
                        start_range_int = prev_freq
                    sigcount_int += threshold_count

                elif(diff <= 2.0): # count interrupted transmissions (no more
                    start_range_cont = freq
                    sigcount_cont = threshold_count

                    if(start_range_int == 0.0):
                        start_range_int = prev_freq
                    sigcount_int += threshold_count

                else: # reset counts, assume current frequency is a beginning
                    start_range_cont = freq
                    start_range_int  = freq
                    sigcount_cont = threshold_count
                    sigcount_int  = threshold_count

                # Plus one since 2401-2400 MHz would be 1 MHz but there 2 frequencies in the range 2401-2400 MHz : 2401 MHz and 2400 MHz
                range_cont = (freq - start_range_cont) + 1
                range_int  = (freq - start_range_int) + 1

                if(range_cont > 5.0): # only consider ranges wider than 5 MHz
                    continuous[start_range_cont] = [freq, range_cont, sigcount_cont]

                if(range_int > 5.0):
                    interrupted_once[start_range_int] = [freq, range_int, sigcount_int]

                prev_freq = freq

        # The only thing happening below is displaying intermediate results. This will become a optional debug output later on.

        if(newline is True and self.debug_level > 1): print()

        if(len(continuous) > 0 or len(interrupted_once) > 0):
            if(self.detect_dji(continuous) is False):
               is_there_drone = self.detect_dji(interrupted_once)

        # Calculate and save the base noise level ( avg of all averages in each band in the considered spectrum )
        self.prev_avg = round(total_avg/len(data_freqs), 2)

    def detect_dji(self, dataset):
        retval = False
        freq_min_start = [[2400, 2415], [2420, 2435], [2440, 2452], [2455, 2465]]

        #remove signals older than 3 seconds
        for timestamp in self.logger:
            if(round(time.time()) - timestamp > 3):
                self.logger.remove(timestamp)

        #if some signals was removed and there is no more signals, give up
        if(len(dataset) == 0):
            return False

        is_there_drone = False

        #check if there is a signal within signature - between 9 and 30 MHz long, starting between 2400-2410 MHz or 2455-2465 MHz
        for freq in dataset:
            for start in freq_min_start:
                for r in range(start[0], start[1]):
                    if(freq == r and dataset[freq][1] >= 10 and dataset[freq][1] <= 30):
                        self.logger.append(round(time.time(), 2))
                        retval = True

        #if there are more than 10 signals in past 3 seconds, it's a hit. there can be maximum 20 signals processed in 3 seconds, so it's 10/20
        if(len(self.logger) > 10):
            self.last_detection = time.time()
            print(datetime.fromtimestamp(time.time()).strftime("%H:%M:%S") + ": DRONE DETECTED - " + str(len(self.logger)) + " signals")
        elif(self.debug_level > 0):
            print(dataset)
            print(len(self.logger))

        return retval

class Hackrf:
    processName = "hackrf_"
    running = False

    def start(self, q, if_gain=16, bb_gain=16):
        if(self.running is False):
            self.if_gain = if_gain
            self.bb_gain = bb_gain
            self.captureProcess = multiprocessing.Process(target=self.capture, args=(q,))
            self.captureProcess.start()
            print("Starting capture")
            self.running = True

    def stop(self):
        if(self.running is True):
            self.captureProcess.terminate()
            print("Capturing stopped")
            self.running = False

            self.killHackrf()

    def killHackrf(self):
        # check whether the process name matches
        for p in psutil.process_iter():
            if(len(p.name()) > 7):
                if(p.name()[:7] == self.processName):
                    p.kill()

        #restart only for hackrf_transfer
        cmd = 'hackrf_spiflash -R > nul 2>&1'
        try:
            subprocess.check_call(cmd.split(), shell=True)
        except subprocess.CalledProcessError:
            pass

    def capture(self, q):
        # Since bandwidth is fixed to 20MHz for sweeping for a certain reason, 2483 MHz will be rounded to 2500 MHz for sweeping

        cmd = 'hackrf_sweep -a 1 -l ' + str(self.if_gain) + ' -g ' + str(self.bb_gain) + ' -f 2400:2483 -r now.csv > nul 2>&1'
        try:
            subprocess.check_call(cmd.split(), shell=True) # returns the exit status
        except subprocess.CalledProcessError:
            print('Error: Hackrf not connected')

        q.put("finish")
        self.running = False

        print("Capturing stopped")

if __name__ == '__main__':
    master = MasterProcess()