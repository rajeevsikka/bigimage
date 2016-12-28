# Ingest
Ingest program that reads from the twitter home for a user and writes to the firehose.
Environment variables documented in the application identify these external entities.
# Layout
Directories:
* application - the application
* build - the python program to build the zip file
# Usage
Use an virtual python environment.  See [virtualenv](https://virtualenv.pypa.io/en/stable/userguide/):

    pip install virtualenv
    ./afterclone.sh
   source ./sourceme

./afterclone.sh will create a .env/ directory,
initialize the environment with the stuff needed from requirements.txt

source ./sourceme can be executed any time you need to initialize a new shell.
Your prompt should now contain (.env) as a reminder that you are working on the pything program.
It will also cd into the application/ directory to get you started.
Try `which python` to verify that python is coming from the .env directory

Once the firehose is running you can share it with a local application.

    export StackName=bigimage
    export DeliveryStreamName=bigimageTwitterDeliveryStream


