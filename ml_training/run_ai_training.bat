@echo off
:loop
python test_ml_data_gen.py
python train_ml_model.py
goto loop
