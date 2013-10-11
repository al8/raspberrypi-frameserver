import ConfigParser
import os

g_path_config_map = {}  # key = path, value = parsed picasa config

def _getconfig(path):
    """
    @param string path
    @returns config object or None
    """
    if path in g_path_config_map:
        return g_path_config_map[path]

    picasa_ini = os.path.join(path, '.picasa.ini')
    if not os.path.isfile(picasa_ini):
        g_path_config_map[path] = None
        return None

    config = ConfigParser.ConfigParser()
    config.read(picasa_ini)
    g_path_config_map[path] = config
    return config

def run(params, path, dirs, files, logger=None):
    """
    @param string path
    @param [] dirs
    @param [] files
    @return (dirs, files)
    """
    picasa_ini = os.path.join(path, '.picasa.ini')
    config = _getconfig(path)
    if config is None:
        return dirs, []

    star_files = set()
    cnt_suppressed = 0
    for s in config.sections():
        if logger: logger.debug("%s %s %s" % (s, config.items(s), ('suppress', 'yes') in config.items(s)))
        if ('suppress', 'yes') in config.items(s):  # "Block from Uploading" flag in picasa
            cnt_suppressed += 1
            continue
        if logger: logger.debug("%s %s %s" % (s, config.items(s), ('star', 'yes') in config.items(s)))
        if ('star', 'yes') in config.items(s):
            star_files.add(s.lower())
    # meta["pre_starred_filter"] = len(files)
    files = filter(lambda e: os.path.basename(e).lower() in star_files, files)
    if logger and (len(files) > 0 or cnt_suppressed > 0):
        str_suppressed = (", %d files suppressed" % cnt_suppressed) if cnt_suppressed else ""
        logger.debug("picasa_ini filter: %d files starred%s, %d left in \"%s\"" % (len(star_files), str_suppressed, len(files), os.path.basename(path)))
    return dirs, files
