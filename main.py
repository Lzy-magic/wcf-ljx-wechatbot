from queue import Empty
from wcferry import Wcf
from threading import Thread, Event
import time

from utils.common import logger, initCacheFolder
from servers.db_server import DbInitServer
from servers.msg_server import SingleMsgHandler, RoomMsgHandler, GhMsgHandler
from servers.schedule_server import ScheduleTaskServer

class MainServer:
    def __init__(self):
        self.wcf = Wcf()
        self.wcf.enable_receiving_msg() # 开启全局接收
        self.initDateBase()
        self.rmh = RoomMsgHandler(self.wcf)
        self.smh = SingleMsgHandler(self.wcf)
        self.gmh = GhMsgHandler(self.wcf)
        self.sts = ScheduleTaskServer(self.wcf)
        self.stop_event = Event()  # Used to signal threads to stop
        Thread(target=self.sts.run, name='定时推送服务').start()
        
    def initDateBase(self, ):
        # 初始化数据存储
        dis = DbInitServer()
        dis.initDb()
        initCacheFolder()

    def isLogin(self, ):
        """
        判断是否登录
        :return:
        """
        ret = self.wcf.is_login()
        if ret:
            userInfo = self.wcf.get_user_info()
            logger.info(f"""
            \t微信名：{userInfo.get('name')}
            \t微信ID：{userInfo.get('wxid')}
            \t手机号：{userInfo.get('mobile')}  
            \t存储地址：{userInfo.get('home')}    
            """.replace(' ', ''))

    def processMsg(self, ):
        # 判断是否登录
        self.isLogin()
        while self.wcf.is_receiving_msg() and not self.stop_event.is_set():
            try:
                msg = self.wcf.get_msg() # WxMsg 对象
                logger.info(f'main_server 接收到消息: {msg.type} {msg.sender} {msg.roomid} {msg.content}')
                # 开始处理消息的逻辑
                # 群聊消息处理
                if '@chatroom' in msg.roomid:
                    Thread(target=self.rmh.mainHandle, args=(msg,)).start()
                # 私聊消息处理
                elif '@chatroom' not in msg.roomid and 'gh_' not in msg.sender:
                    Thread(target=self.smh.mainHandle, args=(msg,)).start()
                # 公众号消息处理
                elif msg.sender.startswith('gh_'):
                    Thread(target=self.gmh.mainHandle, args=(msg,)).start()
                else:
                    pass

            except Empty:
                time.sleep(0.1)  # Add a small delay to reduce CPU usage
                continue
            except KeyboardInterrupt:
                logger.info("processMsg 收到 KeyboardInterrupt，准备退出...")
                self.wcf.disable_recv_msg()  # 停止接收消息
                self.wcf.cleanup()
                self.stop_event.set()  # Signal threads to stop
                break


if __name__ == '__main__':
    ms = MainServer()
    logger.info('main_server 启动成功！！！')
    try:
        ms.processMsg()
    except KeyboardInterrupt:
        logger.info("主程序在顶层收到 KeyboardInterrupt，准备退出...")
    finally:
        logger.info("程序退出。")