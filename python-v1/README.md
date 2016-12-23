# Setup
    ./aftergitclone.sh; # set up the python virtual environment
    . sourceme; # anytime you want to initialize a shell to work on the python program

Your prompt should now contain (.env) as a reminder that you are working on the pything program.
Try `which python` to verify that python is coming from the .env directory


$ export WORKON_HOME=~/Envs
$ mkdir -p $WORKON_HOME
$ source /usr/local/bin/virtualenvwrapper.sh
$ mkvirtualenv env1
