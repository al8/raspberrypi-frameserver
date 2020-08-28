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

from plugins import \
    filter_picasa, \
    filter_hash, \
    filter_recent, \
    filter_regex

def set_params(params):
    global g_params
    g_params = params

def setup_logging():
    global g_lgr
    logfilename = os.path.join(tempfile.gettempdir(), "sync_all.log")

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

    return g_lgr

transfer_params_t = namedtuple(
    "transfer_params_t", [
        "path",
        "local_filters",
        "global_filters",
    ]
)

def get_dirs_files(path, local_filters):
    items = os.listdir(path)
    fullitems = map(lambda p: os.path.join(path, p), items)  # full path

    # split between dirs and files
    dirs = filter(os.path.isdir, fullitems)
    files = filter(os.path.isfile, fullitems)

    # per path filters e.g. filter_picasa
    if local_filters:
        for f_params in local_filters:
            if isinstance(f_params, tuple):
                f, params = f_params
            else:
                f, params = f_params, None
            dirs, files = f.run(params, path, dirs, files, g_lgr)

    return dirs, files

def get_files(transfer_param, path_override=None):
    # gather viable image files into this set
    files = set()

    if path_override is None:
        path = transfer_param.path
    else:
        path = path_override

    p_dirs, p_files = get_dirs_files(
        path,
        transfer_param.local_filters)

    # log debug information
    logger = g_lgr.debug # if len(p_dirs) == 0 and len(p_files) == 0 else g_lgr.info
    logger("dirs:%d files:%d path: \"%s\"" % (
            len(p_dirs),
            len(p_files),
            os.path.basename(path),
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

    # process filters like filter_recent, filter_hash
    if transfer_param.global_filters:
        for f_params in transfer_param.global_filters:
            if isinstance(f_params, tuple):
                f, params = f_params
            else:
                f, params = f_params, None
            _, files = f.run(params, None, None, files, g_lgr)

    return files

def copy_resize_rotate(files, output_path):
    """
    resize and rotate files
    returns resized files and would be resized files
    """
    new_files = set()  # new files to be copied over
    not_new_files = set()
    cnt_skip = 0
    cnt_convert = 0
    dst_size = g_params.get("output_jpg_size", 2048)
    for idx, f in enumerate(sorted(files)):
        src, dst = f, os.path.join(output_path, os.path.basename(f))

        # if file already exists, then don't resize, and don't add to new_files set
        if os.path.isfile(dst):
            g_lgr.debug("skipping file '%s' because dst:'%s' already exists" % (src, dst))
            cnt_skip += 1
            not_new_files.add(dst)
            continue

        if not src.lower().endswith("jpg"):
            g_lgr.error("skipping file '%s' because it is not a jpeg!!!" % (src))
            continue

        args = [
            g_params["imagemagick_convert_binary"],
            src,
            "-quality",
            str(g_params.get("output_jpg_quality", 55)),
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

        if g_params["jhead_binary"]:
            args = [
                g_params["jhead_binary"],
                "-autorot",
                dst,
            ]
            g_lgr.debug("auto rotate file '%s'" % (dst))
            g_lgr.debug(" ".join(args))
            try:
                subprocess.check_output(
                    args,
                    stderr=subprocess.STDOUT,
                    cwd=os.path.dirname(g_params["jhead_binary"]),
                )
                new_files.add(dst)
            except subprocess.CalledProcessError as ex:
                g_lgr.warning("removing file that could not be rotated %s" % dst)
                g_lgr.error(traceback.format_exc())
                try:
                    os.remove(dst)
                except:
                    pass

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
        dst = "pi@%s:photos/%s" % (g_params["PI-HOST"], os.path.basename(f).lower())
        args = g_params["scp_cmdline"] + [src, dst]
        g_lgr.info("uploading file '%s' to '%s' (%d of %d)" % (os.path.basename(src), dst, idx + 1, len(files)))
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

if __name__ == "__main__":
    pass
