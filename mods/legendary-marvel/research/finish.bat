@echo off
python C:\Users\steph\match5.py
python C:\Users\steph\finalize.py
copy /Y "E:\Media\Board Games\TTS_work\matches.csv" "E:\Media\Board Games\TTS_work\matches_pre_rescue.csv"
python C:\Users\steph\rescue2.py
python C:\Users\steph\build.py
python C:\Users\steph\install.py install