import os
import sqlite3
from datetime import datetime
from utils.common import logger

current_path = os.path.dirname(__file__)
userDb = current_path + '/../data/user.db'
roomDb = current_path + '/../data/room.db'
messageDb = current_path + '/../data/message.db'

def openDb(dbPath, ):
    conn = sqlite3.connect(database=dbPath, )
    cursor = conn.cursor()
    return conn, cursor

def closeDb(conn, cursor):
    cursor.close()
    conn.close()

class DbInitServer:
    def __init__(self):
        pass

    def createTable(self, cursor, table_name, columns):
        """
        :param table_name:  要创建的表名
        :param columns:  要创建的字段名 要符合SQL语法
        :return:
        """
        try:
            cursor.execute(
                f"CREATE TABLE IF NOT EXISTS {table_name} ({columns})"
            )
            return True
        except Exception as e:
            logger.error(f'[-]: 创建数据表出现错误, 错误信息: {e}')
            return False

    def initDb(self, ):
        # 初始化用户数据库 用户表 管理员表
        conn, cursor = openDb(userDb)
        self.createTable(cursor, 'whiteUser', 'wxId varchar(255) PRIMARY KEY, wxName varchar(255)')
        self.createTable(cursor, 'Admin', 'wxId varchar(255) PRIMARY KEY, roomId varchar(255)')
        closeDb(conn, cursor)
        # 初始化群聊数据库 白名单表 推送定时任务表
        conn, cursor = openDb(roomDb)
        self.createTable(cursor, 'whiteRoom', 'roomId varchar(255) PRIMARY KEY, roomName varchar(255)')
        self.createTable(cursor, 'pushRoom', 'taskName varchar(255), roomId varchar(255), roomName varchar(255), PRIMARY KEY (taskName, roomId)')
        self.createTable(cursor, 'responseRoom', 'roomId varchar(255) PRIMARY KEY, roomName varchar(255)')
        closeDb(conn, cursor)
        # 初始化消息数据库 消息表 群聊消息表
        conn, cursor = openDb(messageDb)
        self.createTable(cursor,'chatMessage', 'id INTEGER PRIMARY KEY AUTOINCREMENT, wxId varchar(255), wxName varchar(255), roomId varchar(255), content varchar(255), createTime datetime DEFAULT CURRENT_TIMESTAMP')
        closeDb(conn, cursor)
        logger.info(f'数据库初始化成功！！！')

class DbUserServer:
    def __init__(self):
        pass
    
    def addUser(self, wxId, wxName):
        """
        增加好友
        :param wxId: 微信ID
        :param roomId: 微信昵称
        :return:
        """
        conn, cursor = openDb(userDb)
        try:
            cursor.execute('INSERT INTO whiteUser VALUES (?, ?)', (wxId, wxName))
            conn.commit()
            closeDb(conn, cursor)
            return True
        except Exception as e:
            logger.error(f'增加好友出现错误: {e}')
            closeDb(conn, cursor)
            return False

    def delUser(self, wxId):
        conn, cursor = openDb(userDb)
        try:
            cursor.execute('DELETE FROM whiteUser WHERE wxId=?', (wxId, ))
            conn.commit()
            closeDb(conn, cursor)
            return True
        except Exception as e:
            logger.error(f'删除好友出现错误: {e}')
            closeDb(conn, cursor)
            return False

    def searchUser(self, wxId):
        conn, cursor = openDb(userDb)
        try:
            cursor.execute('SELECT wxId FROM whiteUser WHERE wxId=?', (wxId, ))
            result = cursor.fetchone()
            closeDb(conn, cursor)
            return True if result else False
        except Exception as e:
            logger.error(f'[-]: 查询好友出现错误, 错误信息: {e}')
            closeDb(conn, cursor)
            return False
    
    def showUser(self):
        conn, cursor = openDb(userDb)
        try:
            cursor.execute('SELECT wxId, wxName FROM whiteUser')
            result = cursor.fetchall()
            closeDb(conn, cursor)
            return result
        except Exception as e:
            logger.error(f'获取白名单好友出现错误: {e}')
            closeDb(conn, cursor)
            return []

    def addAdmin(self, wxId, roomId):
        """
        增加管理员
        :param wxId: 微信ID
        :param roomId: 群聊ID
        :return:
        """
        conn, cursor = openDb(userDb)
        try:
            cursor.execute('INSERT INTO Admin VALUES (?, ?)', (wxId, roomId))
            conn.commit()
            closeDb(conn, cursor)
            return True
        except Exception as e:
            logger.error(f'增加管理员出现错误: {e}')
            closeDb(conn, cursor)
            return False

    def delAdmin(self, wxId, roomId):
        conn, cursor = openDb(userDb)
        try:
            cursor.execute('DELETE FROM Admin WHERE wxId=? AND roomId=?', (wxId, roomId))
            conn.commit()
            closeDb(conn, cursor)
            return True
        except Exception as e:
            logger.error(f'删除管理员出现错误: {e}')
            closeDb(conn, cursor)
            return False

    def searchAdmin(self, wxId, roomId):
        conn, cursor = openDb(userDb)
        try:
            cursor.execute('SELECT wxId FROM Admin WHERE wxId=? AND roomId=?', (wxId, roomId))
            result = cursor.fetchone()
            closeDb(conn, cursor)
            if result:
                return True
            else:
                return False
        except Exception as e:
            logger.error(f'[-]: 查询管理员出现错误, 错误信息: {e}')
            closeDb(conn, cursor)
            return False

class DbRoomServer:
    def __init__(self):
        pass

    def addWhiteRoom(self, roomId, roomName):
        conn, cursor = openDb(roomDb)
        try:
            cursor.execute('INSERT INTO whiteRoom VALUES (?, ?)', (roomId, roomName))
            conn.commit()
            closeDb(conn, cursor)
            return True
        except Exception as e:
            logger.error(f'新增白名单群聊出现错误: {e}')
            closeDb(conn, cursor)
            return False

    def delWhiteRoom(self, roomId):
        conn, cursor = openDb(roomDb)
        try:
            cursor.execute('DELETE FROM whiteRoom WHERE roomId=?', (roomId,))
            conn.commit()
            closeDb(conn, cursor)
            return True
        except Exception as e:
            logger.error(f'删除白名单群聊出现错误, 错误信息: {e}')
            closeDb(conn, cursor)
            return False
    
    def searchWhiteRoom(self, roomId):
        conn, cursor = openDb(roomDb)
        try:
            cursor.execute('SELECT roomId FROM whiteRoom WHERE roomId=?', (roomId,))
            result = cursor.fetchone()
            closeDb(conn, cursor)
            return True if result else False
        except Exception as e:
            logger.error(f'[-]: 查询白名单群聊出现错误, 错误信息: {e}')
            closeDb(conn, cursor)
            return False

    def showWhiteRoom(self, ):
        conn, cursor = openDb(roomDb)
        try:
            cursor.execute('SELECT roomId, roomName FROM whiteRoom')
            result = cursor.fetchall()
            closeDb(conn, cursor)
            return result
        except Exception as e:
            logger.error(f'查看所有白名单群聊出现错误: {e}')
            closeDb(conn, cursor)
            return []

    def addPushRoom(self, taskName, roomId, roomName):
        conn, cursor = openDb(roomDb)
        try:
            cursor.execute('INSERT INTO pushRoom VALUES (?, ?, ?)', (taskName, roomId, roomName))
            conn.commit()
            closeDb(conn, cursor)
            return True
        except Exception as e:
            logger.error(f'新增推送任务出现错误: {e}')
            closeDb(conn, cursor)
            return False
    
    def delPushRoom(self, taskName, roomId, roomName):
        conn, cursor = openDb(roomDb)
        try:
            cursor.execute('DELETE FROM pushRoom WHERE taskName=? AND roomId=? AND roomName=?', (taskName, roomId, roomName))
            conn.commit()
            closeDb(conn, cursor)
            return True
        except Exception as e:
            logger.error(f'删除推送任务出现错误: {e}')
            closeDb(conn, cursor)
            return False
    
    def showPushRoom(self, taskName=None):
        conn, cursor = openDb(roomDb)
        try:
            if taskName:
                cursor.execute('SELECT roomId, roomName FROM pushRoom WHERE taskName=?', (taskName,))
            else:
                cursor.execute('SELECT * FROM pushRoom')
            result = cursor.fetchall()
            closeDb(conn, cursor)
            return result
        except Exception as e:
            logger.error(f'查看推送任务出现错误: {e}')
            closeDb(conn, cursor)
            return []
        
    def addResponseRoom(self, roomId, roomName):
        conn, cursor = openDb(roomDb)
        try:
            cursor.execute('INSERT INTO responseRoom VALUES (?, ?)', (roomId, roomName))
            conn.commit()
            closeDb(conn, cursor)
            return True
        except Exception as e:
            logger.error(f'新增回复群出现错误: {e}')
            closeDb(conn, cursor)
            return False
    
    def delResponseRoom(self, roomId):
        conn, cursor = openDb(roomDb)
        try:
            cursor.execute('DELETE FROM responseRoom WHERE roomId=?', (roomId,))
            conn.commit()
            closeDb(conn, cursor)
            return True
        except Exception as e:
            logger.error(f'删除回复群出现错误: {e}')
            closeDb(conn, cursor)
            return False
    
    def showResponseRoom(self):
        conn, cursor = openDb(roomDb)
        try:
            cursor.execute('SELECT roomId, roomName FROM responseRoom')
            result = cursor.fetchall()
            closeDb(conn, cursor)
            return result
        except Exception as e:
            logger.error(f'查看回复群出现错误: {e}')
            closeDb(conn, cursor)
            return []
        
    def searchResponseRoom(self, roomId):
        conn, cursor = openDb(roomDb)
        try:
            cursor.execute('SELECT roomId, roomName FROM responseRoom WHERE roomId=?', (roomId, ))
            result = cursor.fetchone()
            closeDb(conn, cursor)
            return True if result else False
        except Exception as e:
            logger.error(f'查询回复群出现错误: {e}')
            closeDb(conn, cursor)
            return []

class DbMsgServer:
    def __init__(self):
        pass
    def addChatMessage(self, wxId, wxName, roomId, content):
        conn, cursor = openDb(messageDb)
        try:
            today = datetime.now().strftime('%Y-%m-%d')
            cursor.execute('INSERT INTO chatMessage (wxId, wxName, roomId, content) VALUES (?, ?, ?, ?)', (wxId, wxName, roomId, content))
            conn.commit()
            closeDb(conn, cursor)
            return True
        except Exception as e:
            logger.error(f'新增群聊消息出现错误: {e}')
            closeDb(conn, cursor)
            return False
    
    def showChatMessage(self, roomId):
        conn, cursor = openDb(messageDb)
        try:
            #TODO != robot and format create time, token limit input 128k
            cursor.execute("SELECT wxName, content, createTime FROM chatMessage WHERE roomId=? AND ('%Y-%m-%d', createTime, 'localtime') = strftime('%Y-%m-%d', 'now', 'localtime')", (roomId, ))
            result = cursor.fetchall()
            closeDb(conn, cursor)
            return result
        except Exception as e:
            logger.error(f'查看群聊消息出现错误: {e}')
            closeDb(conn, cursor)
            return []

    def showTodayRank(self, roomId):
        conn, cursor = openDb(messageDb)
        try:
            cursor.execute(
                "select wxName, count(*) as count from chatMessage where chatMessage.roomId = ? and strftime('%Y-%m-%d', createTime, 'localtime') = strftime('%Y-%m-%d', 'now', 'localtime') group by wxId order by count desc;",
                (roomId,))
            result = cursor.fetchall()
            closeDb(conn, cursor)
            return result
        except Exception as e:
            logger.error(f'查看排行榜出现错误: {e}')
            closeDb(conn, cursor)
            return []

    def showLastWeekTalkMembers(self, roomId):
        conn, cursor = openDb(messageDb)
        try:
            cursor.execute(
                "select wxid, wxname from chatMessage where strftime('%Y-%m-%d', createTime) > strftime('%Y-%m-%d', DATE('now', '-7 day', 'localtime')) AND roomId = ? GROUP BY wxId",
                (roomId,))
            result = cursor.fetchall()
            closeDb(conn, cursor)
            return result
        except Exception as e:
            logger.error(f'查看群聊消息出现错误: {e}')
            closeDb(conn, cursor)
            return []

if __name__ == '__main__':
    Dis = DbInitServer()
    Dis.initDb()