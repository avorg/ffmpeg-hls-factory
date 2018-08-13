# -*- coding: utf-8 -*-
import ConfigParser, logging,urllib, json, subprocess
import boto3, os, shutil

class Job(object):

    def __init__(self):

        config = ConfigParser.ConfigParser()
        config.read('settings.ini')

        self.id = 0
        self.status = 'Unknown'
        self.fileName = ''
        self.downloadPath = ''
        self.downloadHostname = ''
        self.destinationURL = ''
        self.ffmpeg = config.get('Encoder', 'ffmpeg')
        self.ffprobe = config.get('Encoder', 'ffprobe')
        self.ffprobe_params = config.get('Encoder', 'ffprobe_params')
        self.audio_encoder = config.get('Encoder', 'audio_encoder')
        self.hls_config = {
            '64': {
                'width': 0,
                'profile': config.get('Encoder', 'hls_audio'),
                'bandwidth': config.get('Encoder', 'audio_bandwidth'),
                'name': config.get('Encoder', 'audio_name')
            },
            '240': {
                'width': 352,
                'profile': config.get('Encoder', 'hls_cell'),
                'bandwidth': config.get('Encoder', 'cell_bandwidth'),
                'name': config.get('Encoder', 'cell_name')
            },
            '360': {
                'width': 640,
                'profile': config.get('Encoder', 'hls_wifi_360'),
                'bandwidth': config.get('Encoder', 'wifi_360_bandwidth'),
                'name': config.get('Encoder', 'wifi_360_name')
            },
            '720': {
                'width': 1280,
                'profile': config.get('Encoder', 'hls_wifi_720'),
                'bandwidth': config.get('Encoder', 'wifi_720_bandwidth'),
                'name': config.get('Encoder', 'wifi_720_name')
            },
            '1080': {
                'width': 1920,
                'profile': config.get('Encoder', 'hls_wifi_1080'),
                'bandwidth': config.get('Encoder', 'wifi_1080_bandwidth'),
                'name': config.get('Encoder', 'wifi_1080_name')
            }
        }
        self.mp4_config = {
            '240': {
                'width': 352,
                'profile': config.get('Encoder', 'mp4_240')
            },
            '360': {
                'width': 640,
                'profile': config.get('Encoder', 'mp4_360')
            },
            '720': {
                'width': 1280,
                'profile': config.get('Encoder', 'mp4_720')
            },
            '1080': {
                'width': 1920,
                'profile': config.get('Encoder', 'mp4_1080')
            }
        }
        self.output_dir_hls = config.get('Encoder', 'output_dir_hls')
        self.remote_dir_hls = config.get('Encoder', 'remote_dir_hls')
        self.output_dir_mp4 = config.get('Encoder', 'output_dir_mp4')
        self.s3_bucket = config.get('AWS_S3', 'Bucket')
        self.ios_playlist = ''
        self.web_playlist = ''
        self.mp4_file_name = ''
        # if the output directory does not exists, create one
        if not os.path.exists(self.output_dir_hls):
            os.makedirs(self.output_dir_hls)

        if not os.path.exists(self.output_dir_mp4):
            os.makedirs(self.output_dir_mp4)

    def download_file(self):

        opener = urllib.URLopener()
        try:
            full_path = self.downloadHostname + self.downloadPath + self.fileName
            logging.info("Job downloading %s from %s" % (self.fileName, full_path))
            opener.retrieve(full_path.encode('utf-8'), self.fileName)

        except IOError as e:
            logging.warning(e)
            raise Exception('DOWNLOAD FILE: Error: ' + e)

    def generate_hls(self, api):

        logging.info('GENERATE HLS: START')
        media_info = self.probe_media_file(self.fileName)
        width = 1920

        if 'width' in media_info:
            width = int(media_info['width'])

        for key in sorted(self.hls_config):

            if width >= self.hls_config[key]['width']:
                logging.info('GENERATE HLS: generating %s' % self.hls_config[key]['width'])
                cmd = (self.hls_config[key]['profile'] % (
                    self.ffmpeg,
                    self.fileName,
                    self.audio_encoder,
                    self.output_dir_hls+key)
                ).split()
                p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                out, err = p.communicate()
                #print out, err
            else:
                logging.info('GENERATE HLS: skipping %s (input movie is %s)' % (key, width))

        logging.info('GENERATE HLS: END')

        # transfer to S3
        self.transfer_S3(self.output_dir_hls, self.destinationURL + self.remote_dir_hls)

        # generate index m3u8
        self.write_ios_playlist(api)
        self.write_web_playlist(api)

    def generate_mp4(self, api):

        logging.info('GENERATE MP4: Begin')
        media_info = self.probe_media_file(self.fileName)
        width = 1920
        self.mp4_file_name, current_file_extension = os.path.splitext(self.fileName)
        file_extension = '.mp4'

        if 'width' in media_info:
            width = int(media_info['width'])

        for key in self.mp4_config:

            if width >= self.mp4_config[key]['width']:
                logging.info('GENERATE MP4: generating %s' % (key))

                # if the file is the same width and is mp4 don't encode, just use the same file
                if width > self.mp4_config[key]['width'] or current_file_extension != '.mp4':
                    cmd = (self.mp4_config[key]['profile'] % (
                        self.ffmpeg,
                        self.fileName,
                        self.audio_encoder,
                        self.output_dir_mp4+self.mp4_file_name+'_'+key)
                    ).split()

                    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    out, err = p.communicate()
                else:
                    logging.info('GENERATE MP4: Skipping same width as the original %s (input movie is %s)' % (key, width))
                    p = {}
                    out = {}

                if hasattr(p, 'returncode') and p.returncode:
                    logging.info('GENERATE MP4: ffmpeg failed out %s err %s' % (out, err))
                else:
                    logging.info('GENERATE MP4: check in')

                    if width > self.mp4_config[key]['width'] or current_file_extension != '.mp4':
                        file_path = self.output_dir_mp4 + self.mp4_file_name + '_' + key + file_extension
                        media_info = self.probe_media_file(file_path)
                        file_name = unicode(self.mp4_file_name + '_' + key + file_extension).encode('utf-8')
                    else:
                        file_path = self.fileName
                        file_name = unicode(self.fileName).encode('utf-8')
                    
                    api.checkin_flavor({
                        'recordingId': self.recordingId,
                        'filename': file_name,
                        'filesize': os.path.getsize(file_path),
                        'duration': round(float(media_info['duration']), 1),
                        'bitrate': media_info['bit_rate'],
                        'width': media_info['width'],
                        'height': media_info['height'],
                        'container': 'mp4'
                    })
            else:
                logging.info('GENERATE MP4: Skipping %s (input movie is %s)' % (key, width))

        logging.info('GENERATE MP4: End')

        # transfer to S3
        self.transfer_S3(self.output_dir_mp4, self.destinationURL)

    def write_ios_playlist(self, api):

        logging.info('WRITE IOS PLAYLIST: BEGIN')
        media_info = self.probe_media_file(self.fileName)
        width = 1920

        if 'width' in media_info:
            width = int(media_info['width'])

        file_name, file_extension = os.path.splitext(self.fileName)
        self.ios_playlist = file_name + ".m3u8"

        f = open(self.ios_playlist, 'w')
        f.write('#EXTM3U\n')

        for key in sorted(self.hls_config):
            if width >= self.hls_config[key]['width']:
                f.write('#EXT-X-STREAM-INF:PROGRAM-ID=1,NAME="%s",BANDWIDTH=%s\n'%(self.hls_config[key]['name'], self.hls_config[key]['bandwidth']))
                f.write(self.remote_dir_hls+key+'_.m3u8\n')

        f.close()

        self.transfer_S3_playlist(self.ios_playlist)

        logging.info('WRITE IOS PLAYLIST: checkin flavor')
        api.checkin_flavor({
            'recordingId': self.recordingId,
            'filename': unicode(self.ios_playlist).encode('utf-8'),
            'filesize': 0,
            'duration': round(float(media_info['duration']), 1),
            'bitrate': media_info['bit_rate'],
            'width': media_info['width'],
            'height': media_info['height'],
            'container': 'm3u8_ios'
        })
        logging.info('WRITE IOS PLAYLIST: ios playlist %s generated'%(self.ios_playlist))

    def write_web_playlist(self, api):

        logging.info('WRITE WEB PLAYLIST: BEGIN')
        media_info = self.probe_media_file(self.fileName)
        width = 1920

        if 'width' in media_info:
            width = int(media_info['width'])

        file_name, file_extension = os.path.splitext(self.fileName)
        self.web_playlist = file_name + "_web.m3u8"

        f = open(self.web_playlist, 'w')
        f.write('#EXTM3U\n')

        for key in sorted(self.hls_config):
            # omitt audio
            if int(key) != 64 and width >= self.hls_config[key]['width']:
                f.write('#EXT-X-STREAM-INF:PROGRAM-ID=1,NAME="%s",BANDWIDTH=%s\n'%(self.hls_config[key]['name'], self.hls_config[key]['bandwidth']))
                f.write(self.remote_dir_hls+key+'_.m3u8\n')

        f.close()

        self.transfer_S3_playlist(self.web_playlist)

        logging.info('WRITE WEB PLAYLIST: checkin flavor')
        api.checkin_flavor({
            'recordingId': self.recordingId,
            'filename': unicode(self.web_playlist).encode('utf-8'),
            'filesize': 0,
            'duration': round(float(media_info['duration']), 1),
            'bitrate': media_info['bit_rate'],
            'width': media_info['width'],
            'height': media_info['height'],
            'container': 'm3u8_web'
        })
        logging.info('WRITE IOS PLAYLIST: ios playlist %s generated'%(self.web_playlist))

    def transfer_S3_playlist(self, fileName):
        try:
            logging.info('S3 TRANSFER PLAYLIST: uploading files to bucket %s' % (self.s3_bucket))
            # Upload index playlist
            s3 = boto3.resource('s3')
            s3.meta.client.upload_file(os.path.join(fileName), self.s3_bucket, os.path.join(self.destinationURL, fileName), ExtraArgs={'ACL':'public-read'})

        except boto3.exception.S3ResponseError as e:
            # 403 Forbidden, 404 Not Found
            logging.error(e)
            raise Exception('S3 TRANSFER: error: ' + e)

        logging.info('S3 TRANSFER END')

    def transfer_S3(self, output_dir, destination):
        try:
            logging.info('S3 TRANSFER %s: uploading files to bucket %s' % (output_dir, self.s3_bucket))

            upload_file_names = []
            for (output_dir, dirname, filename) in os.walk(output_dir):
                upload_file_names.extend(filename)
                break

            s3 = boto3.resource('s3')

            for filename in upload_file_names:
                s3.meta.client.upload_file(os.path.join(output_dir + filename), self.s3_bucket, os.path.join(destination, filename), ExtraArgs={'ACL':'public-read'})

        except boto3.exception.S3ResponseError as e:
            # 403 Forbidden, 404 Not Found
            logging.error(e)
            raise Exception('S3 TRANSFER: error: ' + e)

        logging.info('S3 TRANSFER END')

    def probe_media_file(self, fileName):

        media_info = {}
        cmd = (self.ffprobe_params % (self.ffprobe, fileName)).split()
        logging.info('MEDIA PROBE: Probing %s' % fileName)
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err = p.communicate()
        #print out
        for line in out.split(os.linesep):
            if line.strip():
                name, value = line.partition("=")[::2]
                # ffprobe sometime returns many of the same values
                if name.strip() not in media_info:
                    if ( value == 'N/A'):
                        value = 0
                    media_info[name.strip()] = value
        logging.info('MEDIA PROBE: END');
        return media_info
        
    def cleanup(self):
        logging.info('Job: Cleaning up')
        # delete HLS directory with all of its contents
        shutil.rmtree(self.output_dir_hls)
        # delete MP4 directory with all of its contents
        shutil.rmtree(self.output_dir_mp4)
        # the exceptions were added in the case that the files doesn't exist
        
        try:
            os.remove(self.ios_playlist)
        except OSError:
            pass
        
        try:
            os.remove(self.web_playlist)
        except OSError:
            pass
        
        try:
            os.remove(self.fileName)
        except OSError:
            pass

    def __str__(self):
        print self.id, self.status, self.fileName, self.downloadPath, self.downloadHostname, self.output_dir_hls
