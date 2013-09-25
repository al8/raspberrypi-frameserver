import os
import sys
import re

from collections import namedtuple

import logging
import time

import ConfigParser
import subprocess
import socket
import zlib
import traceback

def setup_logging():
    global g_lgr
    logfilename = "transfer.log"

    # create logger
    g_lgr = logging.getLogger('transfer')
    g_lgr.setLevel(logging.DEBUG)

    # add a file handler
    if os.path.isfile(logfilename):
        os.remove(logfilename)
    fh = logging.FileHandler(logfilename)
    fh.setLevel(logging.INFO)
    # create a formatter and set the formatter for the handler.
    frmt = logging.Formatter('%(asctime)s - %(filename)s:%(lineno)s - %(levelname)s - %(message)s')
    fh.setFormatter(frmt)
    # add the Handler to the logger
    g_lgr.addHandler(fh)

    # add stdout
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    formatter = logging.Formatter('%(levelname)s - %(asctime)s - %(filename)s:%(lineno)s - %(message)s')
    ch.setFormatter(formatter)
    g_lgr.addHandler(ch)

    # You can now start issuing logging statements in your code
    # lgr.debug('debug message') # This won't print to myapp.log
    # lgr.info('info message') # Neither will this.
    # lgr.warn('Checkout this warning.') # This will show up in the log file.
    # lgr.error('An error goes here.') # and so will this.
    # lgr.critical('Something critical happened.') # and this one too.


transfer_params_t = namedtuple(
    "transfer_params_t", [
        "path",
        "directory_re",
        "filename_re",
        "most_recent_x",
        "hash_x",
        "process_stars",
    ]
)

def get_dirs_files(path, directory_re, filename_re, process_stars):
    meta = {}

    items = os.listdir(path)
    fullitems = map(lambda p: os.path.join(path, p), items)  # full path

    # split between dirs and files
    dirs = filter(os.path.isdir, fullitems)
    files = filter(os.path.isfile, fullitems)

    # regex match filter
    dirs = filter(
        lambda e:
            re.match(
                directory_re,
                os.path.basename(e),
                re.IGNORECASE),
        dirs)
    files = filter(
        lambda e:
            re.match(
                filename_re,
                os.path.basename(e),
                re.IGNORECASE),
        files)

    # picasa star filter
    if process_stars:
        picasa_ini = os.path.join(path, '.picasa.ini')
        if os.path.isfile(picasa_ini):
            star_files = set()
            config = ConfigParser.ConfigParser()
            config.read(picasa_ini)
            g_lgr.debug(dir(config))
            for s in config.sections():
                g_lgr.debug("%s %s %s" % (s, config.items(s), ('star', 'yes') in config.items(s)))
                if ('star', 'yes') in config.items(s):
                    star_files.add(s.lower())
            meta["pre_starred_filter"] = len(files)
            files = filter(lambda e: os.path.basename(e).lower() in star_files, files)
            if len(files) > 0:
                g_lgr.debug("picasa_ini filter: %d files starred, %d left" % (len(star_files), len(files)))
        else:
            return dirs, [], meta

    return dirs, files, meta

def get_files(transfer_param, path_override=None, most_recent_x=None, hash_x=None):
    # gather viable image files into this set
    files = set()

    if path_override is None:
        path = transfer_param.path
    else:
        path = path_override

    p_dirs, p_files, meta = get_dirs_files(
        path,
        transfer_param.directory_re,
        transfer_param.filename_re,
        transfer_param.process_stars)

    # log debug information
    logger = g_lgr.debug # if len(p_dirs) == 0 and len(p_files) == 0 else g_lgr.info
    logger("dirs:%d files:%d path: \"%s\" meta: %s" % (
            len(p_dirs),
            len(p_files),
            os.path.basename(path),
            meta,
        )
    )
    for e in p_dirs:
        g_lgr.debug("DIR \"%s\"" % e)
    for e in p_files:
        g_lgr.debug("FILE \"%s\"" % e)

    files |= set(p_files)

    # recurse down the tree
    for d in p_dirs:
        files |= get_files(transfer_param, path_override=d)

    # only get most recent files
    if most_recent_x and len(files) > 0:
        mtime_fname_l = []
        for e in files:
            mtime_fname_l.append((os.path.getmtime(e), e))
        mtime_fname_l.sort(reverse=True)
        # for e in mtime_fname_l:
        #     print e
        files = set(zip(*(mtime_fname_l[:most_recent_x]))[1])

    # get a 'random' selection of files
    if hash_x and len(files) > 0:
        ### configure hash slicing here
        interval_min = 20  # different every 20 minutes / slices
        slices = 4  # split the interval into this many slices
        ###

        tmp_files = set()
        interval = interval_min * 60  # interval in seconds
        interval_per_slice = interval / slices
        photos_per_slice = max(1, int(round(hash_x / float(slices))))

        now = int(time.time()) / interval_per_slice
        # print "now", now
        # print "photos_per_slice", photos_per_slice
        # print "interval", interval
        # print "interval_per_slice", interval_per_slice
        # last = None
        for t in range(now, now - slices, -1):
            # print "t", t, (t - last) if last else ""
            # last = t

            hash_fname_l = []
            hashorig = t  # different every interval
            for e in files:
                h = zlib.crc32(str(hashorig) + e)
                hash_fname_l.append((h, e))
            hash_fname_l.sort()
            # for e in hash_fname_l:
            #     print e
            tmp_files |= set(zip(*(hash_fname_l[:photos_per_slice]))[1])
        # files = set(zip(*(hash_fname_l[:hash_x]))[1])
        files = tmp_files

    return files

def resize(files, output_path, dst_size=2048):
    """
    resize files
    returns resized files and would be resized files
    """
    new_files = set()  # new files to be copied over
    not_new_files = set()
    cnt_skip = 0
    cnt_convert = 0
    for idx, f in enumerate(sorted(files)):
        src, dst = f, os.path.join(output_path, os.path.basename(f))

        # if file already exists, then don't resize, and don't add to new_files set
        if os.path.isfile(dst):
            g_lgr.debug("skipping file '%s' because dst:'%s' already exists" % (src, dst))
            cnt_skip += 1
            not_new_files.add(dst)
            continue

        args = [
            r"C:\Program Files\ImageMagick-6.8.6-Q16\convert.exe",
            src,
            "-quality",
            "65",
            "-resize",
            "%dx%d>" % (dst_size, dst_size),
            dst,
        ]
        g_lgr.debug("resizing file '%s' to '%s' (%d of %d)" % (src, dst, idx + 1, len(files)))
        g_lgr.debug(" ".join(args))
        subprocess.check_output(
            args,
            stderr=subprocess.STDOUT,
        )

        cnt_convert += 1

        args = [
            r"D:\!Dropbox.com\Dropbox\frame_transfer\jhead.exe",
            "-autorot",
            dst,
        ]
        g_lgr.debug("auto rotate file '%s'" % (dst))
        g_lgr.debug(" ".join(args))
        try:
            subprocess.check_output(
                args,
                stderr=subprocess.STDOUT,
            )
        except subprocess.CalledProcessError as ex:
            g_lgr.error(traceback.format_exc())
            g_lgr.debug("removing file that could not be rotated %s" % dst)
            os.remove(dst)
        new_files.add(dst)

    if cnt_convert: g_lgr.info("Resized %d files (%d skipped)" % (cnt_convert, cnt_skip))

    # return list of newly resized files (to be used to upload)
    return new_files, not_new_files

def upload(files):
    """
    upload the list of files to the raspberry pi
    """
    cnt = 0
    for idx, f in enumerate(sorted(files)):
        src = f
        dst = "pi@192.168.1.34:photos/%s" % (os.path.basename(f).lower())
        args = [
            r"D:\Progs\pscp.exe",
            "-batch",
            "-pw",
            "pi",
            src,
            dst,
        ]
        g_lgr.info("uploading file '%s' to '%s' (%d of %d)" % (src, dst, idx + 1, len(files)))
        g_lgr.debug(" ".join(args))
        subprocess.check_output(
            args,
            stderr=subprocess.STDOUT,
        )
        cnt += 1
    if len(files): g_lgr.info("Uploaded %d files" % len(files))

def cleanup_output_path(output_path, output_files):
    items = os.listdir(output_path)
    fullitems = map(lambda p: os.path.join(output_path, p), items)  # full path

    # split between dirs and files
    files = set(filter(os.path.isfile, fullitems))

    cleanup_files = files - output_files

    if len(cleanup_files): g_lgr.info("number of files to clean up: %d" % len(cleanup_files))
    for f in cleanup_files:
        g_lgr.debug("cleanup '%s'" % f)
        os.remove(f)

def send_remote_command(host, port, command, arguments):
    if len(arguments) > 0:
        data = command + "\t" + "\t".join(arguments)
    else:
        data = command

    # Create a socket (SOCK_STREAM means a TCP socket)
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try:
        # Connect to server and send data
        sock.connect((host, port))
        sock.sendall(data + "\n")

        received = ""
        # Receive data from the server and shut down
        r = sock.recv(4096)
        received += r
        while r:
            r = sock.recv(4096)
            received += r
    finally:
        sock.close()

    g_lgr.debug("Sent:     {}".format(data))
    g_lgr.debug("Received: {}".format(received))

    return received

def remote_get_files(host, port):
    files_all = send_remote_command(host, port, "list", [])
    if len(files_all.strip()) == 0: return []
    files = files_all.split("\t")
    files = map(lambda f: f.strip(), files)
    for f in files:
        g_lgr.debug("remote file: '%s'" % f)
    g_lgr.debug("num remote files %d" % len(files))
    return files

def remote_delete_files(host, port, files):
    recv = send_remote_command(host, port, "del", files).strip()
    for f in files:
        g_lgr.info("deleted %s" % f)
    g_lgr.info("num remote files deleted '%s' (requested:%d)" % (recv, len(files)))
    return recv

def main():
    HOST = "192.168.1.34"
    PORT = 9999

    # output_path = r"D:\!digital_picture_frame_tmp"
    output_path = r"D:\!Dropbox.com\Dropbox\frame_transfer_output"
    transfer_params_l = [
        transfer_params_t(
            r"D:\!Memories\staging area\Eye-Fi",
            "\d{4}[-]\d\d[-]\d\d[-].+",
            "(DSC|IMG_)\d+[.]jpg",
            10,  # most_recent_x
            None,  # hash_x
            False,  # process_stars
        ),
        transfer_params_t(
            r"D:\!Memories\staging area\Eye-Fi",
            "\d{4}[-]\d\d[-]\d\d[-].+",
            "(DSC|IMG_)\d+[.]jpg",
            50,  # most_recent_x
            13,  # hash_x
            False,  # process_stars
        ),
        transfer_params_t(
            r"D:\!Memories\staging area\Eye-Fi",
            "\d{4}[-]\d\d[-]\d\d[-].+",
            "(DSC|IMG_)\d+[.]jpg",
            100,  # most_recent_x
            20,  # hash_x
            False,  # process_stars
        ),

        transfer_params_t(
            r"D:\!Memories\Photos\2011",
            "\d{8} .+",
            "\d{8}_\d{4}.+[.]jpg",
            None,  # most_recent_x
            10,  # hash_x
            True,  # process_stars
        ),
        transfer_params_t(
            r"D:\!Memories\Photos\2012",
            "\d{8} .+",
            "\d{8}_\d{4}.+[.]jpg",
            None,  # most_recent_x
            10,  # hash_x
            True,  # process_stars
        ),
        transfer_params_t(
            r"D:\!Memories\Photos\2013",
            "\d{8} .+",
            "\d{8}_\d{4}.+[.]jpg",
            None,  # most_recent_x
            10,  # hash_x
            True,  # process_stars
        ),
        transfer_params_t(
            r"D:\!Memories\Photos\2013",
            "\d{8} .+",
            "\d{8}_\d{4}.+[.]jpg",
            100,  # most_recent_x
            15,  # hash_x
            True,  # process_stars
        ),
    ]

    files = set()
    for p in transfer_params_l:
        files |= get_files(p, most_recent_x=p.most_recent_x, hash_x=p.hash_x)
    g_lgr.info("TOTAL FILES TO SYNC: %d" % len(files))

    # resize and move the files
    new_files, not_new_files = resize(files, output_path)
    if len(new_files): g_lgr.info("FILES RESIZED: %d" % len(new_files))

    # upload files
    # upload(new_files)

    script = cleanup_output_path(output_path, new_files | not_new_files)

    # list remote files to find ones to be deleted that don't exist locally
    local_files = set(map(lambda f: os.path.basename(f).lower(), list(new_files | not_new_files)))
    remote_files = set(remote_get_files(HOST, PORT))

    # upload files that don't exist on remote
    upload_files = local_files - remote_files
    upload(map(lambda f: os.path.join(output_path, f), list(upload_files)))

    # remove renote files
    delete_files = remote_files - local_files
    if len(delete_files): g_lgr.info("num files to be deleted remotely: %d" % len(delete_files))
    for f in delete_files:
        g_lgr.debug("delete file remotely: %s" % f)
    if delete_files:
        remote_delete_files(HOST, PORT, list(delete_files))


if __name__ == "__main__":
    setup_logging()
    main()
    # print "sleeping for 20s"
    time.sleep(5)
