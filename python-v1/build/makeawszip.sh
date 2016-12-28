#!/bin/bash
if [ $# -ne 1 ]; then
    echo supply the full qualified output file name without the .zip suffix like /tmp/foo to generate /tmp/foo.zip
    exit 1
fi

# name can be in the cwd
NAME="$(cd "$(dirname "$1")"; pwd)/$(basename "$1")"
echo $NAME

# cd to the DIR that contains this shell script, the files are next to this shell script
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd $DIR

# put everything into the provided name
set -x
zip $NAME cron.yaml application.py requirements.txt
unzip -lv $NAME
