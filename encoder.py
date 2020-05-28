#!/usr/bin/env python
# -*- coding: utf-8 -*-
# 1. Fetch job metadata from master
# 2. Download video from S3
# 3. Encode video into HLS
# 4. Encode mp4 video to different flavors and check into db
# 4. Generate main m3u8 files
# 5. Upload video to S3
# 6. Report job complete
import logging, os, ConfigParser

from api import ApiManager


def main():

    # change current working directory, usfeul when the script is executed by the cron job
    os.chdir('/home/ec2-user/ffmpeg-hls-factory/')

    init('settings.ini')
    # First check if the script is already running
    pid = str(os.getpid())
    pid_file = "/tmp/encoder.pid"

    # encoder is still running
    if os.path.isfile(pid_file):
        return

    file(pid_file, 'w').write(pid)

    api = ApiManager()
    job = api.get_job()
    # job = api.getLocalJob()

    if job.id != 0:
        logging.info("### JOB START ###")
        try:
            job.download_file()
            job.generate_hls(api)
            job.generate_mp4(api)
            job.status = 'OK'
        except Exception as e:
            job.status = 'Job Error: ' + e.__str__()
            logging.error(job.status)

        api.checkin_job(job)
        job.cleanup()
        logging.info("### JOB END %s ###" % job.recordingId)

    os.unlink(pid_file)


def init(settings_file):

    config = ConfigParser.ConfigParser()
    config.read(settings_file)
    logging.basicConfig(
        filename=config.get('Encoder','log_file'),
        format='%(asctime)s %(message)s',
        datefmt='%m/%d/%Y %I:%M:%S %p',
        level=logging.INFO
    )

if __name__ == '__main__':
    main()
