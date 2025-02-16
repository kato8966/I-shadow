import functools
import json
import operator
from collections import Counter
from queue import Queue
from tkinter import PhotoImage, Text, Tk, ttk

import nltk
import sounddevice as sd
import vosk


def tokenize_captions_per_line(caption):
    caption = caption.replace('&gt;', '>')
    tokenized = nltk.tokenize.wordpunct_tokenize(caption)
    return Counter(tokenized)


def tokenize_captions(captions):
    tokenized_captions_per_line = map(tokenize_captions_per_line,
                                      captions.splitlines())
    return functools.reduce(operator.add, tokenized_captions_per_line)


tokenized_captions = Counter()


def start_shadowing():
    global tokenized_captions
    tokenized_captions = tokenize_captions(caption_text.get('1.0', 'end'))
    start_frame.grid_remove()
    shadowing_frame.grid(row=0, column=0, sticky='nwes')
    global is_shadowing
    is_shadowing = True
    root.attributes("-topmost", 1)


audio_queue = Queue()
last_temp_result = ''


def callback_audio_in(event):
    global last_temp_result
    is_final = recognizer.AcceptWaveform(audio_queue.get())
    if is_final:
        result = json.loads(recognizer.Result())['text']
    else:
        result = json.loads(recognizer.PartialResult())['partial']
        if result == last_temp_result:
            return
    split_result = result.split()
    shadowing_text['state'] = 'normal'
    # `+ 2` is for the last newline a `Text` widget always puts and a trailing
    # whitespace.
    delete_chars = len(last_temp_result) + 2 if last_temp_result != '' else 1
    shadowing_text.delete(f'end -{delete_chars} chars', 'end')
    for word in split_result:
        shadowing_text.insert('end', word + ' ')
    shadowing_text['state'] = 'disabled'
    last_temp_result = '' if is_final else result
    shadowing_text.see('end')


root = Tk()
root.geometry('600x600')
root.title('I-shadow')
root.rowconfigure(0, weight=1)
root.columnconfigure(0, weight=1)

start_frame = ttk.Frame(root)
start_frame.grid(row=0, column=0, sticky='nwes')
mic_off_icon = PhotoImage(file='icon/mic_off.png')
start_button = ttk.Button(start_frame, image=mic_off_icon,
                          command=start_shadowing)
start_button.grid(row=0, column=0, columnspan=2)
notice = ttk.Label(start_frame, text='The icon is designed by SumberRejeki '
                                     'from Flaticon')
notice.grid(row=1, column=0, columnspan=2)

caption_text = Text(start_frame, wrap='none')
xs = ttk.Scrollbar(start_frame, orient='horizontal',
                   command=caption_text.xview)
ys = ttk.Scrollbar(start_frame, orient='vertical',
                   command=caption_text.yview)
caption_text['xscrollcommand'] = xs.set
caption_text['yscrollcommand'] = ys.set
caption_text.grid(row=2, column=0, sticky='nwes')
xs.grid(row=3, column=0, sticky='we')
ys.grid(row=2, column=1, sticky='ns')
start_frame.grid_rowconfigure(2, weight=1)
start_frame.grid_columnconfigure(0, weight=1)

is_shadowing = False
shadowing_frame = ttk.Frame(root)
mic_on_icon = PhotoImage(file='icon/mic_on.png')
start_button = ttk.Button(shadowing_frame, image=mic_on_icon)
start_button.grid(row=0, column=0)
notice = ttk.Label(shadowing_frame, text='The icon is designed by '
                                         'SumberRejeki from Flaticon')
notice.grid(row=1, column=0)
shadowing_text = Text(shadowing_frame, wrap='word', state='disabled')
shadowing_text.tag_configure('correct', foreground='#00FF00')
shadowing_text.tag_configure('incorrect', foreground='#FF0000')
shadowing_text.tag_configure('partial_correct', foreground='#CCFFCC')
shadowing_text.tag_configure('partial_incorrect', foreground='#FFCCCC')
shadowing_text.grid(row=2, column=0, sticky='nwes')
shadowing_frame.grid_rowconfigure(2, weight=1)
shadowing_frame.grid_columnconfigure(0, weight=1)

model = vosk.Model(lang='en-us')
samplerate = sd.query_devices(kind='input')['default_samplerate']
recognizer = vosk.KaldiRecognizer(model, int(samplerate))
shadowing_text.bind('<<audio_in>>', callback_audio_in)


def callback_rawinputstream(indata, frames, time, status):
    if is_shadowing:
        audio_queue.put(bytes(indata))
        shadowing_text.event_generate('<<audio_in>>')


with sd.RawInputStream(samplerate=samplerate, dtype='int16', channels=1,
                       callback=callback_rawinputstream):
    root.mainloop()
