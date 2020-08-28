import os

def run(params, path, dirs, files, logger=None):
    """
    @param string path
    @param [] dirs
    @param [] files
    @return (dirs, files)
    """

    most_recent_x = params.get('pick', None)

    # only get most recent files
    if most_recent_x and len(files) > 0:
        mtime_fname_l = []
        for e in files:
            mtime_fname_l.append((os.path.getmtime(e), e))
        mtime_fname_l.sort(reverse=True)
        # for e in mtime_fname_l:
        #     print e
        files = set(zip(*(mtime_fname_l[:most_recent_x]))[1])

    return dirs, files
