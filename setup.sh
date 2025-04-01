#!/bin/bash
python -m playwright install
python app.py "$@"
