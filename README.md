# simple-nas-pi

## Introduction

Simple implementation of a NAS on raspberry PI with disk redundancy + S3 glacier backup.

Advantages : 
* simplicity : use only simple tools like rsync 
* reliability : local replication using rsync, per directory. AWS S3 backup for creating off site secured archives
* cost : cheap hardware, s3 glacier deep archive cost is ~ 0.3 $ a month per 100GB
* easy maintenance : use commodity hardware : raspberry Pi, USB3 hard drives. Can be easily replaced in case of failure
* Associate with tools you like based on your needs : Plex media server, Nextcloud, Samba share etc...

## Architecture
![Architecture](/diagram/architecture.png)

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
   * Configure Naspi
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
                    "backup_location": ""
                }
            }
        }
        ```
        * Set the "working_dir" to a directory to store the naspi files (logs, config, status files)
        * Set the "disks_list" : mount points of the disks storing the data
         ```bash
        "disks_list": [
            "/disks/disk1",
            "/disks/disk2"
        ]
         ```
        * Set "folder_to_sync_locally"
         ```bash
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
         ```
        * Set "folders_to_sync_s3"         
   * Deploy resources in AWS account
   * Configure AWS CLI

## Get started

## Usage