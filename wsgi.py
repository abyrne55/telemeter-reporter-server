import os
from collections import OrderedDict
from datetime import datetime
from string import Template

from htmlmin.middleware import HTMLMinMiddleware

# Load path from environment
if os.getenv('TELEMETER_REPORTER_SERVER_ROOT'):
    REPORTS_ROOT = os.path.abspath(os.getenv('TELEMETER_REPORTER_SERVER_ROOT'))
else:
    REPORTS_ROOT = "./reports/"


def http_403(env, start_response):
    start_response('403 Forbidden', [('Content-Type', 'text/html')])
    return ['<h1>Error 403: Forbidden</h1>\n'.encode('utf-8')]


def http_404(env, start_response):
    start_response('404 Not Found', [('Content-Type', 'text/html')])
    return ['<h1>Error 404: Page Not Found</h1>\n'.encode('utf-8')]


def index(env, start_response):
    with open("html/index.html", 'r') as f:
        index_template = f.read()

    file_dict = {}

    # Scan reports dir for file
    for entry in os.scandir(os.fsencode(REPORTS_ROOT)):
        if entry.is_dir():
            try:
                # This call to strptime will throw ValueError if entry is not properly named

                datetime.strptime(os.fsdecode(entry.name), "%Y-%m")
                for subentry in os.scandir(os.fsencode(entry.path)):
                    if subentry.is_file() and os.fsdecode(subentry.name).endswith(".html"):
                        dirname = os.fsdecode(entry.name)
                        filename = os.fsdecode(subentry.name)
                        try:
                            file_dict[dirname].append(filename)
                        except KeyError:
                            file_dict[dirname] = [filename]
            except ValueError:
                pass

    # Sort the dict
    file_dict = OrderedDict(sorted(file_dict.items(), key=lambda t: t[0], reverse=True))

    file_index = ""
    for month, files in file_dict.items():
        month_str = datetime.strptime(month, "%Y-%m").strftime("%B %Y")
        file_index += "<h2>{}</h2>\n<ul>\n".format(month_str)
        files.sort(reverse=True)
        for file in files:
            path_no_ext = "/reports/{}/{}".format(month, file.rsplit('.', 1)[0])
            file_index += "\t<li><a href='{0}.html'>{1}</a> (<a href='{0}.csv'>csv</a>)</li>\n".format(
                path_no_ext, file)
        file_index += "</ul>\n"

    start_response('200 OK', [('Content-Type', 'text/html')])
    return [Template(index_template).safe_substitute(title='Foo', body=file_index).encode('utf-8')]


def latest(env, start_response):
    # Scan reports dir for newest file
    newest_file_name = ""
    newest_file_ctime = 0
    for entry in os.scandir(os.fsencode(REPORTS_ROOT)):
        if entry.is_dir():
            try:
                # This call to strptime will throw ValueError if entry is not properly named
                datetime.strptime(os.fsdecode(entry.name), "%Y-%m")
                for subentry in os.scandir(os.fsencode(entry.path)):
                    if subentry.is_file() and os.fsdecode(subentry.name).endswith(".html"):
                        if subentry.stat().st_ctime > newest_file_ctime:
                            newest_file_ctime = subentry.stat().st_ctime
                            newest_file_name = "{}/{}".format(os.fsdecode(entry.name),
                                                              os.fsdecode(subentry.name))
            except ValueError:
                pass
    start_response('302 Found', [('Location', '/reports/' + newest_file_name)])
    return []


def reports(env, start_response):
    # Security/sanity check
    if ".." in env['PATH_INFO'] or len(env['PATH_INFO'].split('/')) != 4:
        return http_403(env, start_response)

    subpath = os.path.join(REPORTS_ROOT, *env['PATH_INFO'].split('/')[2:])
    if os.path.isfile(subpath):
        if subpath.endswith(".html"):
            with open(subpath, 'r') as f:
                start_response('200 OK', [('Content-Type', 'text/html')])
                return [f.read().encode('utf-8')]
        elif subpath.endswith(".csv"):
            with open(subpath, 'r') as f:
                start_response('200 OK', [('Content-Type', 'text/csv'), (
                    "Content-Disposition", "attachment;filename=" + os.path.basename(subpath))])
                return [f.read().encode('utf-8')]

    return http_404(env, start_response)


ROUTES = {'': index, 'index': index, 'reports': reports, 'latest': latest}


def application(env, start_response):
    path = env['PATH_INFO'].split('/')[1:]
    try:
        return HTMLMinMiddleware(ROUTES[path[0]](env, start_response), remove_comments=True,
                                 remove_empty_space=True)
    except KeyError:
        return http_404(env, start_response)
