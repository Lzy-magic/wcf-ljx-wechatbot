
import re
import os
import shutil
from datetime import datetime
import xml.etree.ElementTree as ET
from utils.common import logger, returnConfigData, returnPicCacheFolder
from utils.prompt import intentions_list, welcome_msg
from servers.db_server import DbRoomServer, DbUserServer, DbMsgServer
from servers.api_server import LLMTaskApi, ApiServer, LLMResponseApi

class MsgHandler:
    def __init__(self, wcf):
        self.wcf = wcf
        self.wxid = wcf.get_self_wxid()
        self.wxname = wcf.get_user_info().get('name')
        self.dus = DbUserServer()
        self.drs = DbRoomServer()
        self.dms = DbMsgServer()
        self.lta = LLMTaskApi()
        self.lra = LLMResponseApi()
        self.aps = ApiServer()
        configData = returnConfigData()
        self.superAdmins = configData['Administrators']
        self.adminFunctionWord = configData['adminFunctionWord']
        self.roomKeyWord = configData['roomKeyWord']
        self.bot_name = configData['systemConfig']['robotName']
        self.difyImgConId = {}
        # self.whiteUsers = set([item[0] for item in self.dus.showUser()])
        # self.whiteRooms = set([item[0] for item in self.drs.showWhiteRoom()]) # 示例：[('5xx8@chatroom', 'xx群')]
  
    def judgeSuperAdmin(self, wxId):
        return wxId in self.superAdmins
    
    def getWxName(self, wxid):
        """
        获取好友或者群聊昵称
        """
        name_list = self.wcf.query_sql("MicroMsg.db",
                                f"SELECT NickName FROM Contact WHERE UserName = '{wxid}';")
        if not name_list:
            return ''
        name = name_list[0]['NickName']
        return name

    def getWxId(self, wxname):
        """
        获取好友或者群聊wxid
        """
        name_list = self.wcf.query_sql("MicroMsg.db",
                                f"SELECT UserName FROM Contact WHERE NickName = '{wxname}';")
        if not name_list:
            return ''
        name = name_list[0]['UserName']
        return name
       
    def getAtData(self, msg):
        noAtMsg = msg.content
        try:
            root_xml = ET.fromstring(msg.xml)
            atUserListsElement = root_xml.find('.//atuserlist')
            atUserLists = atUserListsElement.text.replace(' ', '').strip().strip(',').split(
                ',') if atUserListsElement is not None else None
            if not atUserLists:
                return [], ''
            atNames = []
            for atUser in atUserLists:
                atUserName = self.wcf.get_alias_in_chatroom(atUser, msg.roomid)
                atNames.append(atUserName)
            for atName in atNames:
                noAtMsg = noAtMsg.replace('@' + atName, '')
        except Exception as e:
            logger.error(f'[~]: 处理@消息出现小问题, 仅方便开发调试: {e}')
            return [], ''
        return atUserLists, noAtMsg.strip()

    def sendTextMsg(self, msg, text):
        sender = msg.sender
        roomId = msg.roomid
        isRoom = msg.from_group()
        if isRoom:
            status = self.wcf.send_text(msg=self.renderAtPrefix(sender, roomId) + text, receiver=roomId, aters=sender)
            logger.info(f'消息发送状态: {status}')
            if not status == 0:
                status = self.wcf.send_text(msg=self.renderAtPrefix(sender, roomId) + text, receiver=roomId, aters=sender)
                logger.info(f'消息重发状态: {status}')    
        else:
            status = self.wcf.send_text(msg=text, receiver=sender)
            logger.info(f'消息发送状态: {status}')
            if not status == 0:
                status = self.wcf.send_text(msg=text, receiver=sender)
                logger.info(f'消息重发状态: {status}')

    def sendFileMsg(self, msg, path, fileType='pic'):
        isRoom = msg.from_group()
        receiver = msg.roomid if isRoom else msg.sender
        if fileType == 'pic':
            self.wcf.send_image(path=path, receiver=receiver) # send_file 和 send_image 不一样
        else:
            self.wcf.send_file(path=path, receiver=receiver)

    def receiveImgMsg(self, msg):
        logger.info(f'收到图片消息: {msg.extra}')
        picPath = returnPicCacheFolder()
        img_path = self.wcf.download_image(msg.id, msg.extra, picPath)
        # 给图片加上时间戳
        new_name = f'{msg.sender}_{msg.roomid}_{datetime.now().strftime("%Y%m%d%H%M%S")}{os.path.splitext(img_path)[1]}'
        shutil.move(img_path, os.path.join(picPath, new_name))
        # 判断是否为广告图片
        answer = self.lra.isAdPic(os.path.join(picPath, new_name))
        logger.info(f'图片是否为广告图片: {answer}')
        if answer == '是':
            #self.sendTextMsg(msg, '你小子是不是准备发广告？小心被群主发现！')
            nickname = self.getWxName(msg.sender)
            roomname = self.getWxName(msg.roomid)
            for admin in self.superAdmins:    
                msg.sender = admin
                msg.roomid = admin
                #self.sendTextMsg(msg, f"{nickname}在{roomname}群发广告啦！")

    def triggerFunction(self, msg, triggerType, triggerWords, chatid):
        content = msg.content.strip()
        if not any(content.startswith(t) for t in triggerWords):
            return False
        # TODO modify
        # if triggerType == 'gzhRetrive':
        #     # 调用指定公众号文章进行回复
        #     response = self.aps.get_yuanqi(content)
        #     self.sendTextMsg(msg, response)
        #     self.lra.updateMessage(chatid, [msg.content, response])
        #     # 保存消息到数据库
        #     self.addChatMsg(self.wxid, self.bot_name, chatid, response)
        #elif triggerType == 'difySearch':
            # 调用dify搜索智能体进行回复
           # pre_text = f'{self.bot_name}正在调用搜索引擎为您服务，请耐心等待哦，预计20-60s'
            #self.sendTextMsg(msg, pre_text)
           # response = self.lta.difySearch(content, user=self.bot_name)
            #self.sendTextMsg(msg, response)
           # self.lra.updateMessage(chatid, [msg.content, response])
           # self.addChatMsg(self.wxid, self.bot_name, chatid, response)
        # elif triggerType == 'beikeRetrive':
        #     match = re.search(r'\d+', content)
        #     if content.startswith('挂牌'):
        #         bot_answer = f'https://yc.ke.com/ershoufang/{match.group()}.html' if match else '请输入正确的挂牌房源号'
        #     elif content.startswith('成交'):
        #         bot_answer = f'https://yc.ke.com/chengjiao/{match.group()}.html' if match else '请输入正确的成交房源号'
        #     else:
        #         bot_answer = '请输入正确的指令'
        #     self.sendTextMsg(msg, bot_answer)
        elif triggerType == 'KfcKeyWords':   
            response = self.aps.getKfc()
            self.sendTextMsg(msg, response)
        elif triggerType == 'TopWords':
            ranks = self.dms.showTodayRank(chatid)
            rank_contents = '\n'.join([f'{rank[0]}: {rank[1]}' for rank in ranks])
            content = self.lta.getTopSummary(rank_contents)
            self.sendTextMsg(msg, content)
        else:
            bot_answer = f'[-]: 未知的触发器类型: {triggerType}, 请检查配置'
            self.sendTextMsg(msg, bot_answer)
        return True

    def getOrUpdateDifyImgConId(self, chatid, conId=''):
        if not conId:
            return self.difyImgConId.get(chatid, '')
        else:
            self.difyImgConId[chatid] = conId
            return conId
       
    def coreFunction(self, msg):
        response = ""
        chatid = msg.roomid if msg.from_group() else msg.sender
        # 1. 自定义关键词触发功能
        tStatus = []
        for tType, tWords in returnConfigData()['customKeyWord'].items():
            if not isinstance(tWords, list):
                tWords = [tWords]
            status = self.triggerFunction(msg, tType, tWords, chatid)
            tStatus.append(status)
        if any(tStatus):
            return
        # 2. 意图识别+AI回复功能：一个群或一个私聊维护一个messages列表
        conversation_list = self.lra.get_conversation_list(chatid)
        # print(chatid, conversation_list)
        messages = [item[1] for item in conversation_list]
        messages.append({'role': 'user', 'content': msg.content})
        intention = self.lra.intentionRec(messages)
        logger.info(f'意图识别结果：{intention}')
        # 2.0 未识别到指定意图，返回正常回复，否则根据意图进行相应的操作
        if intention not in intentions_list:
            if msg.from_group() and not self.drs.searchResponseRoom(chatid):
                self.sendTextMsg(msg, "聊天功能暂时关闭咯~")
            else:
                response = self.lra.generalResponse(messages, self.bot_name)
                self.sendTextMsg(msg, response)
                self.lra.updateMessage(chatid, [msg.content, response])
        # 2.1 天气预报
        elif intention == '天气':
            response = self.lra.weatherResponse(msg.content, self.bot_name)
            self.sendTextMsg(msg, response)
            self.lra.updateMessage(chatid, [msg.content, response])
        # 2.2 图片理解
        # elif intention in ['数学解题', '图片理解']:
        #     picPath = returnPicCacheFolder()
        #     prefix = f'{msg.sender}_{msg.roomid}_'
        #     img_files = sorted([f for f in os.listdir(picPath) if f.startswith(prefix)])
        #     image_path = os.path.join(picPath, img_files[-1]) if img_files else None
        #     if image_path:
        #         response = self.lra.mmResponse(image_path, msg.content, self.bot_name)
        #     else:
        #         response = "你是需要我帮你理解图片么，请先发送一张图片哦，我会基于你的最近一张图片进行回答"
        #     self.sendTextMsg(msg, response)
        #     self.lra.updateMessage(chatid, [msg.content, response])
        # 2.3 图片理解

        # 保存消息到数据库
        if response != "":
            self.addChatMsg(self.wxid, self.bot_name, chatid, response)

    def parseMsg(self, msg):
        """
        引用 type=57；公众号 type=5；视频号 type=51；音乐 type=92
        """
        root = ET.fromstring(msg.content)
        appmsg = root.find('appmsg')
        eType = appmsg.find('type').text
        if eType == '57': # 引用消息
            if msg.from_group() and (not msg.is_at(self.wxid)):
                return 
            curText = appmsg.find('title').text
            oriType = appmsg.find('refermsg').find('type').text
            oriContent = appmsg.find('refermsg').find('content').text
            oriWxId = root.find('fromusername').text
            oriName = self.getWxName(oriWxId)
            logger.info(f'收到引用消息: {curText}, {oriType}, {oriContent}, {oriWxId}, {oriName}')
            if oriType == '1': # 文本消息
                content = curText + f'\n引用{oriName}的消息：{oriContent}'
                msg.content = content
                logger.info(f'处理后的消息: {content}')
                self.addChatMsg(msg.sender, self.getWxName(msg.sender), msg.roomid, msg.content)
            else:
                # TODO: 处理图片、视频、语音等消息
                msg.content = curText
                logger.info(f'暂不支持引用{oriType}消息 {oriContent}')
            self.coreFunction(msg)
        elif eType == '5': # 公众号消息
            # TODO: url 无法获取内容，待解决
            name = appmsg.find('sourcedisplayname').text
            title = appmsg.find('title').text
            des = appmsg.find('des').text
            url = appmsg.find('url').text
            urlOri = appmsg.find('webviewshared').find('shareUrlOriginal').text
            urlOpen = appmsg.find('webviewshared').find('shareUrlOpen').text
            response = f'公众号：{name}\n题目：{title}\n简介：{des}'
            data = self.lta.genArticleSum(urlOpen)
            if data:
                response += f'\n摘要：{data["content"]}\n发布：{data["date"]}'
            self.sendTextMsg(msg, response)
        elif eType == '51': # 视频号消息
            finderFeed = root.find('.//finderFeed')
            objectId = finderFeed.find('./objectId').text
            objectNonceId = finderFeed.find('./objectNonceId').text
            response = self.aps.getWxVideo(objectId, objectNonceId)
            self.sendTextMsg(msg, response)
        elif eType == '33': # 小程序消息
            logger.info(f'收到其他类型消息: {eType}')
            # content = curText + f'\n引用{oriName}的消息：{oriContent}'
            # msg.content = content
            # logger.info(f'处理后的消息: {content}')
            # self.addChatMsg(msg.sender, self.getWxName(msg.sender), msg.roomid, msg.content)
        else:
            logger.info(f'收到其他类型消息: {eType}')
            #response = f'收到{eType}消息，暂不支持处理，请联系群主安排开发'
           # self.sendTextMsg(msg, response)

    def addChatMsg(self, wxId, wxName, roomId, content):
        self.dms.addChatMessage(wxId, wxName, roomId, content)

class SingleMsgHandler(MsgHandler):
    def __init__(self, wcf):
        super().__init__(wcf)
    
    def autoAcceptFriendRequest(self, msg):
        try:
            xml = ET.fromstring(msg.content)
            v3 = xml.attrib["encryptusername"]
            v4 = xml.attrib["ticket"]
            scene = int(xml.attrib["scene"])
            status = self.wcf.accept_new_friend(v3, v4, scene)
            logger.info(f"同意好友请求：{status}")
        except Exception as e:
            logger.error(f"同意好友出错：{e}")
    
    def sayHiToNewFriend(self, msg):
        logger.info(f"收到系统消息: {msg.type} {msg.content}")
        side_nickName = re.findall(r"(.*)刚刚把你添加到通讯录，现在可以开始聊天了。", msg.content) # 对方添加我为好友
        self_nickName = re.findall(r"你已添加了(.*)，现在可以开始聊天了。", msg.content) # 我主动添加了好友
        if side_nickName:
            # 更新好友列表
            # self.dus.addUser(msg.sender, msg.roomid)
            # 给超管发通知
            for admin in self.superAdmins:
                msg.sender = admin
                self.sendTextMsg(msg, f"{side_nickName[0]}，有好友来了")
        if self_nickName:
            self.sendTextMsg(msg, f"Hi，{self_nickName[0]}，我通过了你的好友请求。\n\n {welcome_msg}")

    def superAdminFunction(self, msg):
        content = msg.content.strip()
        status = False
        # 添加私聊权限
        addWhiteWord = self.adminFunctionWord['addWhiteWord']
        if content.startswith(addWhiteWord):
            status = True
            wxId = content.replace(addWhiteWord, '').strip()
            if wxId.endswith('@chatroom'):
                if self.drs.addWhiteRoom(wxId, self.getWxName(wxId)):
                    self.sendTextMsg(msg, f'{wxId} 已添加群聊权限')
                    # self.whiteRooms.add(wxId)
                else:
                    self.sendTextMsg(msg, f'{wxId} 添加群聊权限失败')
            else:
                if self.dus.addUser(wxId, self.getWxName(wxId)):
                    self.sendTextMsg(msg, f'{wxId} 已添加私聊权限')
                    # self.whiteUsers.add(wxId)
                else:
                    self.sendTextMsg(msg, f'{wxId} 添加私聊权限失败')
        # 删除私聊权限
        delWhiteWord = self.adminFunctionWord['delWhiteWord']
        if content.startswith(delWhiteWord):
            status = True
            wxId = content.replace(addWhiteWord, '').strip()
            if wxId.endswith('@chatroom'):
                if self.drs.delWhiteRoom(wxId):
                    self.sendTextMsg(msg, f'{wxId} 已删除群聊权限')
                    # self.whiteRooms.remove(wxId)
                else:
                    self.sendTextMsg(msg, f'{wxId} 删除群聊权限失败')
            else:
                if self.dus.delUser(wxId):
                    self.sendTextMsg(msg, f'{wxId} 已删除私聊权限')
                    # self.whiteUsers.remove(wxId)
                else:
                    self.sendTextMsg(msg, f'{wxId} 删除私聊权限失败')
        # 添加推送群
        addPushWord = self.adminFunctionWord['addPushWord']
        if content.startswith(addPushWord):
            status = True
            parms = content.split(" ")
            taskName = parms[1]
            wxId = parms[2]
            if wxId.endswith('@chatroom'):
                if self.drs.addPushRoom(taskName, wxId, self.getWxName(wxId)):
                    self.sendTextMsg(msg, f'{wxId} 已添加推送群')
                    # self.whiteRooms.add(wxId)
                else:
                    self.sendTextMsg(msg, f'{wxId} 添加推送群失败')
            else:
                if self.dus.addUser(wxId, self.getWxName(wxId)):
                    self.sendTextMsg(msg, f'{wxId} 已添加推送群')
                    # self.whiteUsers.add(wxId)
                else:
                    self.sendTextMsg(msg, f'{wxId} 添加推送群失败')
        # 删除推送群
        delPushWord = self.adminFunctionWord['delPushWord']
        if content.startswith(delPushWord):
            status = True
            wxId = content.replace(delPushWord, '').strip()
            if wxId.endswith('@chatroom'):
                if self.drs.delPushRoom(wxId):
                    self.sendTextMsg(msg, f'{wxId} 已删除推送群')
                    # self.whiteRooms.add(wxId)
                else:
                    self.sendTextMsg(msg, f'{wxId} 删除推送群失败')
            else:
                if self.dus.delUser(wxId, self.getWxName(wxId)):
                    self.sendTextMsg(msg, f'{wxId} 已删除推送群')
                    # self.whiteUsers.add(wxId)
                else:
                    self.sendTextMsg(msg, f'{wxId} 删除推送群失败')

         # 增加回复群
        AddResponseWord = self.adminFunctionWord['AddResponseWord']
        if content.startswith(AddResponseWord):
            status = True
            wxId = content.replace(AddResponseWord, '').strip()
            if wxId.endswith('@chatroom'):
                if self.drs.addResponseRoom(wxId, self.getWxName(wxId)):
                    self.sendTextMsg(msg, f'{wxId} 已添加回复群')                    
                else:
                    self.sendTextMsg(msg, f'{wxId} 添加回复群失败')
            else:
                if self.dus.delUser(wxId, self.getWxName(wxId)):
                    self.sendTextMsg(msg, f'{wxId} 已添加回复群')
                    # self.whiteUsers.add(wxId)
                else:
                    self.sendTextMsg(msg, f'{wxId} 添加回复群失败')

        # 删除回复群
        delResponseWord = self.adminFunctionWord['delResponseWord']
        if content.startswith(delResponseWord):
            status = True
            wxId = content.replace(delResponseWord, '').strip()
            if wxId.endswith('@chatroom'):
                if self.drs.delResponseRoom(wxId):
                    self.sendTextMsg(msg, f'{wxId} 已删除回复群')                    
                else:
                    self.sendTextMsg(msg, f'{wxId} 删除回复群失败')
            else:
                if self.dus.delUser(wxId, self.getWxName(wxId)):
                    self.sendTextMsg(msg, f'{wxId} 已删除回复群')
                    # self.whiteUsers.add(wxId)
                else:
                    self.sendTextMsg(msg, f'{wxId} 删除回复群失败')

        # 查询回复群
        ShowResponseWord = self.adminFunctionWord['ShowResponseWord']
        if content.startswith(ShowResponseWord):
            status = True
            wxId = content.replace(ShowResponseWord, '').strip()
            response = self.drs.showResponseRoom()
            self.sendTextMsg(msg, f'回复群如下:\n{response}')

        # 7天未说话
        UnTalkMembers = self.adminFunctionWord['UnTalkMembers']
        if content.startswith(UnTalkMembers):
            status = True
            wxId = content.replace(UnTalkMembers, '').strip()
            if wxId.endswith('@chatroom'):
                talkMemberResult = dict(self.dms.showLastWeekTalkMembers(wxId))
                roomMembers = self.wcf.get_chatroom_members(wxId)
                untalkMembers = {key: roomMembers[key] for key in roomMembers.keys() - talkMemberResult.keys()}
                content = '\n'.join([f'{item}' for item in untalkMembers.values()])
                if content:
                    self.sendTextMsg(msg, f'7天未说话列表如下\n{content}')
                else:
                    self.sendTextMsg(msg, f'7天未说话列表为空')
        
        return status
    
    def joinRoom(self, msg):
        sender = msg.sender
        content = msg.content.strip()
        roomId = self.roomKeyWord[content]
        roomMember = self.wcf.get_chatroom_members(roomId)
        if len(roomMember) == 500:
            self.sendTextMsg(msg, f'群满员了，请等候再试')
            return
        if sender in roomMember.keys():
            self.sendTextMsg(msg, '你小子已经进群了, 还想干吗[旺柴]')
            return 
        if self.wcf.invite_chatroom_members(roomId, sender):
            self.sendTextMsg(msg, '欢迎加入')
        else:
            self.sendTextMsg(msg, '邀请进群失败，请稍后再试')

    def mainHandle(self, msg):
        sender = msg.sender
        # 如果是超级管理员的消息，则进行超级管理员功能
        if self.judgeSuperAdmin(sender) and msg.type == 1:
            status = self.superAdminFunction(msg)
            if status:
                return
        
        # 处理好友请求
        ## 此处wcf尚未实现好友请求自动同意功能，故暂时在微信端修改为自动通过好友请求
        # if msg.type == 37: # 首先通过好友申请
        #     self.autoAcceptFriendRequest(msg)
        #     return
        if msg.type == 10000:  # 系统信息-通过好友请求
            self.sayHiToNewFriend(msg)
            return
        
        # 处理进群请求
        if msg.type == 1 and msg.content.strip() in self.roomKeyWord.keys():
            self.joinRoom(msg)
            return 

        # 判断是否有私聊权限
        if not (self.dus.searchUser(sender) or self.judgeSuperAdmin(sender)):
            return
        
        # 开始处理消息
        if msg.type == 1: # 文本消息
            self.coreFunction(msg)
        elif msg.type == 3: # 图片消息
            self.receiveImgMsg(msg)
        elif msg.type == 49: # 引用消息
            self.parseMsg(msg)
        
class RoomMsgHandler(MsgHandler):
    def __init__(self, wcf):
        super().__init__(wcf)
    
    def judgeAdmin(self, wxId, roomId):
        return self.dus.searchAdmin(wxId, roomId)
    
    def AdminFunction(self, msg):
        sender = msg.sender
        roomId = msg.roomid
        if msg.type != 1: # 非文本消息
            return
        # 超级管理员功能
        if self.judgeSuperAdmin(sender):
            self.superAdminFunction(msg)
        # 管理员功能
        atUserLists, noAtMsg = self.getAtData(msg)
        if not atUserLists:
            return
        # 踢人
        delUserWord = self.adminFunctionWord['delUserWord']
        if noAtMsg.strip() in delUserWord:
            for atWxId in atUserLists:
                if self.wcf.del_chatroom_members(roomId, atWxId):
                    self.wcf.send_text(
                        f'@{self.wcf.get_alias_in_chatroom(atWxId, roomId)} 基于你的表现, 给你移出群聊的奖励',
                        receiver=roomId)
                else:
                    self.wcf.send_text(
                        f'@{self.wcf.get_alias_in_chatroom(sender, roomId)} [{self.wcf.get_alias_in_chatroom(atWxId, roomId)}] 移出群聊失败',
                        receiver=roomId, aters=sender)
                
    def superAdminFunction(self, msg):
        sender = msg.sender
        roomId = msg.roomid
        msgType = msg.type
        if not self.judgeSuperAdmin(sender):
            return
        if msgType != 1: # 非文本消息
            return
        atUserLists, noAtMsg = self.getAtData(msg)
        if not atUserLists:
            return
        # 添加管理员
        addAdminWords = self.adminFunctionWord['addAdminWord']
        if noAtMsg.strip() in addAdminWords:
            for atUser in atUserLists:
                if self.dus.searchAdmin(atUser, roomId):
                    logger.info(f'[-]: {atUser} 已是管理员')
                    self.wcf.send_text(f'@{self.wcf.get_alias_in_chatroom(sender, roomId)}\n管理员 [{self.wcf.get_alias_in_chatroom(atUser, roomId)}] 已存在',
                                receiver=roomId, aters=sender)
                else:
                    status = self.dus.addAdmin(atUser, roomId)
                    if status:
                        logger.info(f'[+]: {atUser} 已被设置为管理员')
                        self.wcf.send_text(f'@{self.wcf.get_alias_in_chatroom(sender, roomId)}\n管理员 [{self.wcf.get_alias_in_chatroom(atUser, roomId)}] 添加成功',
                                    receiver=roomId, aters=sender)
                    else:
                        logger.error(f'[-]: {atUser} 添加管理员失败')
                        self.wcf.send_text(f'@{self.wcf.get_alias_in_chatroom(sender, roomId)}\n管理员 [{self.wcf.get_alias_in_chatroom(atUser, roomId)}] 添加失败',
                                    receiver=roomId, aters=sender)
        # 删除管理员
        delAdminWords = self.adminFunctionWord['delAdminWord']
        if noAtMsg.strip() in delAdminWords:
            for atUser in atUserLists:
                if not self.dus.searchAdmin(atUser, roomId):
                    logger.info(f'[-]: {atUser} 不是管理员')
                    self.wcf.send_text(f'@{self.wcf.get_alias_in_chatroom(sender, roomId)}\n管理员 [{self.wcf.get_alias_in_chatroom(atUser, roomId)}] 不存在',
                                receiver=roomId, aters=sender)
                else:
                    status = self.dus.delAdmin(atUser, roomId)
                    if status:
                        logger.info(f'[+]: {atUser} 已被删除为管理员')
                        self.wcf.send_text(f'@{self.wcf.get_alias_in_chatroom(sender, roomId)}\n管理员 [{self.wcf.get_alias_in_chatroom(atUser, roomId)}] 删除成功',
                                    receiver=roomId, aters=sender)
                    else:
                        logger.error(f'[-]: {atUser} 删除管理员失败')
                        self.wcf.send_text(f'@{self.wcf.get_alias_in_chatroom(sender, roomId)}\n管理员 [{self.wcf.get_alias_in_chatroom(atUser, roomId)}] 删除失败',
                                    receiver=roomId, aters=sender)

    def renderAtPrefix(self, atWxId, roomId):
        return f'@{self.wcf.get_alias_in_chatroom(atWxId, roomId)} '
    
    def joinRoomWelcome(self, msg):
        content = msg.content.strip()
        wx_names = None
        if '二维码' in content:
            wx_names = re.search(r'"(?P<wx_names>.*?)"通过扫描', content)
        elif '邀请' in content:
            wx_names = re.search(r'邀请"(?P<wx_names>.*?)"加入了', content)
        if not wx_names:
            return
        wx_names = wx_names.group('wx_names')
        if '、' in wx_names:
            wx_names = wx_names.split('、')
        else:
            wx_names = [wx_names]
        for wx_name in wx_names:
            roomMember = self.wcf.get_chatroom_members(msg.roomid)
            text = self.lta.roomWelcome(room_name=self.getWxName(msg.roomid), invitee=wx_name, index=len(roomMember))
            welcomePrompmtText = self.lta.roomWelcomePrompmt(room_name=self.getWxName(msg.roomid), invitee=wx_name, index=len(roomMember))
            self.wcf.send_text(msg=text, receiver=msg.roomid)
            self.wcf.send_text(msg=welcomePrompmtText, receiver=msg.roomid)
            
    def mainHandle(self, msg):
        roomId = msg.roomid
        sender = msg.sender

        # logger.info(f'收到群消息: {roomId} {self.drs.showWhiteRoom()}')
        # 超管以及管理员功能
        if (self.judgeAdmin(sender, roomId) or self.judgeSuperAdmin(sender)):
            self.AdminFunction(msg)
        
        # 入群欢迎
        if msg.type == 10000:
            self.joinRoomWelcome(msg)

        # 判断是否为白名单群聊
        if not self.drs.searchWhiteRoom(roomId):
            return
        
        # 开始处理消息
        if msg.type == 1: # 文本消息
            self.addChatMsg(sender, self.getWxName(sender), roomId, msg.content)
        if msg.type == 1 and msg.is_at(self.wxid): # 文本消息
            msg.content = re.sub(r"@.*?[\u2005|\s]", "", msg.content) # 删除 content 字符串中以 @ 开头，后跟任意字符，直到遇到中文空格或普通空白字符的部分
            logger.info(f'收到群消息: {msg.content}')
            self.coreFunction(msg)
        elif msg.type == 3: # 图片消息
            self.receiveImgMsg(msg)
        elif msg.type == 49: # 引用消息 公众号/视频号消息
            self.parseMsg(msg)
        
class GhMsgHandler(MsgHandler):
    def __init__(self, wcf):
        super().__init__(wcf)
    
    def mainHandle(self, msg):
        if msg.type != 49:
            return
        gh_id  = msg.sender
        gh_name = self.getWxName(gh_id)
        root = ET.fromstring(msg.content)
        appmsg = root.find('appmsg')
        title = appmsg.find('title').text
        url = appmsg.find('url').text
        
        info = f"公众号：{gh_name}\n标题：{title}\n链接：{url}\n时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}"
        for admin in self.superAdmins:
            msg.sender = admin
            self.sendTextMsg(msg, info)
            # self.wcf.forward_msg(msg.id, admin)