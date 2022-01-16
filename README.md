# Sonos Web Widget
> Self-contained web widget server that shows current playback status.
> Based on aiohttp and soco.

## Table of Contents
* [General Info](#general-information)
* [Technologies Used](#technologies-used)
* [Setup](#setup)
* [Usage](#usage)
* [Project Status](#project-status)
* [Room for Improvement](#room-for-improvement)

## General Information
I've been playing around with [DAKboard](https://www.dakboard.com/site) recently, and wanted to include a widget that
showed the playing status of Sonos speakers. DAKboard includes a Sonos widget (wooohoo), but it's not fantastic
(boohoo). More specifically, the updating speed is quite slow and because artwork images are served from the Sonos
speakers themselves some browsers/platforms will not display them. I set out to create my own widget that solved these
two problems...

## Technologies Used
- Python - version 3.9
- soco
- aiohttp
- aiohttp-jinja2
- aiofiles

## Setup
Download and install dependencies. Generate SSL certificate files.

## Usage
Accepts the following optional arguments:

`--host "your.new.host.ip" (default="0.0.0.0")`

`--port port_number (default=8080)`

`--http (boolean that determines if server is started using HTTP or HTTPS)`

`--debug (boolean that determines if logging level is INFO or DEBUG)`

Run this script as follows:

`python start_server.py OPTIONS`

## Project Status
Project is: IN PROGRESS

## Room for Improvement
Room for improvement:
- Avoid re-contacting the same Sonos
- Switch from a pull model to a push model (based on subscribing to Sonos events)