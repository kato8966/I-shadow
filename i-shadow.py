import functools
import json
import logging
import operator
import os
import shutil
from collections import Counter
from queue import Queue
from time import time
from tkinter import PhotoImage, StringVar, Text, Tk, ttk

import nltk
import sounddevice as sd
import toml
import vosk


class IShadowApp:
    def __init__(self) -> None:
        self.tokenized_captions: Counter[str] = Counter()
        self.total_captions_words = 0
        self.audio_queue: Queue[bytes] = Queue()
        self.last_temp_trans: list[tuple[str, bool]] = []
        self.true_positives = 0
        self.total_user_words = 0
        self.last_time_temp_result_put = time()
        self.logger = logging.getLogger(__name__)
        logging.basicConfig(level=logging.WARNING)
        self.model = vosk.Model(lang='en-us')
        device = sd.query_devices(kind='input')
        assert isinstance(device, dict)
        self.samplerate = device['default_samplerate']
        self.recognizer = vosk.KaldiRecognizer(
            self.model, int(self.samplerate)
        )
        self.root = Tk()
        if not os.path.exists('config-geometry.json'):
            shutil.copy(
                'config-geometry-default.json',
                'config-geometry.json'
            )
        with open('config-geometry.json') as fin:
            self.root.geometry(json.load(fin))
        self.root.title('I-shadow')
        self.root.rowconfigure(0, weight=1)
        self.root.columnconfigure(0, weight=1)
        self.root.protocol('WM_DELETE_WINDOW', self.on_closing)
        self.setup_frames()
        self.rawinputstream = sd.RawInputStream(
            samplerate=self.samplerate,
            dtype='int16',
            channels=1,
            callback=self.callback_rawinputstream
        )

    def setup_frames(self):
        self.start_frame = ttk.Frame(self.root)
        self.start_frame.grid(row=0, column=0, sticky='nwes')
        self.mic_off_icon = PhotoImage(file='icon/mic_off.png')
        self.start_button = ttk.Button(
            self.start_frame,
            image=self.mic_off_icon,
            command=self.start_shadowing
        )
        self.start_button.grid(row=0, column=0, columnspan=2)
        notice = ttk.Label(
            self.start_frame,
            text='The icon is designed by SumberRejeki from Flaticon'
        )
        notice.grid(row=1, column=0, columnspan=2)
        self.caption_text = Text(self.start_frame, wrap='none')
        xs = ttk.Scrollbar(
            self.start_frame,
            orient='horizontal',
            command=self.caption_text.xview
        )
        ys = ttk.Scrollbar(
            self.start_frame,
            orient='vertical',
            command=self.caption_text.yview
        )
        self.caption_text['xscrollcommand'] = xs.set
        self.caption_text['yscrollcommand'] = ys.set
        self.caption_text.grid(row=2, column=0, sticky='nwes')
        xs.grid(row=3, column=0, sticky='we')
        ys.grid(row=2, column=1, sticky='ns')
        self.start_frame.grid_rowconfigure(2, weight=1)
        self.start_frame.grid_columnconfigure(0, weight=1)

        self.shadowing_frame = ttk.Frame(self.root)
        self.mic_on_icon = PhotoImage(file='icon/mic_on.png')
        self.stop_button = ttk.Button(
            self.shadowing_frame,
            image=self.mic_on_icon,
            command=self.finish_shadowing
        )
        self.stop_button.grid(row=0, column=0)
        notice = ttk.Label(
            self.shadowing_frame,
            text='The icon is designed by SumberRejeki from Flaticon'
        )
        notice.grid(row=1, column=0)
        self.shadowing_text = Text(
            self.shadowing_frame,
            wrap='word',
            state='disabled'
        )
        self.shadowing_text.tag_configure('correct', foreground='#00FF00')
        self.shadowing_text.tag_configure('incorrect', foreground='#FF0000')
        self.shadowing_text.tag_configure(
            'partial_correct', foreground='#CCFFCC'
        )
        self.shadowing_text.tag_configure(
            'partial_incorrect', foreground='#FFCCCC'
        )
        self.shadowing_text.grid(row=2, column=0, sticky='nwes')
        self.shadowing_frame.grid_rowconfigure(2, weight=1)
        self.shadowing_frame.grid_columnconfigure(0, weight=1)

        self.processing_audio_frame = ttk.Frame(self.root)
        self.processed_audio_queue_percent = StringVar()
        self.processed_audio_queue_percent_label = ttk.Label(
            self.processing_audio_frame,
            textvariable=self.processed_audio_queue_percent
        )
        self.processed_audio_queue_percent_label.grid(row=0, column=0)
        self.processing_audio_frame.grid_rowconfigure(0, weight=1)
        self.processing_audio_frame.grid_columnconfigure(0, weight=1)

        self.result_frame = ttk.Frame(self.root)
        self.pr_result_content = StringVar()
        self.pr_result = ttk.Label(
            self.result_frame,
            textvariable=self.pr_result_content
        )
        self.f1_score = StringVar()
        self.f1_score_label = ttk.Label(
            self.result_frame,
            textvariable=self.f1_score
        )
        pyproject = toml.load('pyproject.toml')
        self.version_info = ttk.Label(
            self.result_frame,
            text=f'(I-shadow ver. {pyproject['project']['version']})'
        )
        self.pr_result.grid(row=0, column=0)
        self.f1_score_label.grid(row=1, column=0)
        self.version_info.grid(row=2, column=0)
        self.result_frame.grid_rowconfigure(2, weight=1)
        self.result_frame.grid_columnconfigure(0, weight=1)

    def tokenize_captions_per_line(self, caption: str) -> Counter[str]:
        caption = caption.replace('&gt;', '>')
        tokenized = nltk.tokenize.wordpunct_tokenize(caption)
        lowered_tokenized = map(lambda word: word.lower(), tokenized)
        return Counter(lowered_tokenized)

    def tokenize_captions(self, captions: str) -> Counter[str]:
        tokenized_captions_per_line = map(self.tokenize_captions_per_line,
                                          captions.splitlines())
        return functools.reduce(operator.add, tokenized_captions_per_line)

    def process_audio(self, audio: bytes) -> None:
        INTERVAL = 0.1
        is_final = self.recognizer.AcceptWaveform(audio)
        if is_final:
            result = json.loads(self.recognizer.Result())['text']
        else:
            result = json.loads(self.recognizer.PartialResult())['partial']
        if (not is_final and not self.rawinputstream.stopped
                and time() - self.last_time_temp_result_put < INTERVAL):
            return
        if not is_final:
            self.last_time_temp_result_put = time()
        self.process_trans(result, is_final)

    def process_trans(self, trans: str, is_final: bool) -> None:
        split_trans = trans.split()
        if is_final:
            temp_trans_first_different_index = 0
        else:
            min_len = min(len(self.last_temp_trans), len(split_trans))
            temp_trans_first_different_index = min_len
            for i in range(min_len):
                if self.last_temp_trans[i][0] != split_trans[i]:
                    temp_trans_first_different_index = i
                    break
        delete_words = (
            len(self.last_temp_trans) - temp_trans_first_different_index
        )
        delete_chars = 1  # delete the last newline a `Text` widget always puts
        self.total_user_words -= delete_words
        for _ in range(delete_words):
            word, is_correct = self.last_temp_trans.pop()
            delete_chars += len(word) + 1
            if is_correct:
                self.tokenized_captions[word] += 1
                self.true_positives -= 1
        self.shadowing_text['state'] = 'normal'
        self.shadowing_text.delete(f'end -{delete_chars} chars', 'end')
        self.total_user_words += (
            len(split_trans) - temp_trans_first_different_index
        )
        for word in split_trans[temp_trans_first_different_index:]:
            is_correct = self.tokenized_captions[word] >= 1
            if is_correct:
                self.tokenized_captions[word] -= 1
                self.true_positives += 1
            if not is_final:
                self.last_temp_trans.append((word, is_correct))
            tag = (
                f"{'' if is_final else 'partial_'}"
                f"{'correct' if is_correct else 'incorrect'}"
            )
            self.shadowing_text.insert('end', word + ' ', tag)
        self.shadowing_text['state'] = 'disabled'
        self.shadowing_text.see('end')

    def process_audio_queue(self):
        INTERVAL = 0.1
        loop_begin_time = time()
        while (
            time() - loop_begin_time < INTERVAL and
            not self.audio_queue.empty()
        ):
            self.process_audio(self.audio_queue.get())
            self.logger.debug(
                'audio_queue popped. '
                f'remaining queue size: {self.audio_queue.qsize()}'
            )

        if self.rawinputstream.stopped:
            percent = round(
                (self._audio_queue_size_when_finished_shadowing - self.audio_queue.qsize()) / self._audio_queue_size_when_finished_shadowing * 100  # noqa: E501
            ) if self._audio_queue_size_when_finished_shadowing > 0 else 100
            self.processed_audio_queue_percent.set(
                f'Processing audio: {percent}% done'
            )

        if self.rawinputstream.stopped and self.audio_queue.empty():
            self.show_result()
        else:
            self.root.after_idle(self.process_audio_queue)

    def start_shadowing(self):
        self.logger.info('start shadowing')
        self.tokenized_captions = self.tokenize_captions(
            self.caption_text.get('1.0', 'end')
        )
        self.total_captions_words = self.tokenized_captions.total()
        self.start_frame.grid_remove()
        self.shadowing_frame.grid(row=0, column=0, sticky='nwes')
        self.root.attributes("-topmost", 1)
        self.rawinputstream.start()
        self.process_audio_queue()

    def calculate_f1_score(self):
        p = (
            self.true_positives / self.total_user_words
            if self.total_user_words > 0 else 0
        )
        r = (
            self.true_positives / self.total_captions_words
            if self.total_captions_words > 0 else 0
        )
        f1 = (2 * p * r) / (p + r) if p + r > 0 else 0
        p = round(p * 100)
        r = round(r * 100)
        f1 = round(f1 * 100)
        if self.true_positives != self.total_user_words:
            p = min(p, 99)
            f1 = min(f1, 99)
        if self.true_positives != self.total_captions_words:
            r = min(r, 99)
            f1 = min(f1, 99)
        return p, r, f1

    def show_result(self):
        self.processing_audio_frame.grid_remove()
        self.result_frame.grid(row=0, column=0, sticky='nwe')
        p, r, f1 = self.calculate_f1_score()
        self.pr_result_content.set(
            f'Precision: {p}\nRecall: {r}\nYour F1 score is ...\n'
        )
        self.f1_score.set(str(f1))

    def finish_shadowing(self):
        self.logger.info('finish shadowing')
        self.rawinputstream.stop()
        self.logger.info('rawinputstream stopped')
        self.shadowing_frame.grid_remove()
        self.processing_audio_frame.grid(
            row=0, column=0, sticky='nwe'
        )
        self._audio_queue_size_when_finished_shadowing = (
            self.audio_queue.qsize()
        )
        self.processed_audio_queue_percent.set('Processing audio: 0% done')

    def on_closing(self):
        with open('config-geometry.json', 'w') as fout:
            json.dump(self.root.geometry(), fout)
        self.root.destroy()

    def callback_rawinputstream(self, indata, frames, time_, status):
        self.audio_queue.put(bytes(indata))
        self.logger.debug(
            'audio_queue pushed. '
            f'remaining queue size: {self.audio_queue.qsize()}'
        )

    def run(self):
        try:
            self.root.mainloop()
        finally:
            self.rawinputstream.close()


if __name__ == '__main__':
    app = IShadowApp()
    app.run()
