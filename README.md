# simple-nas-pi

## Introduction

Simple implementation of a NAS on raspberry PI with disk redundancy + S3 glacier backup.

Advantages : 
- simplicity : use only simple tools like rsync 
- reliability : local replication using rsync, per directory. AWS S3 backup for creating off site secured archives
- cost : cheap hardware, s3 glacier deep archive cost is ~ 0.3 $ a month per 100GB
- easy maintenance : use commodity hardware : raspberry Pi, USB hard drives

## Architecture
![Architecture](/diagram/architecture.png)

## Installation
1. prerequisites
2. Installation

## Get started

## Usage