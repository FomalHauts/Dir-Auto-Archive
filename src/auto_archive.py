import sys
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR
import logging
import datetime
import os
import shutil

cur_dir_path = os.path.dirname(os.path.abspath(__file__))
root_path = os.path.dirname(cur_dir_path)

sys.path.extend([cur_dir_path, root_path])
from config import config


# 配置日志显示
logging.basicConfig(level=logging.INFO,
                 format='%(asctime)s %(filename)s[line:%(lineno)d] %(levelname)s %(message)s',
                 datefmt='%Y-%m-%d %H:%M:%S',
                filename=os.path.join(root_path, 'log', 'auto_archive.log'),
                filemode='a')

class auto_archive:

    def __init__(self) -> None:
        self.archive_pairs = {}     # {format: archive_path}
        self.archive_dirs = []      # archive_path list

    def set_archive_dirs(self):
        """判断conf文件中archive_path路径是否存在, 若不存在则新建文件夹，并生成路径列表
        """
        for archive_params in config.values():
            if "archive_path" in archive_params.keys():
                archive_path = archive_params['archive_path']
                if not os.path.exists(archive_path):
                    os.mkdir(archive_path)
                self.archive_dirs.append(archive_path)

    def archive_single(self, file_path: str, cur_time: str):
        """归档单个文件
        Args:
            file_path (str): 待归档文件路径
            cur_time (str): 当前时间
        """
        file_real_format = file_path.rsplit(".",1)[1]   # 获取文件的真实后缀,即type
        # 判断该文件是否出现在列举的type中,若不在将其移others文件夹
        if any(file_real_format in file_format for file_format in self.archive_pairs.keys()):
            # 判断该文件具体type,并判断dest路径是否存在同名文件
            for file_format, archive_path in self.archive_pairs.items():
                # 获取format元组,格式示例:("jpg","png")
                file_format = tuple([format.strip() for format in file_format.split(",")])
                if file_path.endswith(file_format):
                    new_file_path = self.exist_check(file_path, archive_path, "plain_file", cur_time)
                    shutil.move(new_file_path, archive_path)
        else:
            # 若不在设定的format中, 将其归档至others文件夹
            new_file_path = self.exist_check(file_path, config['others']['archive_path'], "plain_file", cur_time)
            shutil.move(new_file_path, config['others']['archive_path'])


    def archive_all(self):
        """归档所有文件(夹)
        """
        root_path = config['root_path']['root_path']
        cur_time = self.get_cur_time()

        for file in os.listdir(root_path):
            file_path = os.path.join(root_path, file)
            # 判断是否为文件夹，且文件夹不是准备归档的文件夹路径
            if  os.path.isdir(file_path):
                if file_path not in self.archive_dirs:
                    new_file_path = self.exist_check(file_path, config['dir']['archive_path'], "dir", cur_time)
                    shutil.move(new_file_path, config['dir']['archive_path'])
            else:
                # 若不是文件夹，则归档单个文件
                self.archive_single(file_path,cur_time)

    def get_archive_pairs(self):
        """获取归档参数，即{format: archive_path}
        """
        for archive_params in config.values():
            if "format" in archive_params.keys() and "archive_path" in archive_params.keys():
                format, archive_path = archive_params['format'], archive_params['archive_path']
                self.archive_pairs.update({format: archive_path})

    def exist_check(self, cur_file_path: str, archive_path: str, file_type: str, cur_time ):
        """判断待归档的文件(夹)是否已归档过,若归档过则加时间戳

        Args:
            cur_file_path (str): 当前文件路径
            archive_path (str): 待归档路径
            file_type (str): 文件类型: 文件夹:dir/普通文件:plain_file
            cur_time ([type]): 当前时间

        Returns:
            str : 当前文件路径(新)
        """
        file_name = cur_file_path.rsplit("/", 1)[1]
        new_file_path = os.path.join(archive_path, file_name)
        if os.path.exists(new_file_path):
            if file_type == "plain_file":
                new_file_path = f"{cur_file_path.rsplit('.', 1)[0]}_{cur_time}.{cur_file_path.rsplit('.', 1)[1]}"
            elif file_type == "dir":
                new_file_path = f"{cur_file_path}_{cur_time}"
                print(cur_time)
                print(new_file_path)
            os.rename(cur_file_path, new_file_path)
            return new_file_path
        return cur_file_path


    @staticmethod
    def get_cur_time() -> str:
        cur_time = datetime.datetime.now().strftime('%Y-%m-%d-%H-%M-%S')
        return cur_time

        
    def launch(self):
        self.set_archive_dirs()
        self.get_archive_pairs()
        self.archive_all()

def my_listener(event):
    if event.exception:
        logging.error('auto archive failed!!!')
    else:
        logging.info('auto archive success...')

if __name__ == '__main__':
    scheduler = BlockingScheduler()
    auto_archiver = auto_archive()
    # 添加定时任务:每天晚上19点执行一次
    scheduler.add_job(func=auto_archiver.launch, trigger='cron', hour=19, minute=0, id='cron_task')

    # 配置任务执行完成和执行错误的监听
    scheduler.add_listener(my_listener, EVENT_JOB_EXECUTED | EVENT_JOB_ERROR)

    # 设置日志
    scheduler._logger = logging

    scheduler.start()