# simple-nas-pi

## Introduction

Simple implementation of a NAS on raspberry PI with disk redundancy + S3 glacier backup.

Advantages : 
- simplicity : use only simple tools like rsync 
- reliability : local replication using rsync, per directory. AWS S3 backup for creating off site secured archives
- cost : cheap hardware, s3 glacier deep archive cost is ~ 0.3 $ a month per 100GB
- easy maintenance : use commodity hardware : raspberry Pi, USB3 hard drives. Can be easily replaced in case of failure
- Associate with tools you like based on your needs : Plex media server, Nextcloud, Samba share etc...

## Architecture
![Architecture](/diagram/architecture.png)

## Installation
1. prerequisites
   * A raspberry pi4 (should work with pi3) with pi OS installed
   * 2 USB3 disks (might require power supply as the Pi can't power up 2 * 2.5 disks)
   * Install disks and configure the mount points in /etc/fstab
2. Installation
   * Install naspi from Pypi : 
  ```bash
  pip3 install naspi
  ```

## Get started

## Usage