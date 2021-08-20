import falcon
from wsgiref.simple_server import make_server
import ee
import datetime
import ast
import wget
import urllib
import json
import multiprocessing
pool = multiprocessing.Pool()

class getThumbs:
    ee.Initialize()
    def imageToThumb(self,img):
        imageThumb = ee.Image(img).getThumbURL({
            'name':img,
            'bands':['B6','B5','B4'],
            'min':0.03,
            'max':0.4,
            'maxDimension':[320,320],
            'region':self.geeGeometry.buffer(self.featureArea),
            'format ':'png'
        },)
        mapid = ee.Image(img).getMapId({'bands': ['B6','B5','B4'], 'min': 0.03, 'max': 0.4})
        return [imageThumb,mapid['tile_fetcher'].url_format]

    def on_post(self, req, resp):
        landsatList
        resp.status = falcon.HTTP_200 
        resp.media = quote

class getImageList:
    ee.Initialize()
    landsat8 = ee.ImageCollection("LANDSAT/LC08/C01/T1_TOA")
    EE_TILES = 'https://earthengine.googleapis.com/map/{mapid}/{{z}}/{{x}}/{{y}}?token={token}'
    geeGeometry = ''
    featureArea = 0
    
    def on_post(self, req, resp):
        """Handles POST requests"""
        resp.status = falcon.HTTP_200 
        #print(req.params['polygon'])
        polygon = json.loads(req.get_param('polygon',False)  or req.params['polygon'])  #get via GET or POST
        if(polygon != ''):
            self.geeGeometry = ee.Geometry.MultiPolygon(polygon['coordinates'],'EPSG:4326',True)
            self.featureArea = ee.Number(self.geeGeometry.area()).sqrt().getInfo()
            landsatList = self.landsat8.filterBounds(self.geeGeometry).aggregate_array('system:id').getInfo()
            #print(landsatList)
            #landsatList = list(map(self.imageToThumb,landsatList))
            resp.media = landsatList
        else:
            quote = {
                'quote': (
                    "I've always been more interested in "
                    "the future than in the past."
                ),
                'author': 'Grace Hopper'
            }
            resp.media = quote
api = falcon.API()
api.req_options.auto_parse_form_urlencoded = True #Enable POST parameters receive
ee.Initialize()
api.add_route('/getImageList', getImageList())
api.add_route('/getThumb', getThumbs())

if __name__ == '__main__':
    with make_server('', 9000, api) as httpd:
        print('Serving on port 9000...')

        # Serve until process is killed
        httpd.serve_forever()