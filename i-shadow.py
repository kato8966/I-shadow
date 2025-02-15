from tkinter import PhotoImage, Text, Tk, ttk


def start_shadowing():
    start_frame.grid_remove()
    shadowing_frame.grid(row=0, column=0, sticky='nwes')


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

shadowing_frame = ttk.Frame(root)
mic_on_icon = PhotoImage(file='icon/mic_on.png')
start_button = ttk.Button(shadowing_frame, image=mic_on_icon)
start_button.grid(row=0, column=0)
notice = ttk.Label(shadowing_frame, text='The icon is designed by '
                                         'SumberRejeki from Flaticon')
notice.grid(row=1, column=0)
shadowing_text = Text(shadowing_frame, wrap='word', state='disabled')
shadowing_text.grid(row=2, column=0, sticky='nwes')
shadowing_frame.grid_rowconfigure(2, weight=1)
shadowing_frame.grid_columnconfigure(0, weight=1)

root.mainloop()
