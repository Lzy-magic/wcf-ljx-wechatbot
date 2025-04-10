import os
import json
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from utils.common import logger, returnConfigData, downloadFile, encode_image
from utils.prompt import sys_base_prompt, sys_birthday_wish, sys_weather_report, sys_intention_rec, sys_route_plan, sys_poi_rec, sys_poi_ext, sys_video_gen, sys_room_summary, sys_room_rank_summary
from utils.llm import UniLLM, generate_video_sf, generate_article
from servers.db_server import DbMsgServer

unillm = UniLLM()

class GaoDeApi:
    def __init__(self):
        """
        高德地图api接口
        """
        self.url = "https://restapi.amap.com/v3/"
        self.key = returnConfigData()['apiServer']['gaoDeKey']
        self.dms = DbMsgServer()
    
    def get_api_response(self, url, params):
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()  # 检查请求是否成功
            data = response.json()  # 解析JSON响应
            return data
        except requests.exceptions.RequestException as e:
            logger.error(f"高德api接口请求失败: {e}")
            return None

    def get_adcode(self, address='', city=''):
        url = self.url + "geocode/geo"
        if not address:
            address = city
        params = {
            "address": address,
            "city": city,
            "key": self.key
        }
        data = self.get_api_response(url, params)
        return data

    def get_weather(self, address='', adcode='', extensions='all'):
        url = self.url + "weather/weatherInfo"
        if address:
            res = self.get_adcode(address=address)
            if res and res.get('status') == '1':
                adcode = res.get('geocodes')[0].get('adcode')
        if not adcode:
            return None
        params = {
            "key": self.key,
            "city": adcode,
            "extensions": extensions
        }
        data = self.get_api_response(url, params)
        return data
        
    def get_address(self, origin='', ret_city=False):
        res = self.get_adcode(address=origin)
        data = {}
        if res and res.get('status') == '1':
            data['location'] = res.get('geocodes')[0].get('location')
            if ret_city:
                data['city'] = res.get('geocodes')[0].get('city')
        return data

    def get_driving(self, origin='', destination='', strategy=32):
        url = "https://restapi.amap.com/v5/direction/driving"
        data_origin = self.get_address(origin)
        data_destination = self.get_address(destination)
        if not (data_origin and data_destination):
            return None
        params = {
            "key": self.key,
            "origin": data_origin['location'],
            "destination": data_destination['location'],
            "strategy": strategy
        }
        data = self.get_api_response(url, params)
        return data

    def get_walking(self, origin='', destination='', alternative_route=1):
        url = "https://restapi.amap.com/v5/direction/walking"
        data_origin = self.get_address(origin)
        data_destination = self.get_address(destination)
        if not (data_origin and data_destination):
            return None
        params = {
            "key": self.key,
            "origin": data_origin['location'],
            "destination": data_destination['location'],
            "alternative": alternative_route
        }
        data = self.get_api_response(url, params)
        return data

    def get_bicycling(self, origin='', destination='', alternative_route=1):
        url = "https://restapi.amap.com/v5/direction/bicycling"
        data_origin = self.get_address(origin)
        data_destination = self.get_address(destination)
        if not (data_origin and data_destination):
            return None
        params = {
            "key": self.key,
            "origin": data_origin['location'],
            "destination": data_destination['location'],
            "alternative": alternative_route
        }
        data = self.get_api_response(url, params)
        return data

    def get_bus(self, origin='', destination='', strategy=0, AlternativeRoute=1):
        url = "https://restapi.amap.com/v5/direction/transit/integrated"
        data_origin = self.get_address(origin, ret_city=True)
        data_destination = self.get_address(destination, ret_city=True)
        if not (data_origin and data_destination):
            return None
        res = self.get_adcode(city=data_origin['city'])
        c1_code = res.get('geocodes')[0].get('citycode') if res and res.get('status') == '1' else ''
        res = self.get_adcode(city=data_destination['city'])
        c2_code = res.get('geocodes')[0].get('citycode') if res and res.get('status') == '1' else ''
        if not c1_code or not c2_code:
            return None
        params = {
            "key": self.key,
            "origin": data_origin['location'],
            "destination": data_destination['location'],
            "city1": c1_code,
            "city2": c2_code,
            "strategy": strategy,
            "AlternativeRoute": AlternativeRoute
        }
        data = self.get_api_response(url, params)
        return data

    def get_poi_keyword(self, keyword='', region='', city_limit=False):
        url = "https://restapi.amap.com/v5/place/text"
        res = self.get_adcode(address=region)
        adcode = res.get('geocodes')[0].get('adcode') if res and res.get('status') == '1' else ''
        city_limit = True if adcode else False
        params = {
            "key": self.key,
            "keywords": keyword,
            "region": adcode,
            "citylimit": city_limit
        }
        data = self.get_api_response(url, params)
        return data

    def get_poi_around(self, keyword='', region='', city_limit=False):
        url = "https://restapi.amap.com/v5/place/around"
        res = self.get_adcode(address=region)
        adcode = res.get('geocodes')[0].get('adcode') if res and res.get('status') == '1' else ''
        location = res.get('geocodes')[0].get('location') if res and res.get('status') == '1' else ''
        city_limit = True if adcode else False
        params = {
            "key": self.key,
            "keywords": keyword,
            "location": location,
            "region": adcode,
            "citylimit": city_limit
        }
        data = self.get_api_response(url, params)
        return data

class BeikeApi:
    def __init__(self):
        config = returnConfigData()['apiServer']
        self.db_base_url = config['beike_db_api']
        self.query_district = config['beike_query_district']

    def send_beike(self,):
        date_ho = (datetime.now() - timedelta(days=2))
        date_de = (datetime.now() - timedelta(days=18))
        texts = []
        for district in self.query_district:
            response = requests.get(f"{self.db_base_url}/houses/", params={'upload_time': date_ho.strftime('%Y.%m.%d'), 'district': district})
            if response.status_code == 200:
                text = f"🔥{date_ho.strftime('%Y.%m.%d')}星期{date_ho.weekday()+1} {district} 新增挂牌🔥\n"
                houses = response.json()
                if len(houses) > 0:
                    for i, house in enumerate(houses):
                        text += f"{i+1}. {house['house_id']} {house['biz_circle']} {house['community_name']} {int(house['square'])}平 {int(house['total_price'])}万\n"
                else:
                    text += '暂无数据'
                texts.append(text)
        for district in self.query_district:
            response = requests.get(f"{self.db_base_url}/deals/", params={'deal_date': date_de.strftime('%Y.%m.%d'), 'district': district})
            if response.status_code == 200:
                text = f"🔥{date_de.strftime('%Y.%m.%d')}星期{date_de.weekday()+1} {district} 成交🔥\n"
                deals = response.json()
                if len(deals) > 0:
                    for i, house in enumerate(deals):
                        text += f"{i+1}. {house['house_id']} {house['community_name']} {int(house['square'])}平 成交{int(house['total_price'])}万 挂牌{int(house['up_price'])}万 单价{int(house['unit_price'])}\n"
                else:
                    text += '暂无数据'
                texts.append(text)

        text = self.get_statistical_week(isDeal=False)
        if text:
            texts.append(text)
        text = self.get_statistical_week(isDeal=True)
        if text:
            texts.append(text)
        text = self.get_statistical_mounth(isDeal=False)
        if text:
            texts.append(text)
        text = self.get_statistical_mounth(isDeal=True)
        if text:
            texts.append(text)
        return texts

    def get_statistical_data(self, houses, isDeal=False):
        data_dict = dict()
        for house in houses:
            community_name = house['community_name']
            if community_name not in data_dict:
                data_dict[community_name] = [0, 0, 0]
            data_dict[community_name][0] += 1
            data_dict[community_name][1] += int(house['square'])
            data_dict[community_name][2] += int(house['total_price']) if not isDeal else int(house['total_price'])
        items = sorted(data_dict.items(), key=lambda x: x[1][0], reverse=True)
        return items

    def get_statistical_week(self, isDeal=False):
        delta_days = 18 if isDeal else 2
        rep_text = '成交' if isDeal else '挂牌'
        rep_uri = 'deals' if isDeal else 'houses'
        rep_par = 'deal_date' if isDeal else 'upload_time'
        sta_num = 2 if isDeal else 3
        date_ho = datetime.now() - timedelta(days=delta_days)
        text = ''
        if date_ho.weekday() == 0:
            week_number = date_ho.isocalendar()[1] - 1
            houses = []
            for i in range(1, 8):
                date_cur = (date_ho - timedelta(days=i)).strftime('%Y.%m.%d')
                year = date_cur.split('.')[0]
                response = requests.get(f"{self.db_base_url}/{rep_uri}/", params={rep_par: date_cur})
                if response.status_code == 200:
                    houses.extend(response.json())
            start_date = (date_ho - timedelta(days=7)).strftime('%m.%d')
            end_date = (date_ho - timedelta(days=1)).strftime('%m.%d')
            text += f"🔥{year}年第{week_number}周({start_date}-{end_date}){rep_text}{len(houses)}套🔥\n"
            items = self.get_statistical_data(houses, isDeal)
            for item in items:
                if item[1][0] < sta_num:
                    break
                text += f"- {item[0]}：{item[1][0]}套，均价{item[1][2]/item[1][1]:.2f}万/平\n"
            for i in range(1, sta_num):
                items = [item for item in items if item[1][0] == i]
                text += f"- {rep_text}{i}套的小区：{len(items)}个\n"
        return text

    def get_statistical_mounth(self, isDeal=False):
        delta_days = 18 if isDeal else 2
        rep_text = '成交' if isDeal else '挂牌'
        rep_uri = 'deals' if isDeal else 'houses'
        rep_par = 'deal_date' if isDeal else 'upload_time'
        sta_num = 3 if isDeal else 10
        date_ho = datetime.now() - timedelta(days=delta_days)
        text = ''
        if date_ho.strftime('%d') == '01':
            month = (date_ho - timedelta(days=1)).strftime('%m')
            year = (date_ho - timedelta(days=1)).strftime('%Y')
            houses = []
            for i in range(1, 31):
                date_cur = f'{year}.{month}.{i:02d}'
                response = requests.get(f"{self.db_base_url}/{rep_uri}/", params={rep_par: date_cur})
                if response.status_code == 200:
                    houses.extend(response.json())
            text += f"🔥{year}年{month}月{rep_text}{len(houses)}套🔥\n"
            items = self.get_statistical_data(houses, isDeal)
            for item in items:
                if item[1][0] < sta_num:
                    break
                text += f"- {item[0]}：{item[1][0]}套，均价{item[1][2]/item[1][1]:.2f}万/平\n"
            for i in range(1, sta_num):
                items = [item for item in items if item[1][0] == i]
                text += f"- {rep_text}{i}套的小区：{len(items)}个"
        return text

class LLMTaskApi:
    def __init__(self):
        self.gaoDeApi = GaoDeApi()
        self.beikeApi = BeikeApi()
        config = returnConfigData()['llmServer']
        self.dify_api_url = config['dify_api_url']
        self.dify_search_key = config['dify_search_key']
        self.dify_image_key = config['dify_image_key']
        self.model_name_list = config['model_name_list']

    def getWeather(self, address='上海杨浦区'):
        wea_cast = self.gaoDeApi.get_weather(address, extensions='all')
        forecasts = wea_cast['forecasts'][0]['casts']
        today_cast = json.dumps(forecasts[0], ensure_ascii=False)
        future_cast = json.dumps(forecasts[1:], ensure_ascii=False)
        messages = [
                    {'role': 'system', 'content': sys_weather_report},
                    {'role': 'user', 'content': f'地名：{address}；今日天气：{today_cast}；未来三天：{future_cast}'},
                ]
        result = unillm(['glm4-9b', 'glm4-flash'] + self.model_name_list, messages=messages)
        return result
    
    def getBeike(self,):
        texts = self.beikeApi.send_beike()
        return texts
    
    def getGoodNight(self):
        messages = [
                {'role': 'system', 'content': sys_base_prompt},
                {'role': 'user', 'content': '夜深了，给大家发送一份晚安祝福，提醒不要熬夜，早睡早起等等，文风轻松活泼，不超过50字。直接给出晚安祝福即可，不要回答“好的”'}
            ]
        result = unillm(self.model_name_list, messages=messages, temperature=0.9)
        return result.strip()
    
    def birthdayWish(self, name, solar='', lunar=''):
        messages = [
                {'role': 'system', 'content': sys_birthday_wish},
                {'role': 'user', 'content': f'阳历{solar}，阴历{lunar}，人物{name}'},
            ]
        result = unillm(self.model_name_list, messages=messages)
        return result.strip()
    
    def festivalWish(self, festival, room_name):
        robot_name = returnConfigData()['systemConfig']['robotName']
        messages = [
                {'role': 'system', 'content': f'你是群管理员{robot_name}，明天就是<节日名称>，给<群名称>的小伙伴发一段节日祝福，预祝大家节日快乐，文风轻松活泼一些'},
                {'role': 'user', 'content': f'节日名称：{festival}，群名称：{room_name}'},
            ]
        result = unillm(self.model_name_list, messages=messages)
        return result.strip()

    def roomWelcome(self, room_name, invitee, index):
        text = f'你现在是<{room_name}>群的管理员，<{invitee}>是刚加入群的第{index}位新朋友，结合新朋友的昵称，写一段欢迎词，文风轻松幽默，记得在合适的位置提到第{index}位，不超过100字。'
        messages = [{'role': 'user', 'content': text},]
        result = unillm(self.model_name_list, messages=messages, temperature=0.8)
        return f'@{invitee} {result.strip()}'

    def roomWelcomePrompmt(self, room_name, invitee, index):
        messages = returnConfigData()['prompt']['welcome']
        return f'@{invitee} {messages.strip()}'

    def difySearch(self, query, user):
        data = {
            "api_key": self.dify_search_key, 
            "query": query,
            "user": user
        }
        response = requests.post(self.dify_api_url, json=data)
        if response.status_code == 200:
            return response.json()['answer']
        else:
            return 'AI 搜索引擎速率限制，请稍候再试'
    
    def difyImage(self, query='', user='', conversation_id=''):
        data = {
            "api_key": self.dify_image_key, 
            "query": query,
            "user": user,
            "conversation_id": conversation_id
        }
        response = requests.post(self.dify_api_url, json=data)
        if response.status_code == 200:
            url = response.json()['answer']
            img_path = downloadFile(url, prefix='difyImgGen_')
            return img_path, response.json()['conversation_id']
        else:
            return '', conversation_id

    def genVid(self, prompt):
        vid_path = generate_video_sf(prompt=prompt)
        return vid_path
    
    def genArticleSum(self, url):
        data = generate_article(url)
        if data:
            messages = [
                {'role': 'system', 'content': '一句话给出这篇文章的摘要'},
                {'role': 'user', 'content': data['content']},
            ]
            res = unillm(self.model_name_list, messages=messages)
            data['content'] = res.strip()
        return data

    def getGithubTrending(self,):
        response = requests.get('https://github.com/trending?since=weekly')
        text = '🔥本周GitHub热门项目🔥\n'
        prefix = 'https://github.com'
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            repo_cards = soup.find_all('article', class_='Box-row')
            for i, repo in enumerate(repo_cards[:5]):
                name = repo.find('h2', class_='h3 lh-condensed').find('a')['href']
                desc = repo.find('p', class_='col-9 color-fg-muted my-1 pr-4').text.strip()
                try:
                    lang = repo.find('span', class_='d-inline-block ml-0 mr-3').text.strip()
                except:
                    lang = 'Unknown'
                star_total = repo.find('a', class_='Link Link--muted d-inline-block mr-3').text.strip()
                star_week = repo.find('span', class_='d-inline-block float-sm-right').text.strip().replace(' stars this week', '')
                messages = [{'role': 'user', 'content': f'请用一句中文简述这个项目：{desc}'},]
                res = unillm(self.model_name_list, messages=messages)
                text += f'{i+1}. {prefix + name}\n - 项目简介：{res}\n - 语言：{lang}\n - 总Star: {star_total}\n - 周Star: {star_week}\n'
        else:
            text = '获取GitHub热门项目失败，请检查服务端日志'
            logger.error(f'获取GitHub热门项目失败，状态码：{response.status_code}')
        return text

    def getRoomMessSummary(self, contents):
        messages = [
            {'role': 'system', 'content': sys_room_summary},
            {'role': 'user', 'content': contents},
        ]
        result = unillm(['glm4-9b'] + self.model_name_list, messages=messages)
        return result
            
class LLMResponseApi:
    def __init__(self):
        self.gaoDeApi = GaoDeApi()
        self.conversation_list = {}
        self.model_name_list = returnConfigData()['llmServer']['model_name_list']
    
    def get_conversation_list(self, chatid):
        # 清除缓存
        start_time = (datetime.now() - timedelta(hours=0, minutes=10)).strftime("%Y%m%d%H%M%S")
        conversation_list = self.conversation_list.get(chatid, [])
        conversation_list = [item for item in conversation_list if item[0] >= start_time]
        self.conversation_list[chatid] = conversation_list
        return conversation_list
    
    def updateMessage(self, chatid, contents):
        now_time = str(datetime.now().strftime("%Y%m%d%H%M%S"))
        conversation_list = self.conversation_list.get(chatid, [])
        conversation_list.append((now_time, {"role": "user", "content": contents[0]}))
        conversation_list.append((now_time, {"role": "assistant", "content": contents[1]}))
        self.conversation_list[chatid] = conversation_list
    
    def intentionRec(self, records):
        messages = [
            {'role': 'system', 'content': sys_intention_rec},
            {'role': 'user', 'content': json.dumps(records, ensure_ascii=False)}
        ]
        res = unillm(self.model_name_list, messages=messages)
        return res.strip()
    
    def generalResponse(self, messages, bot_name):
        time_mk = f"\n当需要回答时间时请直接参考回复：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        messages = [{'role': 'system', 'content': sys_base_prompt + time_mk}] + messages
        res = unillm(self.model_name_list, messages=messages)
        return res if res else f'{bot_name}有点累了，稍候再试吧'

    def weatherResponse(self, user_content, bot_name):
        messages = [{'role': 'user', 'content': f'{user_content}，用户要查询某地天气信息，请从这段聊天记录中提取出地址信息，只需回答地址'}]
        res_address = unillm(model_name_list=['glm4-flash'], messages=messages)
        wea_cast = self.gaoDeApi.get_weather(res_address, extensions='all')
        if not wea_cast:
            messages = [{'role': 'user', 'content': user_content}]
            response = self.generalResponse(messages, bot_name)
            return response
        forecasts = wea_cast['forecasts'][0]['casts']
        today_cast = json.dumps(forecasts[0], ensure_ascii=False)
        future_cast = json.dumps(forecasts[1:], ensure_ascii=False)
        messages = [
            {'role': 'system', 'content': sys_weather_report},
            {'role': 'user', 'content': f'地名：{res_address}；今日天气：{today_cast}；未来三天：{future_cast}；聊天记录：{user_content}'},
        ]
        res = unillm(self.model_name_list, messages=messages)
        return res if res else f'{bot_name}有点累了，稍候再试吧'

    def pathResponse(self, user_content, intention, bot_name):
        # 提取起点和终点
        messages = [{'role': 'user', 'content': f'{user_content}，用户要进行路径规划，请从这段聊天记录中提取详细的起点和终点信息，并以以下格式回复：起点|终点。请不要包含其他任何内容'}]
        res_address = unillm(['glm4-9b']+self.model_name_list, messages=messages)
        logger.info(f'提取的地址信息：{res_address}')
        try:
            start, end = res_address.split('|')
        except:
            return f'{intention}失败，请检查起点和终点是否正确'
        logger.info(f'起点：{start}，终点：{end}')
        if intention in ['步行规划', '骑行规划']:
            route_cast = self.gaoDeApi.get_walking(start, end) if intention == '步行规划' else self.gaoDeApi.get_bicycling(start, end)
            path = route_cast['route']['paths'][0]
            steps = json.dumps(path['steps'], ensure_ascii=False)
            distance = int(path['distance']) # 单位米
            if distance > 1000:
                distance_str = f'{distance/1000:.1f}公里'
            else:
                distance_str = f'{distance}米'
            duration = int(path['cost']['duration']) if intention == '步行规划' else int(path['duration']) # 单位秒
            # 换算成xx小时xx分钟
            duration_hour = duration // 3600
            duration_minute = (duration % 3600) // 60
            duration_str = f'{duration_hour}小时{duration_minute}分钟'
            messages = [
                {'role': 'system', 'content': sys_route_plan},
                {'role': 'user', 'content': f'交通方式：{intention[:2]}；起点：{start}；终点：{end}；距离：{distance_str}；耗时：{duration_str}；路线：{steps}；聊天记录：{user_content}'},
            ]
            res = unillm(self.model_name_list, messages=messages)
            return res if res else f'{bot_name}有点累了，稍候再试吧'
        if intention == '驾车规划':
            route_cast = self.gaoDeApi.get_driving(start, end)
            taxi_cost = route_cast['route']['taxi_cost']
            path = route_cast['route']['paths'][0]
            steps = json.dumps(path['steps'], ensure_ascii=False)
            distance = int(path['distance']) # 单位米
            if distance > 1000:
                distance_str = f'{distance/1000:.1f}公里'
            else:
                distance_str = f'{distance}米'
            messages = [
                {'role': 'system', 'content': sys_route_plan},
                {'role': 'user', 'content': f'交通方式：{intention[:2]}；起点：{start}；终点：{end}；距离：{distance_str}；打车费用：{taxi_cost}元；路线：{steps}；聊天记录：{user_content}'},
            ]
            res = unillm(self.model_name_list, messages=messages)
            return res if res else f'{bot_name}有点累了，稍候再试吧'
        if intention == '公交规划':
            route_cast = self.gaoDeApi.get_bus(start, end)
            path = route_cast['route']['transits'][0]
            steps = json.dumps(path['segments'], ensure_ascii=False)
            distance = int(route_cast['route']['distance']) # 单位米
            if distance > 1000:
                distance_str = f'{distance/1000:.1f}公里'
            else:
                distance_str = f'{distance}米'
            messages = [
                {'role': 'system', 'content': sys_route_plan},
                {'role': 'user', 'content': f'交通方式：{intention[:2]}；起点：{start}；终点：{end}；距离：{distance_str}；路线：{steps}；聊天记录：{user_content}'},
            ]
            res = unillm(self.model_name_list, messages=messages)
            return res if res else f'{bot_name}有点累了，稍候再试吧'

    def poiRecResponse(self, user_content, bot_name):
        messages = [
                {'role': 'system', 'content': sys_poi_ext},
                {'role': 'user', 'content': user_content},
        ]
        res_rec = unillm(['glm4-9b']+self.model_name_list, messages=messages)
        logger.info(f'提取的信息：{res_rec}')
        address, keyword = res_rec.split('|')
        logger.info(f'地址：{address}，关键词：{keyword}')
        poi_list = self.gaoDeApi.get_poi_around(keyword=keyword, region=address)
        pois = json.dumps([f'{poi["name"]} {poi["address"]}' for poi in poi_list['pois']], ensure_ascii=False)
        messages = [
                {'role': 'system', 'content': sys_poi_rec},
                {'role': 'user', 'content': f'聊天记录：{user_content}；poi: {pois}'},
        ]
        res = unillm(self.model_name_list, messages=messages)
        return res if res else f'{bot_name}有点累了，稍候再试吧'

    def vidPromptResponse(self, user_content):
        messages = [
            {'role': 'system', 'content': sys_video_gen},
            {'role': 'user', 'content': user_content}
        ]
        res = unillm(self.model_name_list, messages=messages)
        logger.info(f'视频提示词：{res}')
        return res if res else user_content

    def mmResponse(self, image_path, user_content, bot_name):
        base64_image = encode_image(image_path=image_path)
        image_url = f"data:image/jpeg;base64,{base64_image}"
        messages = [
            {'role': 'user', 'content': [
                {"type": "text", "text": f'{user_content}，请用中文回答'},
                {"type": "image_url", "image_url": {"url": image_url}}
            ]}
        ]
        answer = unillm(['glm4v-flash'], messages=messages)
        return answer.strip() if answer else f'{bot_name}有点累了，上游模型速率限制，稍候再试吧'

    def isAdPic(self, image_path):
        base64_image = encode_image(image_path=image_path)
        image_url = f"data:image/jpeg;base64,{base64_image}"
        messages = [
            {'role': 'user', 'content': [
                {"type": "text", "text": '判断这张图片中是否有营销、引流等广告内容，只需直接回复“是”或“否”'},
                {"type": "image_url", "image_url": {"url": image_url}}
            ]}
        ]
        answer = unillm(['glm4v-flash'], messages=messages)
        return answer.strip()

class ApiServer:

    def __init__(self):
        """
        所有api接口的总体调用
        """
        self.configData = returnConfigData()            
        self.dms = DbMsgServer()

    def get_zaobao_al(self, format='json', ret='url'):
        params = {
            "format": format,
            "token": self.configData['apiServer']['alKey']
        }
        response = requests.get(f"{self.configData['apiServer']['alApi']}/zaobao", params=params)
        if response.status_code == 200 and response.json()['code'] == 200:
            if ret == 'url':
                img_url = response.json()['data']['image'] # 'news'=[] 'weiyu'=
                return img_url
            elif ret == 'news':
                news = response.json()['data']['news']
                return news
        else:
            logger.error(f"获取早报失败: {response.status_code} {response.text}")
            return ''
    
    def get_doutu_al(self, keyword='你礼貌么'):
        for i in range(7, 0, -1):
            params = {
                "keyword": keyword,
                "page": 1,
                "type": i,
                "token": self.configData['apiServer']['alKey']
            }
            response = requests.get(f"{self.configData['apiServer']['alApi']}/doutu", params=params)
            if response.status_code == 200 and response.json()['code'] == 200:
                img_list = response.json()['data']
                return img_list
        return []
    
    def get_doutu_hz(self, keyword='你礼貌么'):
        params = {
            "words": keyword,
            "page": 1,
            "id": 10000984,
            "key": self.configData['apiServer']['hzKey']
        }
        response = requests.get(self.configData['apiServer']['hzApi'], params=params)
        if response.status_code == 200 and response.json()['code'] == 200:
            img_list = response.json()['res']
            return img_list
        return []

    def get_yuanqi(self, text):
        headers = {
            'X-Source': 'openapi',
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.configData["apiServer"]["yuanqiToken"]}'
        }
        data = {
            "assistant_id": self.configData['apiServer']['yuanqiAssistant'],
            "user_id": self.configData['apiServer']['yuanqiUser'], 
            "stream": False,
            "messages": [{"role": "user","content": [{"type": "text", "text": text}]}]
        }

        response = requests.post(self.configData['apiServer']['yuanqiApi'], json=data, headers=headers)
        if response.status_code == 200:
            data = response.json()
            return data['choices'][-1]['message']['content']
        else:
            return ''
    
    def getMoringPage(self,):
        current_path = os.path.dirname(__file__)
        with open(f"{current_path}/../data/zaobao_template.json", 'r', encoding='utf-8') as f:
            data = json.load(f)
        # 每日一言
        try:
            response = requests.get("https://glitter.timeline.ink/api/v1")
            yiyan_text = response.text
        except:
            yiyan_text = ''
        if yiyan_text:
            data['texts'][1]['text'] = yiyan_text
        # 每日日期
        day_map = {0: '一', 1: '二', 2: '三', 3: '四', 4: '五', 5: '六', 6: '日'}
        today = datetime.now().strftime('%Y.%m.%d') + f' 星期{day_map[datetime.now().weekday()]}'
        data['texts'][3]['text'] = today
        # 每日新闻
        news = self.get_zaobao_al(ret='news')
        for i, new in enumerate(news[:10]):
            text = {
                    "x": 10,
                    "y": 290 + i*85,
                    "text": new,
                    "font": "Alibaba-PuHuiTi-Regular",
                    "fontSize": 25,
                    "color": "#4A4D4E",
                    "width": 700,
                    "textAlign": "left",
                    "lineSpacing": 1.2,
                    "zIndex": 2
                }
            data['texts'].append(text)
        bottom_logo_y = 290 + (i+1)*85
        canvas_height = bottom_logo_y + data['images'][1]['height']
        data['images'][1]['y'] = bottom_logo_y
        data['height'] = canvas_height

        for line in data['lines']:
            if line['startY'] == 1280:
                line['startY'] = canvas_height-1
            if line['endY'] == 1280:
                line['endY'] = canvas_height-1
        headers = {
            'X-API-Key': self.configData['apiServer']['imgRenderKey'],
            'Content-Type': 'application/json',
            }
        try:
            response = requests.post(self.configData['apiServer']['imgRenderApi'], headers=headers, data=json.dumps(data))
            img_url = response.json()['data']['url']
            img_path = downloadFile(img_url, prefix='morning_')
            return img_path
        except Exception as e:
            logger.error(f'img render error {e}')
            img_url = self.get_zaobao_al(ret='url')
            return img_url

    def getFishImg(self,):
        response = requests.get(self.configData['apiServer']['dpfishApi'])
        if response.status_code == 200:
            img_url = response.json()['data']['url']
            img_path = downloadFile(img_url, prefix='fish_')
            return img_path
        else:
            logger.error(f"获取摸鱼图片失败: {response.status_code} {response.text}")
            return ''

    def getAiNews(self,):
        response = requests.get('https://next.ithome.com/')
        try:
            soup = BeautifulSoup(response.text, 'html.parser')
            # 找到 id 为 'list' 的元素
            list_div = soup.find('div', id='list').find('div', class_='fl').find('ul', class_='bl')
            li_elements = list_div.find_all('li')
            if li_elements:
                text = ''
                count = 1
                for li in li_elements:
                    ele = li.find('a', class_='title')
                    url = ele.get('href')
                    title = ele.get('title')
                    messages = [{'role': 'user', 'content': f'根据这个自媒体标题判断文章类型: 0. 广告，1. AI资讯：{title}。你只需回答文章类型序号 0 或者 1，无需其他任何内容。'}]
                    result = unillm(['glm4-9b', 'glm4-flash'], messages=messages)
                    if result.strip() == '1':
                        text += f' \n🔥{count}. {title}\n🔗：{url}'
                        count += 1
                        if count > 10:
                            break
                return '🔥今日 AI 快讯🔥'+ text if text else ''
            else:
                return ''
        except Exception as e:
            logger.error(f'get_ai_news error {e}')
            return ''
    
    def getWxVideo(self, objectId, objectNonceId):
        params = {
            "AppSecret": self.configData['apiServer']['dpKey'],
            "objectId": objectId,
            "objectNonceId": objectNonceId,
        }
        response = requests.get(self.configData['apiServer']['dpWxVideoApi'], params=params, timeout=500)
        if response.status_code == 200:
            code = response.json().get('code')
            if code == 200:
                videoData = response.json()['data']
                description = videoData.get('description').replace("\n", "")
                nickname = videoData.get('nickname')
                videoUrl = videoData.get('url')
                content = f'描述: {description}\n作者: {nickname}\n链接: {videoUrl}'
                return content
            else:
                return response.json().get('msg', '接口调用失败')
        else:
            logger.error(f"获取微信视频失败: {response.status_code} {response.text}")
            return '获取微信视频失败'

    def getKfc(self, ):
        """
        疯狂星期四
        :return:
        """
        logger.info(f'[*]: 正在调用KFC疯狂星期四Api接口... ... ')
        try:
            jsonData = requests.get(url=self.configData['kfcApi'], timeout=30).json()
            result = jsonData.get('text')
            if result:
                return result
            return None
        except Exception as e:
            logger.error(f'[-]: KFC疯狂星期四Api接口出现错误, 错误信息: {e}')
            return None
    
    def getTopTalkRank(self, room_id):
        ranks = dict(self.dms.showTodayRank(room_id))
        rank_contents = '\n'.join(
            [f'{index + 1}. {talker}: {talker_chat_count}' for index, (talker, talker_chat_count) in
             enumerate(ranks.items())])
        top_talker_name, top_talker_name_chat_count = next(iter(ranks.items()))
        rank_contents = f'>>>>水王：👑{top_talker_name}👑<<<<\n🏊‍♀️>>>>水王Top10<<<<🏊‍♀️\n{rank_contents}'
        return rank_contents

    def getTopImageRank(self, room_id):
        image_ranks = dict(self.dms.showTodayImageRank(room_id))
        if image_ranks:
            image_content = '\n'.join(
                [f'{index + 1}. {talker}: {talker_chat_count}' for index, (talker, talker_chat_count) in
                 enumerate(image_ranks.items())])
            top_talker_name, top_talker_name_chat_count = next(iter(image_ranks.items()))
            image_content = f'>>>>图王：👑{top_talker_name}👑<<<<\n🏊🌇>>>>图王Top10<<<<🌇\n{image_content}'
        else:
            image_content = "今天还没有人发图片哦~" 
        return image_content