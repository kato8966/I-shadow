import functools
import json
import logging
import operator
from collections import Counter
from copy import copy
from queue import Queue
from tkinter import PhotoImage, StringVar, Text, Tk, ttk

import nltk
import sounddevice as sd
import vosk


def tokenize_captions_per_line(caption):
    caption = caption.replace('&gt;', '>')
    tokenized = nltk.tokenize.wordpunct_tokenize(caption)
    tokenized = map(lambda word: word.lower(), tokenized)
    return Counter(tokenized)


def tokenize_captions(captions):
    tokenized_captions_per_line = map(tokenize_captions_per_line,
                                      captions.splitlines())
    return functools.reduce(operator.add, tokenized_captions_per_line)


tokenized_captions = Counter()
total_captions_words = 0


def start_shadowing():
    logger.info('start shadowing')
    global tokenized_captions, total_captions_words
    tokenized_captions = tokenize_captions(caption_text.get('1.0', 'end'))
    total_captions_words = tokenized_captions.total()
    start_frame.grid_remove()
    shadowing_frame.grid(row=0, column=0, sticky='nwes')
    global is_shadowing
    is_shadowing = True
    root.attributes("-topmost", 1)


def calculate_f1_score():
    p = (true_positives / total_user_words if total_user_words > 0
         else 0)
    r = (true_positives / total_captions_words if total_captions_words > 0
         else 0)
    f1 = (2 * p * r) / (p + r) if p + r > 0 else 0

    p = round(p * 100)
    r = round(r * 100)
    f1 = round(f1 * 100)
    if true_positives != total_user_words:
        p = min(p, 99)
        f1 = min(f1, 99)
    if true_positives != total_captions_words:
        r = min(r, 99)
        f1 = min(f1, 99)
    return p, r, f1


def show_result():
    result_frame.grid(row=0, column=0, sticky='nwe')
    p, r, f1 = calculate_f1_score()
    pr_result_content.set(f'Precision: {p}\nRecall: {r}\n'
                          'Your F1 score is ...\n')
    f1_score.set(str(f1))


def finish_shadowing():
    logger.info('finish shadowing')
    global is_shadowing
    is_shadowing = False
    shadowing_frame.grid_remove()

    if audio_queue.empty():
        show_result()
    else:
        logger.debug(f'audio_queue size: {audio_queue.qsize()}')


audio_queue = Queue()
last_temp_result = ''
true_positives = 0
total_user_words = 0


def callback_audio_in(event):
    logger.info('callback audio in')
    global last_temp_result
    is_final = recognizer.AcceptWaveform(audio_queue.get())
    if is_final:
        result = json.loads(recognizer.Result())['text']
    else:
        result = json.loads(recognizer.PartialResult())['partial']
        if not is_shadowing and audio_queue.empty():
            is_final = True
        elif result == last_temp_result:
            return
    split_result = result.split()
    shadowing_text['state'] = 'normal'
    # `+ 2` is for the last newline a `Text` widget always puts and a trailing
    # whitespace.
    delete_chars = len(last_temp_result) + 2 if last_temp_result != '' else 1
    shadowing_text.delete(f'end -{delete_chars} chars', 'end')
    working_tokenized_captions = (tokenized_captions if is_final
                                  else copy(tokenized_captions))
    global true_positives, total_user_words
    for word in split_result:
        is_correct = working_tokenized_captions[word] >= 1
        if is_correct:
            working_tokenized_captions[word] -= 1
            if is_final:
                true_positives += 1
        tag = (f"{'' if is_final else 'partial_'}"
               f"{'correct' if is_correct else 'incorrect'}")
        shadowing_text.insert('end', word + ' ', tag)
    if is_final:
        total_user_words += len(split_result)
    shadowing_text['state'] = 'disabled'
    last_temp_result = '' if is_final else result
    shadowing_text.see('end')

    if not is_shadowing and audio_queue.empty():
        show_result()
    elif not is_shadowing:
        logger.debug(f'audio_queue size: {audio_queue.qsize()}')


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
stop_button = ttk.Button(shadowing_frame, image=mic_on_icon,
                         command=finish_shadowing)
stop_button.grid(row=0, column=0)
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

result_frame = ttk.Frame(root)
pr_result_content = StringVar()
pr_result = ttk.Label(result_frame, textvariable=pr_result_content)
f1_score = StringVar()
f1_score_label = ttk.Label(result_frame, textvariable=f1_score)
pr_result.grid(row=0, column=0)
f1_score_label.grid(row=1, column=0)
result_frame.grid_rowconfigure(1, weight=1)
result_frame.grid_columnconfigure(0, weight=1)

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)

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
