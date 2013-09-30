import time
import zlib

def run(params, path, dirs, files, logger=None):
    """
    @param string path
    @param [] dirs
    @param [] files
    @return (dirs, files)
    """

    hash_x = params.get('pick', None)

    # get a 'random' selection of files
    if hash_x and len(files) > 0:
        ### configure hash slicing here
        interval_min = params.get("interval", 20)  # different every 20 minutes / slices
        slices = params.get("slices", 4)  # split the interval into this many slices
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

    return dirs, files
