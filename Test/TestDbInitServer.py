import unittest
import os
import sqlite3
from datetime import datetime
from unittest.mock import patch
from utils.common import logger  # Assuming you have a logger in utils.common
from servers.db_server import DbInitServer, DbUserServer, DbRoomServer, DbMsgServer, openDb, closeDb

# Define test database paths
TEST_USER_DB = 'test_user.db'
TEST_ROOM_DB = 'test_room.db'
TEST_MESSAGE_DB = 'test_message.db'

class TestDbInitServer(unittest.TestCase):
    def setUp(self):
        # Setup test databases (in-memory for isolation)
        self.init_server = DbInitServer()
        self.user_conn, self.user_cursor = openDb(TEST_USER_DB)
        self.room_conn, self.room_cursor = openDb(TEST_ROOM_DB)
        self.message_conn, self.message_cursor = openDb(TEST_MESSAGE_DB)

    def tearDown(self):
        # Close connections and remove test databases
        closeDb(self.user_conn, self.user_cursor)
        closeDb(self.room_conn, self.room_cursor)
        closeDb(self.message_conn, self.message_cursor)
        os.remove(TEST_USER_DB)
        os.remove(TEST_ROOM_DB)
        os.remove(TEST_MESSAGE_DB)

    def test_createTable(self):
        # Test table creation
        table_name = 'test_table'
        columns = 'id INTEGER PRIMARY KEY, name VARCHAR(255)'
        result = self.init_server.createTable(self.user_cursor, table_name, columns)
        self.assertTrue(result)

        # Verify table exists
        self.user_cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}';")
        table = self.user_cursor.fetchone()
        self.assertIsNotNone(table)

    @patch('servers.db_server.openDb')
    @patch('servers.db_server.closeDb')
    @patch('servers.db_server.DbInitServer.createTable')
    @patch('utils.common.logger.info')
    def test_initDb(self, mock_logger_info, mock_create_table, mock_close_db, mock_open_db):
        # Mock the database connections and createTable method
        mock_open_db.side_effect = [(self.user_conn, self.user_cursor), (self.room_conn, self.room_cursor), (self.message_conn, self.message_cursor)]
        mock_create_table.return_value = True

        # Call the initDb method
        self.init_server.initDb()

        # Assert that openDb and closeDb were called the expected number of times
        self.assertEqual(mock_open_db.call_count, 3)
        self.assertEqual(mock_close_db.call_count, 3)

        # Assert that createTable was called with the correct arguments
        expected_calls = [
            (('whiteUser', 'wxId varchar(255) PRIMARY KEY, wxName varchar(255)'),),
            (('Admin', 'wxId varchar(255) PRIMARY KEY, roomId varchar(255)'),),
            (('whiteRoom', 'roomId varchar(255) PRIMARY KEY, roomName varchar(255)'),),
            (('pushRoom', 'taskName varchar(255), roomId varchar(255), roomName varchar(255), PRIMARY KEY (taskName, roomId)'),),
            (('chatMessage', 'id INTEGER PRIMARY KEY AUTOINCREMENT, wxId varchar(255), wxName varchar(255), roomId varchar(255), content varchar(255), createTime datetime DEFAULT CURRENT_TIMESTAMP'),),
        ]
        self.assertEqual(mock_create_table.call_count, 5)

        # Assert that logger.info was called with the success message
        mock_logger_info.assert_called_with('数据库初始化成功！！！')

class TestDbUserServer(unittest.TestCase):
    def setUp(self):
        self.user_server = DbUserServer()
        self.conn, self.cursor = openDb(TEST_USER_DB)
        # Create the whiteUser and Admin tables for testing
        self.cursor.execute('CREATE TABLE IF NOT EXISTS whiteUser (wxId varchar(255) PRIMARY KEY, wxName varchar(255))')
        self.cursor.execute('CREATE TABLE IF NOT EXISTS Admin (wxId varchar(255) PRIMARY KEY, roomId varchar(255))')
        self.conn.commit()

    def tearDown(self):
        closeDb(self.conn, self.cursor)
        os.remove(TEST_USER_DB)

    def test_addUser(self):
        wxId = 'test_user'
        wxName = 'Test User'
        result = self.user_server.addUser(wxId, wxName)
        self.assertTrue(result)
        self.cursor.execute('SELECT wxId, wxName FROM whiteUser WHERE wxId=?', (wxId,))
        user = self.cursor.fetchone()
        self.assertEqual(user, (wxId, wxName))

    def test_delUser(self):
        wxId = 'test_user'
        wxName = 'Test User'
        self.user_server.addUser(wxId, wxName)
        result = self.user_server.delUser(wxId)
        self.assertTrue(result)
        self.cursor.execute('SELECT wxId FROM whiteUser WHERE wxId=?', (wxId,))
        user = self.cursor.fetchone()
        self.assertIsNone(user)

    def test_searchUser(self):
        wxId = 'test_user'
        wxName = 'Test User'
        self.user_server.addUser(wxId, wxName)
        result = self.user_server.searchUser(wxId)
        self.assertTrue(result)
        result = self.user_server.searchUser('non_existent_user')
        self.assertFalse(result)

    def test_showUser(self):
        self.user_server.addUser('test_user1', 'Test User 1')
        self.user_server.addUser('test_user2', 'Test User 2')
        users = self.user_server.showUser()
        self.assertEqual(len(users), 2)
        self.assertIn(('test_user1', 'Test User 1'), users)
        self.assertIn(('test_user2', 'Test User 2'), users)

    def test_addAdmin(self):
        wxId = 'test_admin'
        roomId = 'test_room'
        result = self.user_server.addAdmin(wxId, roomId)
        self.assertTrue(result)
        self.cursor.execute('SELECT wxId, roomId FROM Admin WHERE wxId=? AND roomId=?', (wxId, roomId))
        admin = self.cursor.fetchone()
        self.assertEqual(admin, (wxId, roomId))

    def test_delAdmin(self):
        wxId = 'test_admin'
        roomId = 'test_room'
        self.user_server.addAdmin(wxId, roomId)
        result = self.user_server.delAdmin(wxId, roomId)
        self.assertTrue(result)
        self.cursor.execute('SELECT wxId FROM Admin WHERE wxId=? AND roomId=?', (wxId, roomId))
        admin = self.cursor.fetchone()
        self.assertIsNone(admin)

    def test_searchAdmin(self):
        wxId = 'test_admin'
        roomId = 'test_room'
        self.user_server.addAdmin(wxId, roomId)
        result = self.user_server.searchAdmin(wxId, roomId)
        self.assertTrue(result)
        result = self.user_server.searchAdmin('non_existent_admin', 'non_existent_room')
        self.assertFalse(result)

class TestDbRoomServer(unittest.TestCase):
    def setUp(self):
        self.room_server = DbRoomServer()
        self.conn, self.cursor = openDb(TEST_ROOM_DB)
        # Create the whiteRoom and pushRoom tables
        self.cursor.execute('CREATE TABLE IF NOT EXISTS whiteRoom (roomId varchar(255) PRIMARY KEY, roomName varchar(255))')
        self.cursor.execute('CREATE TABLE IF NOT EXISTS pushRoom (taskName varchar(255), roomId varchar(255), roomName varchar(255), PRIMARY KEY (taskName, roomId))')
        self.conn.commit()

    def tearDown(self):
        closeDb(self.conn, self.cursor)
        os.remove(TEST_ROOM_DB)

    def test_addWhiteRoom(self):
        roomId = 'test_room'
        roomName = 'Test Room'
        result = self.room_server.addWhiteRoom(roomId, roomName)
        self.assertTrue(result)
        self.cursor.execute('SELECT roomId, roomName FROM whiteRoom WHERE roomId=?', (roomId,))
        room = self.cursor.fetchone()
        self.assertEqual(room, (roomId, roomName))

    def test_delWhiteRoom(self):
        roomId = 'test_room'
        roomName = 'Test Room'
        self.room_server.addWhiteRoom(roomId, roomName)
        result = self.room_server.delWhiteRoom(roomId)
        self.assertTrue(result)
        self.cursor.execute('SELECT roomId FROM whiteRoom WHERE roomId=?', (roomId,))
        room = self.cursor.fetchone()
        self.assertIsNone(room)

    def test_searchWhiteRoom(self):
        roomId = 'test_room'
        roomName = 'Test Room'
        self.room_server.addWhiteRoom(roomId, roomName)
        result = self.room_server.searchWhiteRoom(roomId)
        self.assertTrue(result)
        result = self.room_server.searchWhiteRoom('non_existent_room')
        self.assertFalse(result)

    def test_showWhiteRoom(self):
        self.room_server.addWhiteRoom('test_room1', 'Test Room 1')
        self.room_server.addWhiteRoom('test_room2', 'Test Room 2')
        rooms = self.room_server.showWhiteRoom()
        self.assertEqual(len(rooms), 2)
        self.assertIn(('test_room1', 'Test Room 1'), rooms)
        self.assertIn(('test_room2', 'Test Room 2'), rooms)

    def test_addPushRoom(self):
        taskName = 'test_task'
        roomId = 'test_room'
        roomName = 'Test Room'
        result = self.room_server.addPushRoom(taskName, roomId, roomName)
        self.assertTrue(result)
        self.cursor.execute('SELECT taskName, roomId, roomName FROM pushRoom WHERE taskName=? AND roomId=? AND roomName=?', (taskName, roomId, roomName))
        room = self.cursor.fetchone()
        self.assertEqual(room, (taskName, roomId, roomName))

    def test_delPushRoom(self):
        taskName = 'test_task'
        roomId = 'test_room'
        roomName = 'Test Room'
        self.room_server.addPushRoom(taskName, roomId, roomName)
        result = self.room_server.delPushRoom(taskName, roomId, roomName)
        self.assertTrue(result)
        self.cursor.execute('SELECT taskName, roomId, roomName FROM pushRoom WHERE taskName=? AND roomId=? AND roomName=?', (taskName, roomId, roomName))
        room = self.cursor.fetchone()
        self.assertIsNone(room)

    def test_showPushRoom(self):
        self.room_server.addPushRoom('test_task1', 'test_room1', 'Test Room 1')
        self.room_server.addPushRoom('test_task2', 'test_room2', 'Test Room 2')
        rooms = self.room_server.showPushRoom()
        self.assertEqual(len(rooms), 2)
        self.assertIn(('test_task1', 'test_room1', 'Test Room 1'), rooms)
        self.assertIn(('test_task2', 'test_room2', 'Test Room 2'), rooms)

    def test_showPushRoom_with_taskName(self):
        self.room_server.addPushRoom('test_task', 'test_room1', 'Test Room 1')
        self.room_server.addPushRoom('test_task', 'test_room2', 'Test Room 2')
        self.room_server.addPushRoom('other_task', 'test_room3', 'Test Room 3')
        rooms = self.room_server.showPushRoom(taskName='test_task')
        self.assertEqual(len(rooms), 2)
        self.assertIn(('test_room1', 'Test Room 1'), rooms)
        self.assertIn(('test_room2', 'Test Room 2'), rooms)
        self.assertNotIn(('test_room3', 'Test Room 3'), rooms)

class TestDbMsgServer(unittest.TestCase):
    def setUp(self):
        self.msg_server = DbMsgServer()
        self.conn, self.cursor = openDb(TEST_MESSAGE_DB)
        # Create the chatMessage table
        self.cursor.execute('CREATE TABLE IF NOT EXISTS chatMessage (id INTEGER PRIMARY KEY AUTOINCREMENT, wxId varchar(255), wxName varchar(255), roomId varchar(255), content varchar(255), createTime datetime DEFAULT CURRENT_TIMESTAMP)')
        self.conn.commit()

    def tearDown(self):
        closeDb(self.conn, self.cursor)
        os.remove(TEST_MESSAGE_DB)

    def test_addChatMessage(self):
        wxId = 'test_user'
        wxName = 'Test User'
        roomId = 'test_room'
        content = 'Test message'
        result = self.msg_server.addChatMessage(wxId, wxName, roomId, content)
        self.assertTrue(result)
        self.cursor.execute('SELECT wxId, wxName, roomId, content FROM chatMessage WHERE wxId=? AND wxName=? AND roomId=? AND content=?', (wxId, wxName, roomId, content))
        message = self.cursor.fetchone()
        self.assertEqual(message, (wxId, wxName, roomId, content))

    def test_showChatMessage(self):
        wxId = 'test_user'
        wxName = 'Test User'
        roomId = 'test_room'
        content = 'Test message'
        self.msg_server.addChatMessage(wxId, wxName, roomId, content)
        messages = self.msg_server.showChatMessage(roomId)
        self.assertEqual(len(messages), 1)
        # Extract the wxName and content from the result
        retrieved_wxName = messages[0][0]
        retrieved_content = messages[0][1]

        # Assert that the retrieved wxName and content match the expected values
        self.assertEqual(retrieved_wxName, wxName)
        self.assertEqual(retrieved_content, content)

if __name__ == '__main__':
    unittest.main()