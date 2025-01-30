from queue import Empty
from wcferry import Wcf
from threading import Thread

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
        while self.wcf.is_receiving_msg():
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
                continue


if __name__ == '__main__':
    ms = MainServer()
    logger.info('main_server 启动成功！！！')
    ms.processMsg()