import datetime
import CyclicList
import DataPersistence
from RWLock import RWLock
import copy

USER = "user"
PASSWORD = "geheim"
THUMBNAIL_PATH = "data/recordings/thumbnails/"


class PipcoDaten:
    __m_instance = None
    m_lock = None

    def __init__(self):
        if self.__m_instance is not None:
            raise Exception("Something fucked up - Trying to init second instance")
        else:
            self.m_data_persistence = DataPersistence.DataPersistence(self)
            self.__m_emails_lock = RWLock()
            self.__m_log_lock = RWLock()
            self.__m_setting_lock = RWLock()
            self.__m_settings = self.m_data_persistence.load_settings()
            self.__m_emails = self.m_data_persistence.load_emails()
            self.__m_log = self.m_data_persistence.load_logs()
            if not self.__m_log:
                self.__m_log = AutoIdDict()
            if not self.__m_emails:
                self.__m_emails = AutoIdDict()
            if not self.__m_settings:
                self.__m_settings = Settings()
            self.__m_instance = self
            self.__m_image = None
            self.__m_user = USER
            self.__m_password = PASSWORD

    @staticmethod
    def get_instance():
        if PipcoDaten.__m_instance is None:
            PipcoDaten.__m_instance = PipcoDaten()
        return PipcoDaten.__m_instance

    def toggle_mail_notify(self, id):
        self.__m_emails_lock.writer_acquire()
        state = not self.__m_emails[int(id)].notify
        self.__m_emails[int(id)].notify = state
        self.m_data_persistence.save_emails(self.__m_emails)
        self.__m_emails_lock.writer_release()
        return state

    def add_mail(self, address):
        self.__m_emails_lock.writer_acquire()
        ret = self.__m_emails.append(Mail(address))
        self.m_data_persistence.save_emails(self.__m_emails)
        self.__m_emails_lock.writer_release()
        return ret

    def remove_mail(self, id):
        self.__m_emails_lock.writer_acquire()
        self.__m_emails.__delitem__(id)
        self.m_data_persistence.save_emails(self.__m_emails)
        self.__m_emails_lock.writer_release()
        return id

    def get_mails(self):
        self.__m_emails_lock.reader_acquire()
        ret = copy.deepcopy(self.__m_emails)
        self.__m_emails_lock.reader_release()
        return ret

    def get_settings(self):
        self.__m_setting_lock.reader_acquire()
        ret = copy.copy(self.__m_settings)
        self.__m_setting_lock.reader_release()
        return ret

    def change_settings(self, sensitivity, brightness, contrast, streamaddress):
        self.__m_setting_lock.writer_acquire()
        ret = {}
        if sensitivity:
            ret["sensitivity"] = sensitivity
            self.__m_settings.sensitivity = float(sensitivity)
        if brightness:
            ret["brightness"] = brightness
            self.__m_settings.brightness = float(brightness)
        if contrast:
            ret["contrast"] = contrast
            self.__m_settings.contrast = float(contrast)
        if streamaddress:
            ret["streamaddress"] = streamaddress
            self.__m_settings.streamaddress = streamaddress
        self.m_data_persistence.save_settings(self.__m_settings)
        self.__m_setting_lock.writer_release()
        return ret

    def set_image(self, image):
        self.__m_image = image

    def get_image(self):
        return self.__m_image

    def get_log_page(self, page, batchsize):
        self.__m_log_lock.reader_acquire()
        selected = {}
        try:
            for idx, key in enumerate(sorted(self.__m_log.keys(), reverse=True)[int(page)*int(batchsize):]):
                selected[key] = copy.copy(self.__m_log[key])
                if int(batchsize)-1 == idx:
                    return selected
            return selected
        finally:
            self.__m_log_lock.reader_release()

    def add_log(self):
        self.__m_log_lock.writer_acquire()
        idx = self.__m_log.get_free_index()
        idx = self.__m_log.append(Log(idx))
        self.m_data_persistence.save_logs(self.__m_log)
        self.__m_log_lock.writer_release()
        return idx

    def check_login(self, user, password):
        return self.__m_user == user and self.__m_password == password

    def remove_log(self, id):
        self.__m_log_lock.writer_acquire()
        self.__m_log.__delitem__(id)
        self.__m_log_lock.writer_release()
        return id

class AutoIdDict(dict):

    def __init__(self, list=None):
        if list:
            for val in list:
                self[val.id] = val
        super(dict, self).__init__()

    def append(self, val):
        if val in self.values():
            return -1
        index = self.get_free_index()
        val.id = index
        self[index] = val
        return index

    def get_free_index(self):
        if self:
            ret = sorted(self.keys())[-1]+1
            return ret
        else:
            return 0


class Mail:
    def __init__(self, address, id=0, notify=True):
        self.address = address
        self.notify = notify
        self.id = id

    def __eq__(self, other):
        return self.address == other.address and \
               self.notify == other.notify


class Log:
    def __init__(self, id=0, timestamp=None, message=""):
        if not timestamp:
            timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.message = message
        self.timestamp = timestamp
        self.id = id


class Settings:

    def __init__(self, sensitivity=0.5, brightness=0.5, contrast=0.5, streamaddress=""):
        self.sensitivity = sensitivity
        self.streamaddress = streamaddress
        self.brightness = brightness
        self.contrast = contrast
