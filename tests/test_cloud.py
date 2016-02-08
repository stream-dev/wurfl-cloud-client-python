import json
from sys import maxsize
from six import binary_type

import requests_mock
from requests.exceptions import RequestException
from nose.tools import raises

from wurfl_cloud import Cloud, utils
from wurfl_cloud.cache.null_cache import NullCache
from collections import namedtuple

TestData = namedtuple(
    u'TestData',
    [
        u'user_agent',
        u'headers',
        u'id',
        u'apiVersion',
        u'mtime',
        u'device_claims_web_support',
        u'is_wireless_device',
        u'errors',
    ]
)

API_VERSION = u'WurflCloud 1.5.0.2'
XCLOUD_CLIENT_HEADER = u'WurflCloud_Client/Python_1.1.0'

PC_AGENT = u'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) ' \
           u'Ubuntu Chromium/44.0.2403.89 Chrome/44.0.2403.89 Safari/537.36'
ANDROID_AGENT = u'Mozilla/5.0 (Linux; U; Android 4.0.3; ko-kr; LG-L160L Build/IML74K) ' \
                u'AppleWebkit/534.30 (KHTML, like Gecko) Version/4.0 Mobile Safari/534.30'
IPAD_AGENT = u'Mozilla/5.0 (iPad; CPU OS 9_1 like Mac OS X) ' \
             u'AppleWebKit/600.1.4 (KHTML, like Gecko) GSA/9.0.60246 Mobile/13B143 Safari/600.1.4'
IPHONE_AGENT = u'Mozilla/5.0 (iPhone; CPU iPhone OS 8_4_1 like Mac OS X) ' \
               u'AppleWebKit/600.1.4 (KHTML, like Gecko) Version/8.0 Mobile/12H321 Safari/600.1.4'
BLACKBERRY_AGENT = u'Mozilla/5.0 (BlackBerry; U; BlackBerry 9900; en) ' \
                   u'AppleWebKit/534.11+ (KHTML, like Gecko) Version/7.1.0.346 Mobile Safari/534.11+'
WINDOWS_PHONE_AGENT = u'Mozilla/5.0 (compatible; MSIE 9.0; Windows Phone OS 7.5; Trident/5.0; IEMobile/9.0)'
HEADERS = {
    u'HTTP_USER_AGENT': PC_AGENT,
}

PC_DATA = TestData(PC_AGENT, None, u'generic_web_browser', API_VERSION, 1452529268, True, False, {})

TEST_DATA = [
    PC_DATA,
    TestData(ANDROID_AGENT, None, u'lg_l160l_ver1', API_VERSION, 1452529268, True, True, {}),
    TestData(IPAD_AGENT, None, u'apple_ipad_ver1_sub9_1', API_VERSION, 1452529571, True, True, {}),
    TestData(IPHONE_AGENT, None, u'apple_iphone_ver8_4', API_VERSION, 1452529268, True, True, {}),
    TestData(WINDOWS_PHONE_AGENT, None, u'blackberry9900_ver1_subua71', API_VERSION, 1452529571, True, True, {}),
    TestData(None, HEADERS, u'generic_web_browser', API_VERSION, 1452529268, True, False, {}),
]

class DeviceMock(object):
    def __init__(self, apiVersion, mtime, id, device_claims_web_support, is_wireless_device, errors):
        self.apiVersion = apiVersion
        self.mtime = mtime
        self.id = id
        self.capabilities = Capabilities(device_claims_web_support, is_wireless_device)
        self.errors = errors

    def serialize(self):
        return {
            'apiVersion': self.apiVersion,
            'mtime': self.mtime,
            'id': self.id,
            'capabilities': self.capabilities.serialize(),
            'errors': self.errors,
        }

    def to_json(self):
        return binary_type(json.dumps(self.serialize()).encode())

    @classmethod
    def get_device(cls, mock_data):
        return cls(
            mock_data.apiVersion,
            mock_data.mtime,
            mock_data.id,
            mock_data.device_claims_web_support,
            mock_data.is_wireless_device,
            mock_data.errors
        )


class Capabilities(object):
    def __init__(self, device_claims_web_support, is_wireless_device):
        self.device_claims_web_support = device_claims_web_support
        self.is_wireless_device = is_wireless_device

    def serialize(self):
        return {
            'device_claims_web_support': self.device_claims_web_support,
            'is_wireless_device': self.is_wireless_device,
        }


def configure_wurflcloud_mock(mock, user_agent, content, url, status_code):
    mock.get(
        url,
        content=content,
        status_code=status_code,
        request_headers={
            u'X-Cloud-Client': XCLOUD_CLIENT_HEADER,
            u'User-Agent': user_agent,
        }
    )


def exception_callback(request, context):
    raise RequestException


class CacheStub(NullCache):
    def get_device(self, device_id, do_stats=True):
        return {
            u'errors': {},
            u'capabilities': {u'device_claims_web_support': True},
            u'apiVersion': u'WurflCloud 1.5.0.3',
            u'user_agent': u'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) '
                           u'Ubuntu Chromium/44.0.2403.89 Chrome/44.0.2403.89 Safari/537.36',
            u'mtime': 1452529268,
            u'id': u'generic_web_browser'
        }


class ExpiredCacheStub(CacheStub):
    @property
    def age(self):
        return maxsize


class TestCloudCoverage():
    def setup(self):
        self.wurfl_config = utils.load_config(u'requests_mock_cloud_response_config')

    @requests_mock.mock()
    def test_get_device_from_cloud_coverage(self, mock):
        cloud = Cloud(self.wurfl_config, NullCache())
        url = u'http://api.wurflcloud.com/v1/json/search:(device_claims_web_support,is_wireless_device)'
        for data in TEST_DATA:
            configure_wurflcloud_mock(mock,  data.user_agent, DeviceMock.get_device( data).to_json(), url, 200)

            cloud(
                data.user_agent,
                data.headers,
                capabilities=[u'device_claims_web_support', u'is_wireless_device']
            )

    def test_get_device_from_cache_coverage(self):
        cloud = Cloud(self.wurfl_config, CacheStub())

        cloud(PC_AGENT, HEADERS, capabilities=[u'device_claims_web_support'])

    @requests_mock.mock()
    def test_get_device_with_missing_capabilities_coverage(self, mock):
        cloud = Cloud(self.wurfl_config, CacheStub())
        url = u'http://api.wurflcloud.com/v1/json/search:(is_wireless_device)'
        configure_wurflcloud_mock(mock, PC_DATA.user_agent, DeviceMock.get_device(PC_DATA).to_json(), url, 200)

        cloud(PC_AGENT, HEADERS, capabilities=[u'device_claims_web_support', u'is_wireless_device'])

    @raises(LookupError)
    @requests_mock.mock()
    def test_response_status_is_not_ok_coverage(self, mock):
        cloud = Cloud(self.wurfl_config, NullCache())
        url = u'http://api.wurflcloud.com/v1/json/'
        configure_wurflcloud_mock(mock, PC_DATA.user_agent, DeviceMock.get_device(PC_DATA).to_json(), url, 404)

        cloud(PC_AGENT, HEADERS)

    @raises(LookupError)
    def test_user_agent_and_headers_is_none_coverage(self):
        cloud = Cloud(self.wurfl_config, utils.get_cache(self.wurfl_config))

        cloud(None, None)

    @raises(LookupError)
    @requests_mock.mock()
    def test_request_exception_coverage(self, mock):
        cloud = Cloud(self.wurfl_config, ExpiredCacheStub())
        url = u'http://api.wurflcloud.com/v1/json/search:(is_wireless_device)'
        configure_wurflcloud_mock(mock, PC_DATA.user_agent, exception_callback, url, 200)

        cloud(PC_AGENT, HEADERS, capabilities=[u'device_claims_web_support', u'is_wireless_device'])
