import falcon
from lib.connection import Conexao
import ee
import datetime
import ast
import wget
import urllib


class bridge:
    def on_get(self, req, resp):
        """Handles GET requests"""
        quote = {
            'quote': (
                "I've always been more interested in "
                "the future than in the past."
            ),
            'author': 'Grace Hopper'
        }

        resp.media = quote

api = falcon.API()
ee.Initialize()
api.add_route('/about', bridge())