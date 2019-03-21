# ffmpeg-hls-factory
## Installation on EC2
- yum install git
- git clone https://github.com/AVORG/ffmpeg-hls-factory
- wget ffmpeg (check latest version [here](https://johnvansickle.com/ffmpeg/))
- tar -xf ffmpeg-file.xz
- copy settings.ini.example to settings.ini and add the values
- curl -O https://bootstrap.pypa.io/get-pip.py
- python get-pip.py --user
- pip install boto3 --user
- configure your aws [credentials file](https://boto3.amazonaws.com/v1/documentation/api/latest/guide/quickstart.html)
- cd ffmpeg-hls-factory
- python encoder.py &
