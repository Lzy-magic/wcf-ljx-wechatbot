import time
import schedule
import functools
from datetime import datetime
from lunarcalendar import Converter, Solar, Lunar
from utils.common import logger, returnConfigData, clearCacheFolder
from servers.api_server import ApiServer, LLMTaskApi
from servers.db_server import DbRoomServer

def exception_handler(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(f'{func.__name__}异常: {e}')
    return wrapper

# 阳历转换为阴历
def solar_to_lunar(date):
    year, month, day = date.split('-')
    solar_date = Solar(int(year), int(month), int(day))
    lunar_date = Converter.Solar2Lunar(solar_date)
    date = f'{lunar_date.year}-{lunar_date.month:02d}-{lunar_date.day:02d}'
    return date

# 阴历转换为阳历
def lunar_to_solar(date, leap_month=False):
    year, month, day = date.split('-')
    lunar_date = Lunar(int(year), int(month), int(day), leap_month)
    solar_date = Converter.Lunar2Solar(lunar_date)
    date = f'{solar_date.year}-{solar_date.month:02d}-{solar_date.day:02d}'
    return date

class ScheduleTaskServer:
    
    def __init__(self, wcf):
        self.wcf = wcf
        self.ams = ApiServer()
        self.lta = LLMTaskApi()
        self.drs = DbRoomServer()

    @exception_handler
    def pushMorningPage(self):
        page = self.ams.getMoringPage()
        if not page:
            logger.error('获取早安页面失败')
            return
        room_items = self.drs.showPushRoom(taskName='morningPage')
        logger.info(f'准备推送给群: {room_items}')
        for room_id, room_name in room_items:
            self.wcf.send_image(path=page, receiver=room_id) # 传本地文件
            logger.info(f'早安页面推送给{room_name}成功')
    
    @exception_handler
    def pushFish(self):
        page = self.ams.getFishImg()
        if not page:
            logger.error('获取摸鱼图片失败')
            return
        room_items = self.drs.showPushRoom(taskName='fishPage')
        logger.info(f'准备推送给群: {room_items}')
        for room_id, room_name in room_items:
            self.wcf.send_image(path=page, receiver=room_id) # 传本地文件
            logger.info(f'摸鱼图片推送给{room_name}成功')
    
    @exception_handler
    def pushAiNews(self):
        text = self.ams.getAiNews()
        if not text:
            logger.error('获取AI新闻页面失败')
            return
        room_items = self.drs.showPushRoom(taskName='aiNews')
        logger.info(f'准备推送给群: {room_items}')
        for room_id, room_name in room_items:
            self.wcf.send_text(msg=text, receiver=room_id) # 传本地文件
            logger.info(f'AI新闻页面推送给{room_name}成功')
    
    @exception_handler
    def pushGoodNight(self):
        text = self.lta.getGoodNight()
        if not text:
            logger.error('获取晚安页面失败')
            return
        room_items = self.drs.showPushRoom(taskName='goodNight')
        logger.info(f'准备推送给群: {room_items}')
        for room_id, room_name in room_items:
            self.wcf.send_text(msg=text, receiver=room_id)
            logger.info(f'晚安页面推送给{room_name}成功')
    
    @exception_handler
    def pushFestivalWish(self):
        festival_dict = returnConfigData()['scheduleConfig']['festival']
        today = str(datetime.now().date())
        today_solar = '-'.join(today.split('-')[1:])
        if today_solar in festival_dict.values():
            for festival, date in festival_dict.items():
                if date == today_solar:
                    room_items = self.drs.showPushRoom(taskName='festival')
                    logger.info(f'准备推送给群: {room_items}')
                    for room_id, room_name in room_items:
                        content = self.lta.festivalWish(festival, room_name)
                        self.wcf.send_text(msg=content, receiver=room_id)
                        logger.info(f'节日祝福推送给{room_name}成功: {festival} {date}')

    @exception_handler
    def pushBirthdayWish(self):
        birthday_dict = returnConfigData()['scheduleConfig']['birthday']
        today = str(datetime.now().date())
        today_lunar = solar_to_lunar(today)
        today_lunar = '-'.join(today_lunar.split('-')[1:])
        if today_lunar in birthday_dict.values():
            for name, birthday in birthday_dict.items():
                if birthday == today_lunar:
                    content = self.lta.birthdayWish(name, solar=today, lunar=today_lunar)
                    room_items = self.drs.showPushRoom(taskName='birthday')
                    logger.info(f'准备推送给群: {room_items}')
                    for room_id, room_name in room_items:
                        self.wcf.send_text(msg=content, receiver=room_id)
                        logger.info(f'生日祝福推送给{room_name}成功: {name} {birthday}')
    
    @exception_handler
    def pushWeatherReport(self):
        weather_list = returnConfigData()['scheduleConfig']['weather_district']
        room_items = self.drs.showPushRoom(taskName='weatherReport')
        logger.info(f'准备推送给群: {room_items}')
        for room_id, room_name in room_items:
            for district in weather_list:
                content = self.lta.getWeather(address=district)
                self.wcf.send_text(msg=content, receiver=room_id)
                logger.info(f'天气预报推送给{room_name}成功: {district}')
    
    @exception_handler
    def pushBeikeReport(self):
        room_items = self.drs.showPushRoom(taskName='beikeReport')
        logger.info(f'准备推送给群: {room_items}')
        for room_id, room_name in room_items:
            contents = self.lta.getBeike()
            for content in contents:
                self.wcf.send_text(msg=content, receiver=room_id)
            logger.info(f'房源信息推送给{room_name}成功')

    @exception_handler
    def pushGitHubReport(self):
        week_day = datetime.now().weekday()
        if week_day == 6:
            room_items = self.drs.showPushRoom(taskName='githubReport')
            logger.info(f'准备推送给群: {room_items}')
            try:
                for room_id, room_name in room_items:
                    content = self.lta.getGithubTrending()
                    self.wcf.send_text(msg=content, receiver=room_id)
                    logger.info(f'GitHub热榜推送给{room_name}成功')
            except Exception as e:
                logger.error(f'GitHub热榜推送失败: {e}')

    @exception_handler
    def clearCache(self):
        clearCacheFolder()
        logger.info('缓存清理成功')

    def run(self):
        configData = returnConfigData()['scheduleConfig']
        schedule.every().day.at(configData['morningPageTime']).do(self.pushMorningPage)
        schedule.every().day.at(configData['fishTime']).do(self.pushFish)
        schedule.every().day.at(configData['aiNewsTime']).do(self.pushAiNews)
        schedule.every().day.at(configData['goodNightTime']).do(self.pushGoodNight)
        schedule.every().day.at(configData['festivalTime']).do(self.pushFestivalWish)
        schedule.every().day.at(configData['birthdayTime']).do(self.pushBirthdayWish)
        schedule.every().day.at(configData['weatherReportTime']).do(self.pushWeatherReport)
        schedule.every().day.at(configData['beikeReportTime']).do(self.pushBeikeReport)
        schedule.every().day.at(configData['githubReportTime']).do(self.pushGitHubReport)
        schedule.every().day.at(configData['clearCacheTime']).do(self.clearCache)
        while True:
            schedule.run_pending()
            time.sleep(1)