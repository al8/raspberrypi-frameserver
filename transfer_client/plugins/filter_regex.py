import os
import re

def run(params, path, dirs, files, logger=None):
    """
    @param string path
    @param [] dirs
    @param [] files
    @return (dirs, files)
    """

    directory_re = params.get('dir', None)
    filename_re = params.get('file', None)

    # regex match filter

    if directory_re:
        dirs = filter(
            lambda e:
                re.match(
                    directory_re,
                    os.path.basename(e),
                    re.IGNORECASE),
            dirs)
    if filename_re:
        files = filter(
            lambda e:
                re.match(
                    filename_re,
                    os.path.basename(e),
                    re.IGNORECASE),
            files)

    return dirs, files
