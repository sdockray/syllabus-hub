# -*- coding: utf-8 -*-
import os

import cherrypy
import gitlab
import markdown2
from itsdangerous import Signer

SERVER = 'http://grr.aaaaarg.fail:9090'
PRIVATE_TOKEN = 'wPXof4gFWNMEMS4CycRr'
TMPL = """
<!doctype html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>%s</title>
    <link rel="stylesheet" href="http://yui.yahooapis.com/pure/0.6.0/pure-min.css">
    <style>
    #layout {
        padding: 2em;
        color: black;
    }
    </style>
</head>
<body>
<div id="layout">
    %s
</div>
</body>
</html>
"""

def html(content, title):
    return TMPL % (title, markdown2.markdown(content))

"""
Non-project Gitlab API interaction
"""
class Git(object):
    def __init__(self, *args, **kwargs):
        self.gl = gitlab.Gitlab(SERVER, token=PRIVATE_TOKEN)

"""
Interfaces with Gitlab API for a project
"""
class Project(Git):
    def __init__(self, project_id):
        super(Project, self).__init__()
        self.project = self.gl.getproject(project_id)

    def get_content(self, file_name='README.md', branch='master'):
        return self.gl.getrawfile(self.project['id'], branch, file_name)

    def get_title(self):
        return self.project['name_with_namespace']

"""
CherryPy resource handling
"""
class SyllabusServer(object):

    @cherrypy.expose
    def default(self, *args, **kwargs):
        if len(args)<2:
            return 'Error'
        project_id = "%s/%s" % (args[0], args[1])
        p = Project(project_id)
        if len(args)==2:
            return html(p.get_content(), p.get_title())
        if args[2]=='edit':
            pass

    @cherrypy.expose
    def register(self, *args, **kwargs):
        pass

    @cherrypy.expose
    def login(self, *args, **kwargs):
        pass

    @cherrypy.expose
    def create(self, *args, **kwargs):
        pass

    def view(self, project_id):
        pass

    @cherrypy.expose
    def edit(self, *args, **kwargs):
        pass

    @cherrypy.expose
    def fork(self, *args, **kwargs):
        pass


# Starting things up
if __name__ == '__main__':
	try:
		cherrypy.config.update({
			'server.socket_port': 8101,
		})
		app = cherrypy.tree.mount(SyllabusServer(), '/', 'app.conf')
		cherrypy.quickstart(app)
	except:
		print "Survey server couldn't start :("