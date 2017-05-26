import os
import requests
import logging
import argparse
import xml.etree.ElementTree as ET
import cherrypy
import share_unshare_libraries as plexlib
from helpers.utils import logger
import app_setup
from config import appconfig
import sys
from helpers import plex


_logger = logger.configure_logging(__name__, level='INFO')
_args = None
plex_config = None

libraries = {}
shared_servers = None


def get_libraries():
    global libraries
    url = 'https://plex.tv/api/servers/%s' % plex_config['server_id']
    r = requests.get(url, headers=appconfig.plex_headers)
    xml = ET.fromstring(r.text)
    sections = [{'id': int(i.get('id')), 'title': i.get('title')} for i in xml.iter('Section')]
    libraries['sections'] = sections

class PlexUtil(object):

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def get_shared_servers(self):
        global libraries, shared_servers
        get_libraries()
        url = appconfig.plex_shared_servers_url % plex_config['server_id']
        r = requests.get(url, headers=appconfig.plex_headers)
        xml = ET.fromstring(r.text)
        shared_servers = []
        for ss in xml.iter('SharedServer'):
            user = {}
            library_sections = []
            for s in ss.iter('Section'):
                if bool(int(s.get('shared'))):
                    library_sections.append(int(s.get('id')))
            user[int(ss.get('userID'))] = library_sections
            shared_servers.append(user)
        libraries['shared_servers'] = shared_servers
        return libraries

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def get_users(self):
        url = appconfig.plex_users_url
        r = requests.get(url, headers=appconfig.plex_headers)
        xml = ET.fromstring(r.text)
        xml_users = xml.findall('User')
        users = []
        for u in xml_users:
            user = {
                'id': int(u.get('id')),
                'username': u.get('username'),
                'title': u.get('title'),
                'email': u.get('email'),
                'thumb': u.get('thumb')
            }
            users.append(user)
        return users

    @cherrypy.expose
    @cherrypy.tools.json_in()
    @cherrypy.tools.json_out()
    def save_shared_servers(self):
        data = cherrypy.request.json
        print(data)
        if bool(data['share']) and bool(data['unshare']):
            plexlib.share(data['share'], appconfig.plex_server_id, appconfig.plex_token)
            plexlib.unshare(data['unshare'], appconfig.plex_server_id, appconfig.plex_token)
        elif bool(data['share']):
            plexlib.share(data['share'], appconfig.plex_server_id, appconfig.plex_token)
        elif bool(data['unshare']):
            plexlib.unshare(data['unshare'], appconfig.plex_server_id, appconfig.plex_token)
        else:
            pass

def plex_util():
    global plex_config
    # Authenticate to plex
    try:
        plex.authenticate()
    except Exception as e:
        sys.exit(1)

    plex_config = plex.load_plex_config()

    cherrypy.config.update({'server.socket_host': '0.0.0.0'})
    cherrypy.quickstart(PlexUtil(), '/', {
        '/': {
            'tools.staticdir.root': os.path.abspath(os.path.join(__file__, '..', 'html')),
            'tools.staticdir.on': True,
            'tools.staticdir.dir': '',
            'tools.staticdir.index': 'index.html'
        }
    })

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='Turn on verbose logging', dest='v')
    parser.add_argument('--setup', action='store_true', dest='setup',
                        help='Run the initial setup for the application '
                             '(required before first use)')
    parser.add_argument('--test', action='store_true', dest='test',
                        help='Enable test mode')
    _args = parser.parse_args()

    if _args.v:
        _logger.setLevel(logging.DEBUG)

    if _args.setup:
        app_setup.run_setup(_args)
    else:
        plex_util()


if __name__ == '__main__':
    main()