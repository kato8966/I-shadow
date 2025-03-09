import functools
import json
import logging
import operator
import os
import shutil
from collections import Counter
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
    root.attributes("-topmost", 1)
    rawinputstream.start()


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
    rawinputstream.stop()
    logger.info('rawinputstream stopped')
    shadowing_frame.grid_remove()

    if audio_queue.empty():
        show_result()


audio_queue = Queue()
last_temp_result = []
true_positives = 0
total_user_words = 0


def process_audio(audio):
    is_final = recognizer.AcceptWaveform(audio)
    if is_final:
        result = json.loads(recognizer.Result())['text']
    else:
        result = json.loads(recognizer.PartialResult())['partial']
    split_result = result.split()

    if is_final:
        temp_result_first_different_index = 0
    else:
        min_len = min(len(last_temp_result), len(split_result))
        temp_result_first_different_index = min_len
        for i in range(min_len):
            if last_temp_result[i][0] != split_result[i]:
                temp_result_first_different_index = i
                break

    delete_words = len(last_temp_result) - temp_result_first_different_index
    delete_chars = 1  # delete the last newline a `Text` widget always puts

    global true_positives, total_user_words
    total_user_words -= delete_words
    for _ in range(delete_words):
        word, is_correct = last_temp_result.pop()
        delete_chars += len(word) + 1
        if is_correct:
            tokenized_captions[word] += 1
            true_positives -= 1

    shadowing_text['state'] = 'normal'
    shadowing_text.delete(f'end -{delete_chars} chars', 'end')

    total_user_words += len(split_result) - temp_result_first_different_index
    for word in split_result[temp_result_first_different_index:]:
        is_correct = tokenized_captions[word] >= 1
        if is_correct:
            tokenized_captions[word] -= 1
            true_positives += 1

        if not is_final:
            last_temp_result.append((word, is_correct))

        tag = (f"{'' if is_final else 'partial_'}"
               f"{'correct' if is_correct else 'incorrect'}")
        shadowing_text.insert('end', word + ' ', tag)
    shadowing_text['state'] = 'disabled'
    shadowing_text.see('end')

    if rawinputstream.stopped and audio_queue.empty():
        show_result()


def process_audio_queue():
    for _ in range(audio_queue.qsize()):
        process_audio(audio_queue.get())
        logger.debug('audio_queue popped. '
                     f'remaining queue size: {audio_queue.qsize()}')
    root.after(100, process_audio_queue)


def on_closing():
    with open('config-geometry.json', 'w') as fout:
        json.dump(root.geometry(), fout)
    root.destroy()


root = Tk()
if not os.path.exists('config-geometry.json'):
    shutil.copy('config-geometry-default.json', 'config-geometry.json')
with open('config-geometry.json') as fin:
    root.geometry(json.load(fin))
root.title('I-shadow')
root.rowconfigure(0, weight=1)
root.columnconfigure(0, weight=1)
root.protocol('WM_DELETE_WINDOW', on_closing)


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


def callback_rawinputstream(indata, frames, time, status):
    audio_queue.put(bytes(indata))
    logger.debug('audio_queue pushed. '
                 f'remaining queue size: {audio_queue.qsize()}')


rawinputstream = sd.RawInputStream(samplerate=samplerate, dtype='int16',
                                   channels=1,
                                   callback=callback_rawinputstream)

process_audio_queue()
try:
    root.mainloop()
finally:
    rawinputstream.close()
