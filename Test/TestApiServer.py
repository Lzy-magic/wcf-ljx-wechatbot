import unittest
import json
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
import os
import sys

import requests

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from servers.api_server import GaoDeApi, BeikeApi, LLMTaskApi, LLMResponseApi, ApiServer
from utils.common import returnConfigData, downloadFile, encode_image
from utils.prompt import sys_base_prompt, sys_birthday_wish, sys_weather_report, sys_intention_rec, sys_route_plan, sys_poi_rec, sys_poi_ext, sys_video_gen, sys_room_summary

class TestApiServer(unittest.TestCase):

    def setUp(self):
        self.config_data = {
            'apiServer': {
                'gaoDeKey': 'test_gaode_key',
                'beike_db_api': 'http://test.com/beike',
                'beike_query_district': ['district1', 'district2'],
                'alKey': 'test_al_key',
                'alApi': 'http://test.com/al',
                'hzKey': 'test_hz_key',
                'hzApi': 'http://test.com/hz',
                'yuanqiToken': 'test_yuanqi_token',
                'yuanqiAssistant': 'test_yuanqi_assistant',
                'yuanqiUser': 'test_yuanqi_user',
                'imgRenderKey': 'test_img_render_key',
                'imgRenderApi': 'http://test.com/img_render',
                'dpfishApi': 'http://test.com/dpfish',
                'dpKey': 'test_dp_key',
                'dpWxVideoApi': 'http://test.com/dpwxvideo'
            },
            'llmServer': {
                'dify_api_url': 'http://test.com/dify',
                'dify_search_key': 'test_dify_search_key',
                'dify_image_key': 'test_dify_image_key',
                'model_name_list': ['model1', 'model2']
            },
            'systemConfig': {
                'robotName': 'TestBot'
            }
        }

        # Patch returnConfigData to return the test config data
        self.return_config_data_patch = patch('servers.api_server.returnConfigData', return_value=self.config_data)
        self.return_config_data_mock = self.return_config_data_patch.start()

        self.gaode_api = GaoDeApi()
        self.beike_api = BeikeApi()
        self.llm_task_api = LLMTaskApi()
        self.llm_response_api = LLMResponseApi()
        self.api_server = ApiServer()

    def tearDown(self):
        self.return_config_data_patch.stop()

    # GaoDeApi Tests
    @patch('servers.api_server.requests.get')
    def test_get_api_response_success(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'status': '1'}
        mock_get.return_value = mock_response
        
        url = "https://restapi.amap.com/v3/geocode/geo"
        params = {"address": "上海", "city": "上海", "key": self.config_data['apiServer']['gaoDeKey']}
        result = self.gaode_api.get_api_response(url, params)
        self.assertEqual(result, {'status': '1'})

    @patch('servers.api_server.requests.get')
    def test_get_api_response_failure(self, mock_get):
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = requests.exceptions.RequestException("API Error")
        mock_get.return_value = mock_response

        url = "https://restapi.amap.com/v3/geocode/geo"
        params = {"address": "上海", "city": "上海", "key": self.config_data['apiServer']['gaoDeKey']}
        result = self.gaode_api.get_api_response(url, params)
        self.assertIsNone(result)

    @patch('servers.api_server.GaoDeApi.get_api_response')
    def test_get_adcode(self, mock_get_api_response):
        mock_get_api_response.return_value = {'status': '1', 'geocodes': [{'adcode': '310000'}]}
        result = self.gaode_api.get_adcode(address='上海')
        self.assertEqual(result, {'status': '1', 'geocodes': [{'adcode': '310000'}]})

    @patch('servers.api_server.GaoDeApi.get_adcode')
    @patch('servers.api_server.GaoDeApi.get_api_response')
    def test_get_weather_with_address(self, mock_get_api_response, mock_get_adcode):
        mock_get_adcode.return_value = {'status': '1', 'geocodes': [{'adcode': '310101'}]}
        mock_get_api_response.return_value = {'status': '1', 'forecasts': [{'casts': [{'dayweather': 'Sunny'}]}]}
        result = self.gaode_api.get_weather(address='上海', extensions='all')
        self.assertEqual(result, {'status': '1', 'forecasts': [{'casts': [{'dayweather': 'Sunny'}]}]})
        mock_get_adcode.assert_called_with(address='上海')
        mock_get_api_response.assert_called_with(
            self.gaode_api.url + "weather/weatherInfo",
            {'key': self.gaode_api.key, 'city': '310101', 'extensions': 'all'}
        )

    @patch('servers.api_server.GaoDeApi.get_api_response')
    def test_get_weather_with_adcode(self, mock_get_api_response):
        mock_get_api_response.return_value = {'status': '1', 'forecasts': [{'casts': [{'dayweather': 'Sunny'}]}]}
        result = self.gaode_api.get_weather(adcode='310101', extensions='all')
        self.assertEqual(result, {'status': '1', 'forecasts': [{'casts': [{'dayweather': 'Sunny'}]}]})
        mock_get_api_response.assert_called_with(
            self.gaode_api.url + "weather/weatherInfo",
            {'key': self.gaode_api.key, 'city': '310101', 'extensions': 'all'}
        )

    @patch('servers.api_server.GaoDeApi.get_adcode')
    def test_get_weather_no_adcode(self, mock_get_adcode):
        mock_get_adcode.return_value = {'status': '0'}
        result = self.gaode_api.get_weather(address='unknown')
        self.assertIsNone(result)

    @patch('servers.api_server.GaoDeApi.get_adcode')
    def test_get_address(self, mock_get_adcode):
        mock_get_adcode.return_value = {'status': '1', 'geocodes': [{'location': '120.0,30.0'}]}
        result = self.gaode_api.get_address(origin='上海')
        self.assertEqual(result, {'location': '120.0,30.0'})

    @patch('servers.api_server.GaoDeApi.get_adcode')
    def test_get_address_ret_city(self, mock_get_adcode):
        mock_get_adcode.return_value = {'status': '1', 'geocodes': [{'location': '120.0,30.0', 'city': '上海'}]}
        result = self.gaode_api.get_address(origin='上海', ret_city=True)
        self.assertEqual(result, {'location': '120.0,30.0', 'city': '上海'})

    @patch('servers.api_server.GaoDeApi.get_address')
    @patch('servers.api_server.GaoDeApi.get_api_response')
    def test_get_driving(self, mock_get_api_response, mock_get_address):
        mock_get_address.side_effect = [{'location': '120.0,30.0'}, {'location': '121.0,31.0'}]
        mock_get_api_response.return_value = {'status': '1', 'route': {'taxi_cost': 30}}
        result = self.gaode_api.get_driving(origin='上海', destination='杭州')
        self.assertEqual(result, {'status': '1', 'route': {'taxi_cost': 30}})

    @patch('servers.api_server.GaoDeApi.get_address')
    def test_get_driving_no_address(self, mock_get_address):
        mock_get_address.return_value = None
        result = self.gaode_api.get_driving(origin='unknown', destination='unknown')
        self.assertIsNone(result)

    @patch('servers.api_server.GaoDeApi.get_address')
    @patch('servers.api_server.GaoDeApi.get_api_response')
    def test_get_walking(self, mock_get_api_response, mock_get_address):
        mock_get_address.side_effect = [{'location': '120.0,30.0'}, {'location': '121.0,31.0'}]
        mock_get_api_response.return_value = {'status': '1', 'route': {'paths': [{'distance': 1000, 'cost': {'duration': 600}, 'steps': []}]}}
        result = self.gaode_api.get_walking(origin='上海', destination='杭州')
        self.assertEqual(result, {'status': '1', 'route': {'paths': [{'distance': 1000, 'cost': {'duration': 600}, 'steps': []}]}})

    @patch('servers.api_server.GaoDeApi.get_address')
    def test_get_walking_no_address(self, mock_get_address):
        mock_get_address.return_value = None
        result = self.gaode_api.get_walking(origin='unknown', destination='unknown')
        self.assertIsNone(result)

    @patch('servers.api_server.GaoDeApi.get_address')
    @patch('servers.api_server.GaoDeApi.get_api_response')
    def test_get_bicycling(self, mock_get_api_response, mock_get_address):
        mock_get_address.side_effect = [{'location': '120.0,30.0'}, {'location': '121.0,31.0'}]
        mock_get_api_response.return_value = {'status': '1', 'route': {'paths': [{'distance': 1000, 'duration': 600, 'steps': []}]}}
        result = self.gaode_api.get_bicycling(origin='上海', destination='杭州')
        self.assertEqual(result, {'status': '1', 'route': {'paths': [{'distance': 1000, 'duration': 600, 'steps': []}]}})

    @patch('servers.api_server.GaoDeApi.get_address')
    def test_get_bicycling_no_address(self, mock_get_address):
        mock_get_address.return_value = None
        result = self.gaode_api.get_bicycling(origin='unknown', destination='unknown')
        self.assertIsNone(result)

    @patch('servers.api_server.GaoDeApi.get_adcode')
    @patch('servers.api_server.GaoDeApi.get_address')
    @patch('servers.api_server.GaoDeApi.get_api_response')
    def test_get_bus(self, mock_get_api_response, mock_get_address, mock_get_adcode):
        mock_get_address.side_effect = [{'location': '120.0,30.0', 'city': '上海'}, {'location': '121.0,31.0', 'city': '杭州'}]
        mock_get_adcode.side_effect = [{'status': '1', 'geocodes': [{'citycode': '021'}]}, {'status': '1', 'geocodes': [{'citycode': '0571'}]}]
        mock_get_api_response.return_value = {'status': '1', 'route': {'distance': 2000}}
        result = self.gaode_api.get_bus(origin='上海', destination='杭州')
        self.assertEqual(result, {'status': '1', 'route': {'distance': 2000}})

    @patch('servers.api_server.GaoDeApi.get_address')
    def test_get_bus_no_address(self, mock_get_address):
        mock_get_address.return_value = None
        result = self.gaode_api.get_bus(origin='unknown', destination='unknown')
        self.assertIsNone(result)

    @patch('servers.api_server.GaoDeApi.get_adcode')
    def test_get_bus_no_citycode(self, mock_get_adcode):
        mock_get_adcode.return_value = {'status': '0'}
        self.gaode_api.get_address = MagicMock(return_value={'location': 'test', 'city': 'test'})
        result = self.gaode_api.get_bus(origin='unknown', destination='unknown')
        self.assertIsNone(result)

    @patch('servers.api_server.GaoDeApi.get_adcode')
    @patch('servers.api_server.GaoDeApi.get_api_response')
    def test_get_poi_keyword(self, mock_get_api_response, mock_get_adcode):
        mock_get_adcode.return_value = {'status': '1', 'geocodes': [{'adcode': '310101'}]}
        mock_get_api_response.return_value = {'status': '1', 'pois': []}
        result = self.gaode_api.get_poi_keyword(keyword='餐厅', region='上海')
        self.assertEqual(result, {'status': '1', 'pois': []})

    @patch('servers.api_server.GaoDeApi.get_adcode')
    @patch('servers.api_server.GaoDeApi.get_api_response')
    def test_get_poi_around(self, mock_get_api_response, mock_get_adcode):
        mock_get_adcode.return_value = {'status': '1', 'geocodes': [{'adcode': '310101', 'location': '120.0,30.0'}]}
        mock_get_api_response.return_value = {'status': '1', 'pois': []}
        result = self.gaode_api.get_poi_around(keyword='餐厅', region='上海')
        self.assertEqual(result, {'status': '1', 'pois': []})

    # BeikeApi Tests
    @patch('servers.api_server.requests.get')
    def test_send_beike(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [{'house_id': '123', 'biz_circle': 'test', 'community_name': 'test', 'square': 100, 'total_price': 500}]
        mock_get.return_value = mock_response
        self.beike_api.get_statistical_week = MagicMock(return_value='')
        self.beike_api.get_statistical_mounth = MagicMock(return_value='')
        texts = self.beike_api.send_beike()
        self.assertTrue(isinstance(texts, list))

    @patch('servers.api_server.requests.get')
    def test_send_beike_no_data(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = []
        mock_get.return_value = mock_response
        self.beike_api.get_statistical_week = MagicMock(return_value='')
        self.beike_api.get_statistical_mounth = MagicMock(return_value='')
        texts = self.beike_api.send_beike()
        self.assertTrue(isinstance(texts, list))

    def test_get_statistical_data(self):
        houses = [{'community_name': 'A', 'square': 100, 'total_price': 500}, {'community_name': 'A', 'square': 120, 'total_price': 600}, {'community_name': 'B', 'square': 80, 'total_price': 400}]
        items = self.beike_api.get_statistical_data(houses)
        self.assertEqual(len(items), 2)
        self.assertEqual(items[0][0], 'A')
        self.assertEqual(items[1][0], 'B')

    @patch('servers.api_server.datetime')
    @patch('servers.api_server.requests.get')
    def test_get_statistical_week(self, mock_get, mock_datetime):
        # Mock today as Monday
        today = datetime(2024, 1, 8)
        mock_datetime.now.return_value = today
    
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [{'community_name': 'A', 'square': 100, 'total_price': 500}]
        mock_get.return_value = mock_response
    
        text = self.beike_api.get_statistical_week()
        self.assertNotEqual(text, '')

    @patch('servers.api_server.datetime')
    def test_get_statistical_week_not_monday(self, mock_datetime):
        # Mock today as Tuesday
        today = datetime(2024, 1, 9)
        mock_datetime.now.return_value = today
        text = self.beike_api.get_statistical_week()
        self.assertEqual(text, '')

    @patch('servers.api_server.datetime')
    @patch('servers.api_server.requests.get')
    def test_get_statistical_mounth(self, mock_get, mock_datetime):
        # Mock today as 1st of the month
        today = datetime(2024, 1, 1)
        mock_datetime.now.return_value = today
    
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [{'community_name': 'A', 'square': 100, 'total_price': 500}]
        mock_get.return_value = mock_response
    
        text = self.beike_api.get_statistical_mounth()
        self.assertNotEqual(text, '')

    @patch('servers.api_server.datetime')
    def test_get_statistical_mounth_not_first(self, mock_datetime):
        # Mock today as 2nd of the month
        today = datetime(2024, 1, 2)
        mock_datetime.now.return_value = today
        text = self.beike_api.get_statistical_mounth()
        self.assertEqual(text, '')

    # LLMTaskApi Tests
    @patch('servers.api_server.UniLLM')
    @patch('servers.api_server.GaoDeApi.get_weather')
    def test_getWeather(self, mock_get_weather, mock_unillm):
        mock_get_weather.return_value = {'forecasts': [{'casts': [{'dayweather': 'Sunny'}]}]}
        mock_unillm.return_value = 'Weather report'
        result = self.llm_task_api.getWeather()
        self.assertEqual(result, 'Weather report')

    @patch('servers.api_server.BeikeApi.send_beike')
    def test_getBeike(self, mock_send_beike):
        mock_send_beike.return_value = ['Beike data']
        result = self.llm_task_api.getBeike()
        self.assertEqual(result, ['Beike data'])

    @patch('servers.api_server.UniLLM')
    def test_getGoodNight(self, mock_unillm):
        mock_unillm.return_value = 'Good night message'
        result = self.llm_task_api.getGoodNight()
        self.assertEqual(result, 'Good night message')

    @patch('servers.api_server.UniLLM')
    def test_birthdayWish(self, mock_unillm):
        mock_unillm.return_value = 'Happy birthday'
        result = self.llm_task_api.birthdayWish(name='Test')
        self.assertEqual(result, 'Happy birthday')

    @patch('servers.api_server.UniLLM')
    def test_festivalWish(self, mock_unillm):
        mock_unillm.return_value = 'Happy festival'
        result = self.llm_task_api.festivalWish(festival='Test', room_name='TestRoom')
        self.assertEqual(result, 'Happy festival')

    @patch('servers.api_server.UniLLM')
    def test_roomWelcome(self, mock_unillm):
        mock_unillm.return_value = 'Welcome message'
        result = self.llm_task_api.roomWelcome(room_name='TestRoom', invitee='TestUser', index=1)
        self.assertEqual(result, '@TestUser Welcome message')

    @patch('servers.api_server.requests.post')
    def test_difySearch(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'answer': 'Dify search result'}
        mock_post.return_value = mock_response
        result = self.llm_task_api.difySearch(query='Test', user='TestUser')
        self.assertEqual(result, 'Dify search result')

    @patch('servers.api_server.requests.post')
    def test_difySearch_failure(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_post.return_value = mock_response
        result = self.llm_task_api.difySearch(query='Test', user='TestUser')
        self.assertEqual(result, 'AI 搜索引擎速率限制，请稍候再试')

    @patch('servers.api_server.downloadFile')
    @patch('servers.api_server.requests.post')
    def test_difyImage(self, mock_post, mock_downloadFile):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'answer': 'http://test.com/image.jpg', 'conversation_id': '123'}
        mock_post.return_value = mock_response
        mock_downloadFile.return_value = 'image_path'
        result = self.llm_task_api.difyImage(query='Test', user='TestUser')
        self.assertEqual(result, ('image_path', '123'))

    @patch('servers.api_server.downloadFile')
    @patch('servers.api_server.requests.post')
    def test_difyImage_failure(self, mock_post, mock_downloadFile):
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_post.return_value = mock_response
        result = self.llm_task_api.difyImage(query='Test', user='TestUser')
        self.assertEqual(result, ('', ''))

    @patch('servers.api_server.generate_video_sf')
    def test_genVid(self, mock_generate_video_sf):
        mock_generate_video_sf.return_value = 'video_path'
        result = self.llm_task_api.genVid(prompt='Test')
        self.assertEqual(result, 'video_path')

    @patch('servers.api_server.generate_article')
    @patch('servers.api_server.UniLLM')
    def test_genArticleSum(self, mock_unillm, mock_generate_article):
        mock_generate_article.return_value = {'content': 'Article content'}
        mock_unillm.return_value = 'Article summary'
        result = self.llm_task_api.genArticleSum(url='http://test.com')
        self.assertEqual(result, {'content': 'Article summary'})

    @patch('servers.api_server.generate_article')
    def test_genArticleSum_no_data(self, mock_generate_article):
        mock_generate_article.return_value = None
        result = self.llm_task_api.genArticleSum(url='http://test.com')
        self.assertIsNone(result)

    @patch('servers.api_server.BeautifulSoup')
    @patch('servers.api_server.requests.get')
    @patch('servers.api_server.UniLLM')
    def test_getGithubTrending(self, mock_unillm, mock_get, mock_beautifulsoup):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = '<html></html>'
        mock_get.return_value = mock_response

        mock_soup = MagicMock()
        mock_beautifulsoup.return_value = mock_soup
        mock_soup.find_all.return_value = []

        result = self.llm_task_api.getGithubTrending()
        self.assertEqual(result, '🔥本周GitHub热门项目🔥\n')

    @patch('servers.api_server.BeautifulSoup')
    @patch('servers.api_server.requests.get')
    def test_getGithubTrending_failure(self, mock_get, mock_beautifulsoup):
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_get.return_value = mock_response
        result = self.llm_task_api.getGithubTrending()
        self.assertEqual(result, '获取GitHub热门项目失败，请检查服务端日志')

    @patch('servers.api_server.UniLLM')
    def test_getRoomMessSummary(self, mock_unillm):
        mock_unillm.return_value = 'Room summary'
        result = self.llm_task_api.getRoomMessSummary(contents='Test')
        self.assertEqual(result, 'Room summary')

    # LLMResponseApi Tests
    def test_get_conversation_list(self):
        self.llm_response_api.conversation_list = {'chat1': [
            ((datetime.now() - timedelta(minutes=5)).strftime("%Y%m%d%H%M%S"), {"role": "user", "content": "Test"}),
            ((datetime.now() - timedelta(minutes=15)).strftime("%Y%m%d%H%M%S"), {"role": "user", "content": "Test"})
        ]}
        result = self.llm_response_api.get_conversation_list('chat1')
        self.assertEqual(len(result), 1)

    def test_updateMessage(self):
        self.llm_response_api.updateMessage(chatid='chat1', contents=['User message', 'Bot message'])
        self.assertTrue('chat1' in self.llm_response_api.conversation_list)

    @patch('servers.api_server.UniLLM')
    def test_intentionRec(self, mock_unillm):
        mock_unillm.return_value = 'Intention'
        result = self.llm_response_api.intentionRec(records=['Test'])
        self.assertEqual(result, 'Intention')

    @patch('servers.api_server.UniLLM')
    def test_generalResponse(self, mock_unillm):
        mock_unillm.return_value = 'General response'
        result = self.llm_response_api.generalResponse(messages=[{'role': 'user', 'content': 'Test'}], bot_name='TestBot')
        self.assertEqual(result, 'General response')

    @patch('servers.api_server.UniLLM')
    def test_generalResponse_no_response(self, mock_unillm):
        mock_unillm.return_value = None
        result = self.llm_response_api.generalResponse(messages=[{'role': 'user', 'content': 'Test'}], bot_name='TestBot')
        self.assertEqual(result, 'TestBot有点累了，稍候再试吧')

    @patch('servers.api_server.UniLLM')
    @patch('servers.api_server.GaoDeApi.get_weather')
    def test_weatherResponse(self, mock_get_weather, mock_unillm):
        mock_unillm.return_value = 'Shanghai'
        mock_get_weather.return_value = {'forecasts': [{'casts': [{'dayweather': 'Sunny'}]}]}
        mock_unillm.return_value = 'Weather response'
        result = self.llm_response_api.weatherResponse(user_content='Test', bot_name='TestBot')
        self.assertEqual(result, 'Weather response')

    @patch('servers.api_server.UniLLM')
    @patch('servers.api_server.GaoDeApi.get_weather')
    def test_weatherResponse_no_weather(self, mock_get_weather, mock_unillm):
        mock_unillm.return_value = 'Shanghai'
        mock_get_weather.return_value = None
        mock_unillm.return_value = 'General response'
        self.llm_response_api.generalResponse = MagicMock(return_value='General response')
        result = self.llm_response_api.weatherResponse(user_content='Test', bot_name='TestBot')
        self.assertEqual(result, 'General response')

    # @patch('servers.api_server.UniLLM')
    # @patch('servers.api_server.GaoDeApi.get_walking')
    # def test_pathResponse_walking(self, mock_get_walking, mock_unillm):
        # mock_unillm.return_value = 'Shanghai|Hangzhou'
        # mock_get_walking.return_value = {'route': {'paths': [{'distance': 1000, 'cost': {'duration': 600}, 'steps': []}]}}
        # mock_unillm.return_value = 'Path response'
        # result = self.llm_response_api.pathResponse(user_content='Test', intention='步行规划', bot_name='TestBot')
        # self.assertEqual(result, 'Path response')

    @patch('servers.api_server.UniLLM')
    @patch('servers.api_server.GaoDeApi.get_bicycling')
    def test_pathResponse_bicycling(self, mock_get_bicycling, mock_unillm):
        mock_unillm.return_value = 'Shanghai|Hangzhou'
        mock_get_bicycling.return_value = {'route': {'paths': [{'distance': 1000, 'duration': 600, 'steps': []}]}}
        mock_unillm.return_value = 'Path response'
        result = self.llm_response_api.pathResponse(user_content='Test', intention='骑行规划', bot_name='TestBot')
        self.assertEqual(result, 'Path response')

    @patch('servers.api_server.UniLLM')
    @patch('servers.api_server.GaoDeApi.get_driving')
    def test_pathResponse_driving(self, mock_get_driving, mock_unillm):
        mock_unillm.return_value = 'Shanghai|Hangzhou'
        mock_get_driving.return_value = {'route': {'taxi_cost': 30, 'paths': [{'distance': 1000, 'steps': []}]}}
        mock_unillm.return_value = 'Path response'
        result = self.llm_response_api.pathResponse(user_content='Test', intention='驾车规划', bot_name='TestBot')
        self.assertEqual(result, 'Path response')