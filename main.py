"""Launcher for the ECHO desktop application.

Running this script starts the Tkinter GUI defined in ``app_gui.py``; the
camera feed, gesture menu, and modes all come up automatically.
"""

from app_gui import EchoApp

if __name__ == "__main__":
    EchoApp().mainloop()
