import unittest
import logging
import os
import shutil
import datetime

# from naspi import load_configuration
# naspi = __import__("naspi")
# from naspi.naspi import *
import naspi.naspi as naspi

import logging
import sys

logger = logging.getLogger()
logger.setLevel(logging.INFO)

handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)


class TestMain(unittest.TestCase):
    def test_main_help(self):
        """
        Test the main help function
        """
        result = os.system("python3 naspi/naspi.py -h")
        self.assertEqual(result, 0)

    def test_main_nomode(self):
        """
        Test the main help function
        """
        result = os.system("python3 naspi/naspi.py")
        self.assertEqual(result, 512)

    def test_main_novalidmode(self):
        """
        Test the main help function
        """
        result = os.system("python3 naspi/naspi.py -m notvalid -c /tmp/conf.json")
        self.assertEqual(result, 512)

    def test_main_noconfig(self):
        """
        Test the main help function
        """
        result = os.system("python3 naspi/naspi.py -m system")
        self.assertEqual(result, 512)

class TestConf(unittest.TestCase):
    def test_load_conf(self):
        """
        Test the load configuration function
        """

        result = naspi.load_configuration("tests/conf.json")
        self.assertNotEqual(result, None)
    def test_load_conf_no_file(self):
        """
        Test the load configuration function
        """

        # result = load_configuration("tests/noconf.json")
        # self.assertEqual(result, FileNotFoundError)
        # self.assertEqual(result, 2)
        with self.assertRaises(FileNotFoundError):
            result = naspi.load_configuration("tests/noconf.json")

class TestRunCmd(unittest.TestCase):

    def test_run_cmd(self):
        """
        Test the run shell cmd
        """

        code,msg = naspi.run_shell_command("ls")
        self.assertEqual(code, 0)

    def test_run_cmd_ko(self):
        """
        Test the run shell cmd
        """

        code,msg = naspi.run_shell_command("exit 1")
        self.assertNotEqual(code, 0)

class TestDateCommands(unittest.TestCase):

    def test_today_time(self):
        """
        Test the today_time 
        """
        time = naspi.today_time()
        self.assertEqual(isinstance(time, str), True)
        self.assertEqual(len(time), 19)

    def test_today_date(self):
        """
        Test the today_date 
        """
        time = naspi.today_date()
        self.assertEqual(isinstance(time, str), True)
        self.assertEqual(len(time), 10)

class TestServerMetrics(unittest.TestCase):
    global path
    path = "/tmp/naspi_test"

    def test_get_server_metrics(self):
        """
        Test the get_server_metrics
        """
        output = naspi.open_or_init_output_file(path)
        output = naspi.get_server_metrics(output)
        logger.info(output)
        self.assertEqual(len(output['server']['last_run']), 19)

class TestAnalyzeDisks(unittest.TestCase):
    global path
    path = "/tmp/naspi_test"

    def test_analyze_disks(self):
        """
        Test analyze_disks
        """
        output = naspi.open_or_init_output_file(path)
        output = naspi.analyze_disks([" /"],output)
        logger.info(output)
        self.assertEqual(output['disks']['all_disks_ok'], True)
        
        output = naspi.analyze_disks(["/nodisk_here"],output)
        logger.info(output)
        self.assertEqual(output['disks']['all_disks_ok'], False)

class TestAnalyzeLocalFiles(unittest.TestCase):
    global NUMBER_OF_FILES
    global path
    NUMBER_OF_FILES=6
    path = "/tmp/naspi_test"

    # global NUMBER_DAYS_RETENTION
    # global MIN_DELAY_BETWEEN_SYNCS_SECONDS
    # global working_dir
    global folder_to_sync_locally
    global configuration

    disks_list,folder_to_sync_locally,folders_to_sync_s3,configuration = naspi.load_configuration("tests/conf.json")
    # NUMBER_DAYS_RETENTION = configuration.get('NUMBER_DAYS_RETENTION')
    # MIN_DELAY_BETWEEN_SYNCS_SECONDS = configuration.get('MIN_DELAY_BETWEEN_SYNCS_SECONDS')
    # working_dir = configuration.get('working_dir')
    
    def setUp(self):
        try:
            os.makedirs("{}/srcdir".format(path))
            os.makedirs("{}/dstdir".format(path))
        except FileExistsError:
            pass
        for i in range(NUMBER_OF_FILES):
            f= open("{}/srcdir/{}".format(path,str(i)),"w+")
            f.close()

    def test_count_files(self):
        """
        Test the count_files_in_dir
        """
        count = naspi.count_files_in_dir(path,[''])
        self.assertEqual(count, NUMBER_OF_FILES)
    
    def test_init_config_file(self):
        """
        Test the init_config_file
        """     
        init_conf = naspi.init_config_file("{}/conf.json".format(path))
        self.assertEqual(init_conf, "ok")

        with self.assertRaises(SystemExit):
            init_conf = naspi.init_config_file("{}/conf.json".format(path))

    def test_open_or_init_output_file(self):
        output = naspi.open_or_init_output_file(path)
        self.assertEqual(isinstance(output, dict), True)

    def test_sync_local_files(self):
        output = naspi.open_or_init_output_file(path)
        output = naspi.analyze_local_files(folder_to_sync_locally,output)
        print(output)
        
        self.assertEqual(output['local_sync']['files_source'], NUMBER_OF_FILES)
        self.assertEqual(isinstance(output, dict), True)

        output = naspi.run_local_syncs(folder_to_sync_locally,configuration,output)
        print(output)
        self.assertEqual(output['local_sync']['success'], True)

    def test_backup(self):
        output = naspi.open_or_init_output_file(path)
        output = naspi.backup_naspi(configuration['backup'],output)
        time = naspi.today_date()
        count = naspi.count_files_in_dir(configuration['backup']['backup_location']+time,[''])
        self.assertEqual(count, 1)

    def tearDown(self):
        shutil.rmtree(path, ignore_errors=True)

if __name__ == '__main__':
    unittest.main()
