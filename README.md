# simple-nas-pi

## Introduction

Simple implementation of a NAS on raspberry PI with disk redundancy + S3 glacier backup.

### Advantages 
* **simplicity** : use only simple tools like rsync 
* **reliability** : local replication using rsync, per directory. AWS S3 backup for creating off site secured archives
* **cost** : cheap hardware, s3 glacier deep archive cost is ~ 0.3 $ a month per 100GB
* **easy maintenance** : use commodity hardware : raspberry Pi, USB3 hard drives. Can be easily replaced in case of failure
* Associate with tools you like based on your needs : **Plex media server, Nextcloud, Samba share** etc...

## Architecture
![Architecture](/diagram/architecture.png)

## Usage
### Modes
The different mode of the Cli are :
* naspi -c /path/to/conf.json **-m init_config** 
  - init a configuration file 
* naspi -c /path/to/conf.json **-m synclocal**
  - sync local folders based on local folder configuration 
* naspi -c /path/to/conf.json **-m syncs3**
  - sync local folders to s3 glacier deep archive
* naspi -c /path/to/conf.json **-m analyze** 
  - give local and s3 replication status
* naspi -c /path/to/conf.json **-m system**
  - return system information cpu, ram, temp
* naspi -c /path/to/conf.json **-m backup** 
  - backup specific files or folders as set in the backup section of the config file
* naspi -c /path/to/conf.json **-m osbackup** 
  - backup the entire sd card to an .img.gz archive file

### Status file
Each run of the CLI updates a status file you will find in the tool working dir. It gives information on the syncronization status, server metrics, disks health and usage etc..
These files are sent to AWS on a regular basis, so mail alerts can be triggered in case of an issue. Emails alerts are also sent in case files are not received, probably meaning the NAS is unreachable.

Example status file :
```json
{
    "disks": {
        "disk-list": [
            {
                "name": "/disks/disk2",
                "occupied_%": "13% ",
                "present": true
            },
            {
                "name": "/disks/disk1",
                "occupied_%": "13% ",
                "present": true
            },
            {
                "name": " /",
                "occupied_%": " 46%",
                "present": true
            }
        ],
        "all_disks_ok": true,
        "last_run": "2021-02-10 23:50:01"
    },
    "local_sync": {
        "success": true,
        "files_source": 101255,
        "files_dest": 101257,
        "files_delta": -2,
        "locked": false,
        "last_started": "2021-02-10 23:14:17",
        "last_run": "2021-02-10 23:21:02"
    },
    "s3_sync": {
        "success": true,
        "files_source": 23105,
        "files_dest": 23105,
        "files_delta": 0,
        "locked": false,
        "last_started": "2021-02-10 17:32:35",
        "last_run": "2021-02-10 17:33:25"
    },
    "server": {
        "cpu_%": " 1,4 ",
        "ram_Mo": " 508 ",
        "temp_c": "50.6'C",
        "last_run": "2021-02-10 23:50:02"
    }
}
```
## Installation
1. prerequisites
   * A raspberry pi4 (should work with pi3) with pi OS installed
   * 2 USB3 disks (might require power supply as the Pi can't power up 2 * 2.5 disks)
   * Install disks and configure the mount points in /etc/fstab
   * An AWS account with admin access
2. Installation
   * Install naspi from Pypi : 
        ```bash
        pip3 install naspi

        ```

### Configure Naspi
* Initialize a new config file
    ```bash
    naspi -c ./naspi_config.json -m init_config
    ```
* Configure the tool 
    ```bash
    vi ./naspi_config.json
    ```
Initially the config file is :
```json
{
    "disks_list": [],
    "folder_to_sync_locally": [],
    "folders_to_sync_s3": [],
    "naspi_configuration": {
        "working_dir": "",
        "NUMBER_DAYS_RETENTION": 7,
        "MIN_DELAY_BETWEEN_SYNCS_SECONDS": 14400,
        "backup": {
            "files_to_backup": [],
            "backup_location": "",
            "os_backup_location": ""
        }
    }
}
```
* Set the **"working_dir"** to a directory to store the naspi files (logs, config, status files)

* Set the **"disks_list"** : mount points of the disks storing the data so they can be monitored
```json
"disks_list": [
    "/disks/disk1",
    "/disks/disk2"
]
```
* Set **"folder_to_sync_locally"** following the examples below. "delete" option means the deletion are replicated as well.
```json
"folder_to_sync_locally": [
    {
        "source_folder": "/disks/disk1/media/photos/",
        "dest_folder": "/disks/disk2/media/photos/",
        "delete": false
    },
    {
        "source_folder": "/disks/disk1/media/download/",
        "dest_folder": "/disks/disk2/media/download/",
        "delete": true
    }
]
```
* Set "folders_to_sync_s3". **delete option not implemented yet**  
```json
"folders_to_sync_s3": [
    {
        "source_folder": "/disks/disk1/media/photos/",
        "dest_folder": "s3://<bucket-name>/photos",
        "exclude": [
            "folder-to-exclude"
        ],
        "delete": false
    },
    {
        "source_folder": "/disks/disk1/media/download",
        "dest_folder": "s3://<bucket-name>/download",
        "delete": false
    }
]
```
* Set "naspi_configuration" block with files you need to backup 
```json
"naspi_configuration": {
    "working_dir": "/home/pi/naspi",
    "NUMBER_DAYS_RETENTION": 7,
    "MIN_DELAY_BETWEEN_SYNCS_SECONDS": 14400,
    "backup": {
        "files_to_backup": [
            "/etc/fstab",
            "/home/pi",
            "/etc/samba/smb.conf"
        ],
        "backup_location": "/disks/disk1/backups/",
        "os_backup_location": "/disks/disk1/osbackups/"
    }
}
```       
* Set the crons : naspi CLI will be invoked based on a cron schedule. 
Export the path with your local user to make the naspi command available
    ```bash
    crontab -e
    ```
    ```bash
    11 01 * * * export PATH=/home/pi/.local/bin:$PATH && naspi -c /home/pi/naspi/naspi_config.json -m backup
    32 17 * * * export PATH=/home/pi/.local/bin:$PATH && naspi -c /home/pi/naspi/naspi_config.json -m syncs3
    06 * * * * export PATH=/home/pi/.local/bin:$PATH && naspi -c /home/pi/naspi/naspi_config.json -m synclocal
    */10 * * * * export PATH=/home/pi/.local/bin:$PATH && naspi -c /home/pi/naspi/naspi_config.json -m system
    11 3 * * 2 export PATH=/home/pi/.local/bin:$PATH && naspi -c /home/pi/nas_monitor/naspi_config.json -m osbackup
    ```
### Deploy resources in AWS account
Several resources are deployed in AWS : S3 bucket, user, monitoring lambda functions, SNS topic for email notifications.
* In your AWS account, with administrator access : go to **cloudformation** service
* Create a new stack using the template aws/deply-naspi.yml
* Parameters of the stack are :
  - **NaspiBucketName** (REQUIRED): Bucket Name to save the content backed up from the NAS
  - **EmailForReceivingAlerts** (REQUIRED) : Email address to receive the NAS alerts
  - MonitoringSchedule : This defines the Schedule at which to trigger the Naspi monitoring function. Default: cron(0 15 ? * * *)
      
### Generate access keys
AWS Access keys will give the NAS access to the AWS account (S3 bucket)
* In your AWS account, with administrator access : go to **IAM** service
* Find the user **NasPiUser**
* Go to security credentials, generate an access key / secret key pair

### Configure AWS CLI
* Insert the access key / secret key obtained before in **˜/.aws/credentials** file :
    ```bash
    [default]
    aws_access_key_id = AKIAJXXXXXXXXXXX
    aws_secret_access_key = XXXXXXXXXXXXXXXXXXXXXXXX
    ```



