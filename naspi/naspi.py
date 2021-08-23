import os
import boto3
# import subprocess
from subprocess import Popen, PIPE
from time import sleep
import json
import ast
from datetime import datetime, time, timedelta, date
import logging
import logging.handlers
import sys, getopt
import glob
import shutil

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def main():

    ### Order of tasks
    # # 0 check disks are here, catch output
    # # 1 sync to replica disk, catch output
    # # 2 sync to aws, catch output
    # # 3 compare disks files vs replica, catch oputput
    # # 4 compare disks files vs s3, catch out

    # # # Run option
    # -l, --system : only analyze_disks & get_server_metrics ,            every 5m
    # -a, --analyze : analyze_s3_files & analyze_local_files,           every 1 or 3 hours
    # -s, --sync : run_s3_syncs & run_local_syncs,                      every night
    # -d, --syncdelete : run_s3_syncs & run_local_syncs with delete     no cron

    #### exception handling in logger:
    sys.excepthook = handle_exception

    valid_modes = ["system","analyze","sync","syncdelete","synclocal","syncs3","backup","osbackup","init_config"]
    mode = ''
    config = ''
    usage_message = 'naspi -c /path/to/config.json -m <system|analyze|sync|syncdelete|synclocal|syncs3|backup|osbackup|init_config>'

    try:
        opts, args = getopt.getopt(sys.argv[1:],"hm:c:",["mode=","config="])
    # except getopt.GetoptError:
    except Exception as e:
        print(usage_message)
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            print(usage_message)
            sys.exit()
        elif opt in ("-m", "--mode"):
            mode = arg
        elif opt in ("-c", "--config"):
            config = arg

    # # # checking values passed
    if not mode:
        print("Error, mode is mandatory !!")
        print(usage_message)
        sys.exit(2)
    elif not config:
        print("Error, config file is mandatory !!")
        print(usage_message)
        sys.exit(2)        
    elif mode not in valid_modes:
        print("Wrong mode selected, correct modes are : {}".format(valid_modes))
        print(usage_message)
        sys.exit(2)

    # logger.info("Context info : ")
    # logger.info(os.getcwd())
    # logger.info(__file__)
    
    if mode == "init_config":
        output = init_config_file(config)
        sys.exit(0)
    else:
    #### Configuration loading
        disks_list,folder_to_sync_locally,folders_to_sync_s3,configuration = load_configuration(config)

    global NUMBER_DAYS_RETENTION
    global MIN_DELAY_BETWEEN_SYNCS_SECONDS
    global working_dir
    NUMBER_DAYS_RETENTION = configuration.get('NUMBER_DAYS_RETENTION')
    MIN_DELAY_BETWEEN_SYNCS_SECONDS = configuration.get('MIN_DELAY_BETWEEN_SYNCS_SECONDS')
    working_dir = configuration.get('working_dir')

    home_dir = os.environ['HOME']
    global export_path_cmd
    export_path_cmd = 'export PATH={}/.local/bin:$PATH'.format(home_dir)


    ### Logging setup
    # Change root logger level from WARNING (default) to NOTSET in order for all messages to be delegated.
    logging.getLogger('').setLevel(logging.NOTSET)

    # Add file rotatin handler, with level DEBUG
    rotatingHandler = logging.handlers.RotatingFileHandler(filename='{}/nas_monitor.log'.format(working_dir), maxBytes=1000000, backupCount=5)
    rotatingHandler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    rotatingHandler.setFormatter(formatter)
    logging.getLogger('').addHandler(rotatingHandler)
    
    global logger
    logger = logging.getLogger("naspi." + __name__)


    logger.info("")
    logger.info("")
    logger.info("----------------------------------------------------------------------------------------")
    logger.info("----------------------------------------------------------------------------------------")
    logger.info("### Starting Nas Monitor")

    logger.info('Mode is {} and config file is {}'.format(mode,config))

    output = open_or_init_output_file(working_dir)
    if mode == "backup":
        output = backup_naspi(configuration['backup'],output)
    if mode == "osbackup":
        output = os_backup(configuration['backup'],output)
    if mode == "system":
        output = analyze_disks(disks_list,output)
        output = get_server_metrics(output)
    if mode == "synclocal":
        output = analyze_local_files(folder_to_sync_locally, output)
        output = run_local_syncs(folder_to_sync_locally,configuration,output)
        output = analyze_local_files(folder_to_sync_locally, output)
        # File stored to s3 once per hour like local sync (TODO can be improved with a dedicated mode and cron)
        res_s3 = write_and_cleanup_output_file_to_s3(output,'archive-fgi')
    if mode == "syncs3":
        output = analyze_s3_files(folders_to_sync_s3, output)
        output = run_s3_syncs(folders_to_sync_s3,configuration,output)
        output = analyze_s3_files(folders_to_sync_s3, output)  
    if mode == "sync":
        output = run_s3_syncs(folders_to_sync_s3,configuration,output)
        output = run_local_syncs(folder_to_sync_locally,configuration,output)
    if mode == "analyze" or mode == "sync":
        output = analyze_s3_files(folders_to_sync_s3, output)
        output = analyze_local_files(folder_to_sync_locally, output)
    result = write_and_cleanup_output_file(output,configuration)
    # res_s3 = write_and_cleanup_output_file_to_s3(output,'archive-fgi')

    logger.info(json.dumps(output))

####
#### function defs
####

def handle_exception(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    logger.error("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))

def load_configuration(conf_file):
    try:
        f = open(conf_file, "r")
        dict_conf = json.loads(f.read())
        f.close()
        return(
                    dict_conf['disks_list'],
                    dict_conf['folder_to_sync_locally'],
                    dict_conf['folders_to_sync_s3'],
                    dict_conf['naspi_configuration']
                )

    except FileNotFoundError as e:
        print("Conf file not found, provide a file named {}".format(conf_file))
        raise(e)
        # sys.exit(2)

def today_time():
    today = datetime.today()
    d1 = today.strftime("%Y-%m-%d %H:%M:%S")
    return(d1)

def today_date():
    today = datetime.today()
    d1 = today.strftime("%Y-%m-%d")
    return(d1)

def date_diff_in_seconds(dt2, dt1):
  timediff = dt2 - dt1
  return timediff.days * 24 * 3600 + timediff.seconds

def run_shell_command(command):
    message = ""
    logger.info("### Running {}".format(command))
    df_out = Popen(command, 
                                shell=True, 
                                stdout=PIPE,
                                stderr=PIPE
                            )
    sleep(.2)
    retcode = df_out.poll()
    while retcode is None: # Process running
        # logger.info("### Process not finished, waiting...")
        sleep(10)
        retcode = df_out.poll()

    # Here, `proc` has finished with return code `retcode`
    if retcode != 0:
        """Error handling."""
        logger.info("### Error !")
        message = df_out.stderr.read().decode("utf-8")
        logger.info(retcode)
        logger.info(message)
        return(retcode,message)

    message = df_out.stdout.read().decode("utf-8")
    logger.info(retcode)
    logger.info(message)
    return(retcode,message)

def open_or_init_output_file(working_dir):
    today = today_date()
    try:
        f = open("{}/naspi_status_{}.json".format(working_dir,today), "r")
        dict_output = json.loads(f.read())
        f.close()
    except FileNotFoundError:
        logger.info("File for today does not exist, initializing it")
        dict_output = {}
        dict_output['disks'] = {}
        dict_output['disks']['disk-list'] = []
        dict_output['local_sync'] = {}
        dict_output['local_sync']['success'] = True
        dict_output['s3_sync'] = {}
        dict_output['s3_sync']['success'] = True
        dict_output['server'] = {}
    
    return(dict_output)

def init_config_file(file_name):

    print("initializing config file {}".format(file_name))

    if os.path.exists(file_name):
        print("Error, config file {} already exists !!".format(file_name))
        sys.exit(2)
    else:
        dict_conf = {}
        dict_conf['disks_list'] = []
        dict_conf['folder_to_sync_locally'] = []
        dict_conf['folders_to_sync_s3'] = []
        dict_conf['naspi_configuration'] = {}
        dict_conf['naspi_configuration']['working_dir'] = ""
        dict_conf['naspi_configuration']['NUMBER_DAYS_RETENTION'] = 7
        dict_conf['naspi_configuration']['MIN_DELAY_BETWEEN_SYNCS_SECONDS'] = 14400
        dict_conf['naspi_configuration']['backup'] = {}
        dict_conf['naspi_configuration']['backup']['files_to_backup'] = []
        dict_conf['naspi_configuration']['backup']['backup_location'] = ""
        dict_conf['naspi_configuration']['backup']['os_backup_location'] = ""

        f = open("{}".format(file_name), "w")
        f.write(json.dumps(dict_conf,indent=4))
        f.close()
    
    return("ok")

def write_and_cleanup_output_file_to_s3(output,bucket):
    s3_client = boto3.client('s3',region_name='eu-west-1')
    today = today_date()

    response = s3_client.put_object( Body=json.dumps(output),
                                      Bucket=bucket,
                                      Key="status/naspi_status_{}.json".format(today)
                                     )
    return(response)

def write_and_cleanup_output_file(output,configuration):
    NUMBER_DAYS_RETENTION = configuration.get('NUMBER_DAYS_RETENTION')
    working_dir = configuration.get('working_dir')
    today = today_date()
    f = open("{}/naspi_status_{}.json".format(working_dir,today), "w")
    f.write(json.dumps(output,indent=4))
    f.close()

    existing_output_files = glob.glob('{}/naspi_status_*.json'.format(working_dir))
    existing_output_files.sort()
    for out_file in existing_output_files:
        if out_file not in existing_output_files[-NUMBER_DAYS_RETENTION:]:
            logger.info("Deleting {}".format(out_file))
            os.remove(out_file)

    return("done")

def analyze_disks(disks_list,output):

    output['disks']['all_disks_ok'] = True
    output['disks']['disk-list'] = []
    retcode,message = run_shell_command('df -kh | tail -n +2')
    #logger.info(message)
    all_disks_present = True
    for disk in disks_list:
        disk_output = {}
        if disk in message:
            logger.info("### disk {} is here".format(disk))
            usage = message.split(disk)[0][-4:]
            logger.info("### usage : {}".format(usage))

            disk_output['name'] = disk
            disk_output['occupied_%'] = usage
            disk_output['present'] = True
            output['disks']['disk-list'].append(disk_output)
        else:
            logger.info("### disk {} not here".format(disk))
            all_disks_present = False

            disk_output['name'] = disk
            disk_output['occupied_%'] = "NA"
            disk_output['present'] = False
            output['disks']['disk-list'].append(disk_output)

    if not all_disks_present:
        logger.info("### some disks are missing")
        output['disks']['all_disks_ok'] = False

    output['disks']['last_run'] = today_time()
    return(output)

def acquire_sync_lock(output,local_or_s3,configuration):
    # Make sure only one sync process runs at a time
    can_run = True
    MIN_DELAY_BETWEEN_SYNCS_SECONDS = configuration.get('MIN_DELAY_BETWEEN_SYNCS_SECONDS')

    if 'last_started' in output[local_or_s3]:
        started_time = datetime.strptime(output[local_or_s3]['last_started'], '%Y-%m-%d %H:%M:%S')
    else:
        started_time = datetime.strptime('2020-12-25 12:00:00', '%Y-%m-%d %H:%M:%S')
    
    now_time = datetime.now()
    logger.info(" %d seconds from previous run" %(date_diff_in_seconds(now_time, started_time)))

    if 'locked' in output[local_or_s3] and output[local_or_s3]['locked'] == True and date_diff_in_seconds(now_time, started_time) < MIN_DELAY_BETWEEN_SYNCS_SECONDS:
        logger.info("Can't run sync as another process might be running")
        can_run = False
    else:
        logger.info("Acquiring lock for {}".format(local_or_s3))
        output[local_or_s3]['locked'] = True
        output[local_or_s3]['last_started'] = today_time()
        logger.info(output)
        # Acquire lock and write it to disk:
        result = write_and_cleanup_output_file(output,configuration)

    return(can_run,output)



def run_s3_syncs(folders_to_sync_s3,configuration, output):

    can_run,output = acquire_sync_lock(output, 's3_sync',configuration)

    if can_run:
        success = True
        for folder in folders_to_sync_s3:
            exclusions_flags = ''
            if 'exclude' in folder:
                for exclusion in folder['exclude']:
                    exclusions_flags = exclusions_flags + ' --exclude "{}/*" '.format(exclusion)
            # command = 'aws s3 sync {} {} {} --storage-class DEEP_ARCHIVE --dryrun'.format(folder['source_folder'],folder['dest_folder'],exclusions_flags)
            command = 'aws s3 sync {} {} {} --storage-class DEEP_ARCHIVE --only-show-errors'.format(folder['source_folder'],folder['dest_folder'],exclusions_flags)
            ret,msg = run_shell_command('{}; {}'.format(export_path_cmd,command))

            if ret != 0:
                success = False

        output['s3_sync']['success'] = success
        output['s3_sync']['last_run'] = today_time()
        output['s3_sync']['locked'] = False

    else:
        logger.info("/!\ Cant run the sync, there is a sync process ongoing")

    return(output)

def count_files_in_dir(folder,exclude_list):
    exclude_directories = set(exclude_list)    #directory (only names) want to exclude
    total_file = 0
    for dname, dirs, files in os.walk(folder):  #this loop though directies recursively 
        dirs[:] = [d for d in dirs if d not in exclude_directories] # exclude directory if in exclude list 
        total_file += len(files)

    logger.info("Files in {} : {}".format(folder,total_file))
    return(total_file)

def analyze_s3_files(folders_to_sync_s3, output):
    output['s3_sync']['files_source'] = 0
    output['s3_sync']['files_dest'] = 0
    output['s3_sync']['folders'] = []
    for folder in folders_to_sync_s3:
        one_folder = {}
        one_folder['source_folder'] = folder['source_folder']
        # Get local files count
        if 'exclude' in folder:
            exclude_directories = set(folder['exclude'])    #directory (only names) want to exclude
        else:
            exclude_directories = []
        total_file = 0
        for dname, dirs, files in os.walk(folder['source_folder']):  #this loop though directies recursively 
            dirs[:] = [d for d in dirs if d not in exclude_directories] # exclude directory if in exclude list 
            # print(len(files))
            total_file += len(files)

        logger.info("Files in {} : {}".format(folder['source_folder'],total_file))
        one_folder['source_count'] = total_file
        output['s3_sync']['files_source'] += total_file

        # Get s3 files count
        ret,msg = run_shell_command('{}; aws s3 ls {} --recursive --summarize | grep "Total Objects"'.format(export_path_cmd,folder['dest_folder']))
        output['s3_sync']['files_dest'] += int(msg.split(': ')[1])
        one_folder['dest_folder'] = folder['dest_folder']
        one_folder['dest_count'] = int(msg.split(': ')[1])
        output['s3_sync']['folders'].append(one_folder)


    output['s3_sync']['files_delta'] = output['s3_sync']['files_source'] - output['s3_sync']['files_dest']

    logger.info("Analyze s3 file output : {}".format(json.dumps(output)))
        
    return(output)

def run_local_syncs(folder_to_sync_locally,configuration, output):
    # rsync -anv dir1 dir2   # n = dryrun, v = verbose
    # will create dir2/dir1
    can_run,output = acquire_sync_lock(output, 'local_sync', configuration)

    if can_run:
        success = True
        for folder in folder_to_sync_locally:
            delete = ""
            if folder['delete']:
                delete = "--delete"
            ret,msg = run_shell_command('mkdir -p {}'.format(folder['dest_folder']))
            ret,msg = run_shell_command('rsync -aq {} {} {}'.format(folder['source_folder'],folder['dest_folder'],delete))
            if ret != 0:
                success = False

        output['local_sync']['success'] = success
        output['local_sync']['last_run'] = today_time()
        output['local_sync']['locked'] = False
    else:
        logger.info("/!\ Cant run the sync, there is a sync process ongoing")
    
    return(output)

def analyze_local_files(folder_to_sync_locally, output):
    output['local_sync']['files_source'] = 0
    output['local_sync']['files_dest'] = 0
    output['local_sync']['folders'] = []

    for folder in folder_to_sync_locally:
        one_folder = {}
        one_folder['source_folder'] = folder['source_folder']
        src_count = count_files_in_dir(folder['source_folder'],[''])
        output['local_sync']['files_source'] += src_count
        one_folder['source_count'] = src_count

        dest_folder = "{}/{}".format(folder['dest_folder'],folder['source_folder'].split("/")[-1])
        one_folder['dest_folder'] = dest_folder
        dest_count = count_files_in_dir(dest_folder,[''])
        output['local_sync']['files_dest'] += dest_count
        one_folder['dest_count'] = dest_count

        output['local_sync']['folders'].append(one_folder)

    output['local_sync']['files_delta'] = output['local_sync']['files_source'] - output['local_sync']['files_dest']  

    logger.info("Analyze local file output : {}".format(json.dumps(output)))      

    return(output)

def get_server_metrics(output):
    # get cpu usage
    ret,msg = run_shell_command('top -bn 1 | grep Cpu | head -c 14 | tail -c 5')
    output['server']['cpu_%'] = msg

    ret,msg = run_shell_command('free -m | grep Mem | head -c 32 | tail -c 5')
    output['server']['ram_Mo'] = msg

    ret,msg = run_shell_command('vcgencmd measure_temp | head -c 11 | tail -c 6')
    output['server']['temp_c'] = msg

    output['server']['last_run'] = today_time()

    return(output)

def backup_naspi(backup,output):
    backup_location = backup.get('backup_location')
    backup_dir = "{}{}".format(backup_location,today_date())
    ret,msg = run_shell_command('mkdir -p {}'.format(backup_dir))

    files_to_backup = backup.get("files_to_backup")

    for entry in files_to_backup:
        if os.path.isdir(entry):
            ret,msg = run_shell_command('rsync -aqR {} {}'.format(entry,backup_dir))
        else:
            subdir = entry.rsplit('/',1)[0]
            ret,msg = run_shell_command('mkdir -p {}{}'.format(backup_dir,subdir))
            ret,msg = run_shell_command('rsync -aq {} {}{}'.format(entry,backup_dir,entry))

    # old bkp cleanup
    existing_backup_dir = glob.glob('{}/*'.format(backup_location))
    existing_backup_dir.sort()
    for out_file in existing_backup_dir:
        if out_file not in existing_backup_dir[-10:]:
            print("Deleting {}".format(out_file))
            shutil.rmtree(out_file,ignore_errors=True)

    return(output)

def os_backup(backup,output):
    os_backup_location = backup.get('os_backup_location')
    backup_name = "osbkp-{}.img".format(today_date())

    # sudo dd if=/dev/mmcblk0 of=/disks/Elements/os_bkp/osbkp18082021.img bs=1M
    # sudo ./pishrink.sh -z osbkp18082021.img

    ret,msg = run_shell_command('sudo dd if=/dev/mmcblk0 of={}/{} bs=1M'.format(os_backup_location,backup_name))

    if not os.path.exists("{}/pishrink.sh".format(working_dir)):
        ret,msg = run_shell_command('wget https://raw.githubusercontent.com/Drewsif/PiShrink/master/pishrink.sh -P {}'.format(working_dir))
        # wget https://raw.githubusercontent.com/Drewsif/PiShrink/master/pishrink.sh
        ret,msg = run_shell_command('sudo chmod +x {}/pishrink.sh'.format(working_dir))
        # sudo chmod +x pishrink.sh

    ret,msg = run_shell_command('sudo bash {}/pishrink.sh -z {}/{}'.format(working_dir,os_backup_location,backup_name))

    # old bkp cleanup
    existing_backup_dir = glob.glob('{}/*'.format(os_backup_location))
    existing_backup_dir.sort()
    for out_file in existing_backup_dir:
        if out_file not in existing_backup_dir[-4:]:
            print("Deleting {}".format(out_file))
            shutil.rmtree(out_file,ignore_errors=True)

    return(output)

if __name__=='__main__':
    main()
    # main(sys.argv[1:])