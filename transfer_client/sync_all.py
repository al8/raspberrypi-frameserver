import os
import sys

from collections import namedtuple

import logging
import time

import subprocess
import socket
import zlib
import traceback
import tempfile

from sync_all_lib import set_params, setup_logging, get_dirs_files, get_files, copy_resize_rotate, upload, cleanup_output_path, send_remote_command, remote_get_files, remote_delete_files, transfer_params_t

from plugins import \
    filter_picasa, \
    filter_hash, \
    filter_recent, \
    filter_regex

def main(logger):
    params = {
        "PI-HOST": None, #"192.168.1.34",
        "PI-PORT": 9999,
        "output_path": r"D:\!Dropbox.com\Dropbox (Personal)\sync_output",
        "scp_cmdline": [
            r"D:\Progs\pscp.exe",
            "-batch",
            "-pw",
            "pi",
        ],
        "output_jpg_size": 2048,
        "output_jpg_quality": 55,
        "imagemagick_convert_binary":  # from ImageMagick-6.9.3-7-portable-Q16-x64
            r"D:\!Dropbox.com\Dropbox (Personal)\raspberrypi-frameserver\transfer_client\convert.exe",
        "jhead_binary":  # on windows, jpegtran.exe must be in the same path
            r"D:\!Dropbox.com\Dropbox (Personal)\raspberrypi-frameserver\transfer_client\jhead.exe",
    }
    set_params(params)

    HOST = params["PI-HOST"]
    PORT = int(params["PI-PORT"])

    transfer_params_l = [
        transfer_params_t(
            r"D:\!Memories\staging area\Eye-Fi",
            [(filter_regex, {"dir": "\d{4}[-]\d\d[-]\d\d[-].+", "file": "(((DSC|IMG_|[A-Z]+)\d+)|(\d+-\d+-\d+ \d+.\d+.\d+))[.]jpg"})],  # local_filters
            [],  # global_filters
        ),
        transfer_params_t(
            r"D:\!Memories\Photos\2011",
            [(filter_regex, {"dir": "\d{8} .+", "file": "\d{8}_\d{4}.+[.]jpg",}), filter_picasa],  # local_filters
            [],  # global_filters
        ),
        transfer_params_t(
            r"D:\!Memories\Photos\2012",
            [(filter_regex, {"dir": "\d{8} .+", "file": "\d{8}_\d{4}.+[.]jpg",}), filter_picasa],  # local_filters
            [],  # global_filters
        ),
        transfer_params_t(
            r"D:\!Memories\Photos\2013",
            [(filter_regex, {"dir": "\d{8} .+", "file": "\d{8}_\d{4}.+[.]jpg",}), filter_picasa],  # local_filters
            [],  # global_filters
        ),
        transfer_params_t(
            r"D:\!Memories\Photos\2014",
            [(filter_regex, {"dir": "\d{8} .+", "file": "\d{8}_\d{4}.+[.]jpg",}), filter_picasa],  # local_filters
            [],  # global_filters
        ),
        transfer_params_t(
            r"D:\!Memories\Photos\2015",
            [(filter_regex, {"dir": "\d{8} .+", "file": "\d{8}_\d{4}.+[.]jpg",}), filter_picasa],  # local_filters
            [],  # global_filters
        ),
        transfer_params_t(
            r"D:\!Memories\Photos\2016",
            [(filter_regex, {"dir": "\d{8} .+", "file": "\d{8}_\d{4}.+[.]jpg",}), filter_picasa],  # local_filters
            [],  # global_filters
        ),
        transfer_params_t(
            r"D:\!Memories\Photos\2017",
            [(filter_regex, {"dir": "\d{8} .+", "file": "\d{8}_\d{4}.+[.]jpg",}), filter_picasa],  # local_filters
            [],  # global_filters
        ),
        transfer_params_t(
            r"D:\!Memories\Photos\2018",
            [(filter_regex, {"dir": "\d{8} .+", "file": "\d{8}_\d{4}.+[.]jpg",}), filter_picasa],  # local_filters
            [],  # global_filters
        ),
        transfer_params_t(
            r"D:\!Memories\Photos\2019",
            [(filter_regex, {"dir": "\d{8} .+", "file": "\d{8}_\d{4}.+[.]jpg",}), filter_picasa],  # local_filters
            [],  # global_filters
        ),
        transfer_params_t(
            r"D:\!Memories\Photos\2020",
            [(filter_regex, {"dir": "\d{8} .+", "file": "\d{8}_\d{4}.+[.]jpg",}), filter_picasa],  # local_filters
            [],  # global_filters
        ),
    ]

    files = set()
    for p in transfer_params_l:
        files |= get_files(p)
    logger.info("TOTAL FILES TO SYNC: %d (cached in %s)" % (len(files), params["output_path"]))

    # resize rotate and copy the files
    new_files, not_new_files = copy_resize_rotate(files, params["output_path"])
    all_output_files = new_files | not_new_files
    if len(new_files): logger.info("FILES RESIZED: %d" % len(new_files))

    script = cleanup_output_path(params["output_path"], all_output_files)

    if HOST is None:
        logger.info("No HOST specified, skipping upload")
    else:
        # list remote files to find ones to be deleted that don't exist locally
        local_files = set(map(lambda f: os.path.basename(f).lower(), list(all_output_files)))
        remote_files = set(remote_get_files(HOST, PORT))

        # upload files that don't exist on remote
        upload_files = local_files - remote_files
        upload(map(lambda f: os.path.join(params["output_path"], f), list(upload_files)))

        # remove renote files
        delete_files = remote_files - local_files
        if len(delete_files): logger.info("num files to be deleted remotely: %d" % len(delete_files))
        for f in delete_files:
            logger.debug("delete file remotely: %s" % f)
        if delete_files:
            remote_delete_files(HOST, PORT, list(delete_files))


if __name__ == "__main__":
    logger = setup_logging()
    main(logger)
