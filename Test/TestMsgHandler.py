import unittest
from unittest.mock import MagicMock, patch
from servers.msg_server import MsgHandler
from utils.prompt import intentions_list
import xml.etree.ElementTree as ET

class TestMsgHandler(unittest.TestCase):

    def setUp(self):
        # Mock the WCF class and its methods
        self.mock_wcf = MagicMock()
        self.mock_wcf.get_self_wxid.return_value = 'test_wxid'
        self.mock_wcf.get_user_info.return_value = {'name': 'test_name'}
        self.mock_wcf.query_sql.return_value = [{'NickName': 'Test User'}]
        self.mock_wcf.get_alias_in_chatroom.return_value = 'Test Alias'

        # Mock the database server classes
        self.mock_dus = MagicMock()
        self.mock_drs = MagicMock()
        self.mock_dms = MagicMock()

        # Mock the API server classes
        self.mock_lta = MagicMock()
        self.mock_lra = MagicMock()
        self.mock_aps = MagicMock()

        # Mock the returnConfigData function
        self.mock_returnConfigData = MagicMock(return_value={
            'Administrators': ['admin1', 'admin2'],
            'adminFunctionWord': {'addWhiteWord': '!add', 'delWhiteWord': '!del'},
            'roomKeyWord': {'join': 'test_room_id'},
            'systemConfig': {'robotName': 'TestBot'},
            'customKeyWord': {'gzhRetrive': ['gzh']}
        })

        # Patch the necessary classes and functions
        self.patch_dus = patch('servers.msg_server.DbUserServer', return_value=self.mock_dus)
        self.patch_drs = patch('servers.msg_server.DbRoomServer', return_value=self.mock_drs)
        self.patch_dms = patch('servers.msg_server.DbMsgServer', return_value=self.mock_dms)
        self.patch_lta = patch('servers.msg_server.LLMTaskApi', return_value=self.mock_lta)
        self.patch_lra = patch('servers.msg_server.LLMResponseApi', return_value=self.mock_lra)
        self.patch_aps = patch('servers.msg_server.ApiServer', return_value=self.mock_aps)
        self.patch_returnConfigData = patch('servers.msg_server.returnConfigData', new=self.mock_returnConfigData)

        # Start the patches
        self.patch_dus.start()
        self.patch_drs.start()
        self.patch_dms.start()
        self.patch_lta.start()
        self.patch_lra.start()
        self.patch_aps.start()
        self.patch_returnConfigData.start()

        # Create an instance of MsgHandler with the mock WCF
        self.msg_handler = MsgHandler(self.mock_wcf)

    def tearDown(self):
        # Stop the patches
        self.patch_dus.stop()
        self.patch_drs.stop()
        self.patch_dms.stop()
        self.patch_lta.stop()
        self.patch_lra.stop()
        self.patch_aps.stop()
        self.patch_returnConfigData.stop()

    def test_judgeSuperAdmin(self):
        self.assertTrue(self.msg_handler.judgeSuperAdmin('admin1'))
        self.assertFalse(self.msg_handler.judgeSuperAdmin('non_admin'))

    def test_getWxName(self):
        name = self.msg_handler.getWxName('test_wxid')
        self.assertEqual(name, 'Test User')
        self.mock_wcf.query_sql.assert_called_with("MicroMsg.db",
                                                "SELECT NickName FROM Contact WHERE UserName = 'test_wxid';")

    def test_getWxId(self):
        self.mock_wcf.query_sql.return_value = [{'UserName': 'wxid_test'}]
        wxid = self.msg_handler.getWxId('test_wxname')
        self.assertEqual(wxid, 'wxid_test')
        self.mock_wcf.query_sql.assert_called_with("MicroMsg.db",
                                                "SELECT UserName FROM Contact WHERE NickName = 'test_wxname';")

    def test_getAtData(self):
        # Mock the message object and its attributes
        mock_msg = MagicMock()
        mock_msg.content = '@TestAlias Hello'
        mock_msg.xml = '<msg><appmsg><title>test</title></appmsg><atuserlist>user1,user2</atuserlist></msg>'
        mock_msg.roomid = 'test_room_id'

        at_user_lists, no_at_msg = self.msg_handler.getAtData(mock_msg)

        self.assertEqual(at_user_lists, ['user1', 'user2'])
        self.assertEqual(no_at_msg, 'Hello')
        self.mock_wcf.get_alias_in_chatroom.assert_called()

    def test_sendTextMsg_single(self):
        mock_msg = MagicMock()
        mock_msg.sender = 'test_sender'
        mock_msg.roomid = 'test_room_id'
        mock_msg.from_group.return_value = False

        self.msg_handler.sendTextMsg(mock_msg, 'Hello')
        self.mock_wcf.send_text.assert_called_with(msg='Hello', receiver='test_sender')

    def test_sendTextMsg_group(self):
        mock_msg = MagicMock()
        mock_msg.sender = 'test_sender'
        mock_msg.roomid = 'test_room_id'
        mock_msg.from_group.return_value = True

        self.msg_handler.sendTextMsg(mock_msg, 'Hello')
        self.mock_wcf.send_text.assert_called_with(msg='@Test Alias Hello', receiver='test_room_id', aters='test_sender')

    @patch('servers.msg_server.returnPicCacheFolder', return_value='/tmp')
    @patch('servers.msg_server.shutil.move')
    @patch('servers.msg_server.os.path.splitext', return_value=('', '.jpg'))
    def test_receiveImgMsg(self, mock_splitext, mock_move, mock_returnPicCacheFolder):
        mock_msg = MagicMock()
        mock_msg.extra = 'test_extra'
        mock_msg.id = 'test_id'
        mock_msg.sender = 'test_sender'
        mock_msg.roomid = 'test_room_id'
        self.mock_wcf.download_image.return_value = '/tmp/test_image.jpg'
        self.mock_lra.isAdPic.return_value = '否'

        self.msg_handler.receiveImgMsg(mock_msg)

        self.mock_wcf.download_image.assert_called_with('test_id', 'test_extra', '/tmp')
        self.mock_lra.isAdPic.assert_called()
        mock_move.assert_called()

    def test_triggerFunction_gzhRetrive(self):
        mock_msg = MagicMock()
        mock_msg.content = 'gzh test content'
        chatid = 'test_chat_id'
        self.mock_aps.get_yuanqi.return_value = 'test response'

        result = self.msg_handler.triggerFunction(mock_msg, 'gzhRetrive', ['gzh'], chatid)

        self.assertTrue(result)
        self.mock_aps.get_yuanqi.assert_called_with('gzh test content')
        self.mock_lra.updateMessage.assert_called_with(chatid, ['gzh test content', 'test response'])
        self.mock_dms.addChatMessage.assert_called_with('test_wxid', 'test_name', chatid, 'test response')

    def test_triggerFunction_difySearch(self):
        mock_msg = MagicMock()
        mock_msg.content = 'search test content'
        chatid = 'test_chat_id'
        self.mock_lta.difySearch.return_value = 'test response'
        self.mock_wcf.send_text.return_value = 0

        result = self.msg_handler.triggerFunction(mock_msg, 'difySearch', ['search'], chatid)

        self.assertTrue(result)
        self.mock_lta.difySearch.assert_called_with('search test content', user='TestBot')
        self.mock_lra.updateMessage.assert_called_with(chatid, ['search test content', 'test response'])
        self.mock_dms.addChatMessage.assert_called_with('test_wxid', 'test_name', chatid, 'test response')

    def test_triggerFunction_beikeRetrive_guapai(self):
        mock_msg = MagicMock()
        mock_msg.content = '挂牌12345'
        self.mock_wcf.send_text.return_value = 0

        result = self.msg_handler.triggerFunction(mock_msg, 'beikeRetrive', ['挂牌', '成交'], 'test_chat_id')

        self.assertTrue(result)
        self.mock_wcf.send_text.assert_called_with(msg='https://yc.ke.com/ershoufang/12345.html', receiver=mock_msg.sender)

    def test_triggerFunction_beikeRetrive_chengjiao(self):
        mock_msg = MagicMock()
        mock_msg.content = '成交12345'
        self.mock_wcf.send_text.return_value = 0

        result = self.msg_handler.triggerFunction(mock_msg, 'beikeRetrive', ['挂牌', '成交'], 'test_chat_id')

        self.assertTrue(result)
        self.mock_wcf.send_text.assert_called_with(msg='https://yc.ke.com/chengjiao/12345.html', receiver=mock_msg.sender)

    def test_triggerFunction_unknown(self):
        mock_msg = MagicMock()
        mock_msg.content = 'unknown test content'
        self.mock_wcf.send_text.return_value = 0

        result = self.msg_handler.triggerFunction(mock_msg, 'unknown', ['unknown'], 'test_chat_id')

        self.assertTrue(result)
        self.mock_wcf.send_text.assert_called_with(msg='[-]: 未知的触发器类型: unknown, 请检查配置', receiver=mock_msg.sender)

    def test_getOrUpdateDifyImgConId(self):
        chatid = 'test_chat_id'
        conId = 'test_con_id'

        # Test get without setting
        result = self.msg_handler.getOrUpdateDifyImgConId(chatid)
        self.assertEqual(result, '')

        # Test update and get
        result = self.msg_handler.getOrUpdateDifyImgConId(chatid, conId)
        self.assertEqual(result, conId)

        # Test get after setting
        result = self.msg_