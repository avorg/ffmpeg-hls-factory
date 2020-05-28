import unittest
from test_case import TestCase
import encoder
import mock
import json


class TestEncoder(TestCase):
    def test_mock_os(self):
        self._mock_os.path.isfile.return_value = False

        self.assertFalse(self._mock_os.path.isfile('testing'))

    def test_starts_job(self):
        self._mock_os.path.isfile.return_value = False
        self._mock_config.get.return_value = ''

        response = mock.MagicMock()
        response.read.return_value = json.dumps({
            'count': 1,
            'result': [
                {
                    'fileName': 'the_file_name',
                    'recordingId': 'the_recording_id',
                    'downloadPath': 'the_download_path',
                    'downloadHostname': 'the_download_hostname',
                    'destinationURL': 'the_destination_url',
                    'jobId': 'the_job_id',
                }
            ]
        })
        self._mock_urllib2.urlopen.return_value = response

        encoder.main()

        self._mock_logging.info.assert_any_call("### JOB START ###")

    def test_does_not_start_job_if_one_already_running(self):
        self._mock_os.path.isfile.return_value = True

        self._set_config_values('Encoder', log_file='the_log_file')

        encoder.main()

        self._mock_logging.info.assert_not_called()

    def test_logs_job_errors(self):
        self._mock_os.path.isfile.return_value = False

        self._set_config_values('Encoder')
        self._set_config_values('MasterAPI')
        self._set_config_values('WorldAPI')
        self._set_config_values('AWS_S3')

        response = mock.MagicMock()
        response.read.return_value = json.dumps({
            'count': 1,
            'result': [
                {
                    'fileName': 'the_file_name',
                    'recordingId': 'the_recording_id',
                    'downloadPath': 'the_download_path',
                    'downloadHostname': 'the_download_hostname',
                    'destinationURL': 'the_destination_url',
                    'jobId': 'the_job_id',
                }
            ]
        })
        self._mock_urllib2.urlopen.return_value = response

        encoder.main()

        self._mock_logging.error.assert_any_call("Job Error: list index out of range")

    def test_starts_generating_hls(self):
        self._mock_os.path.isfile.return_value = False

        response = mock.MagicMock()
        response.read.return_value = json.dumps({
            'count': 1,
            'result': [
                {
                    'fileName': 'the_file_name',
                    'recordingId': 'the_recording_id',
                    'downloadPath': 'the_download_path',
                    'downloadHostname': 'the_download_hostname',
                    'destinationURL': 'the_destination_url',
                    'jobId': 'the_job_id',
                }
            ]
        })
        self._mock_urllib2.urlopen.return_value = response

        encoder.main()

        self._mock_logging.info.assert_any_call("GENERATE HLS: START")


if __name__ == '__main__':
    unittest.main()
