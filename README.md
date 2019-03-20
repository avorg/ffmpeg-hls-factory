# ffmpeg-hls-factory
## Installation on EC2
- yum install git
- git clone https://github.com/AVORG/ffmpeg-hls-factory
- wget (check latest version [here](https://johnvansickle.com/ffmpeg/))
- tar -xf ffmpeg-file.xz
- copy settings.ini.example and add the values
- curl -O https://bootstrap.pypa.io/get-pip.py
- python get-pip.py --user
- pip install boto3 --user
- ffmpeg-hls-factory
- python encoder.py &
