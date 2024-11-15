import os
os.environ['TCL_LIBRARY'] = r'C:\Users\artgr\AppData\Local\Programs\Python\Python313\tcl\tcl8.6'
os.environ['TK_LIBRARY'] = r'C:\Users\artgr\AppData\Local\Programs\Python\Python313\tcl\tk8.6'

import tkinter as tk

root = tk.Tk()
root.title("Tkinter Test")
label = tk.Label(root, text="Tkinter is working!")
label.pack()
root.mainloop()