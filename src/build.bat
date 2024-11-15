@echo off
rmdir /s /q "D:\work\MyLilNetworker\src\dist"
pyinstaller --name NetworkMonitor --noconsole --add-data "C:\Users\artgr\AppData\Local\Programs\Python\Python313\tcl\tcl8.6;tcl8.6" --add-data "C:\Users\artgr\AppData\Local\Programs\Python\Python313\tcl\tk8.6;tk8.6" main.py