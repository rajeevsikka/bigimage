#!/bin/bash
set -ex
cd application
virtualenv --no-site-packages --distribute .env && source .env/bin/activate && pip install -r requirements.txt
