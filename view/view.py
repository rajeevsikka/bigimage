#!/usr/bin/env python
import os
import shutil
import sys


def dumpMe():
    START_DUMP = '#--startDump'
    STOP_DUMP = '#--stopDump'
    s = sys.argv[0]
    print s
    dumping = False
    me = open(s)

    for line in me:
        if line.strip() == START_DUMP:
            dumping = True
        elif line.strip() == STOP_DUMP:
            dumping = False
        else:
            if dumping:
                print line,
    me.close()
dumpMe()

#--startDump
print __name__
from flask import Flask
import json
app = Flask(__name__)

@app.route('/contents/')
def contents():
    contents = {
        "version": "0.1",
        "attributes": ["terms", "dates", "description"],
    }
    return json.dumps(contents)

@app.route("/")
def hello():
    return "hello world"

if __name__ == "__main__":
    app.run()
