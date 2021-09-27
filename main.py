import falcon
from wsgiref.simple_server import make_server
import ee
import datetime
import ast
from pyasn1.type.univ import Null
import wget
import urllib
import json
import multiprocessing
pool = multiprocessing.Pool()

class getThumbs:
    ee.Initialize()
    geeGeometry = ''
    featureArea = 0
    def imageToThumb(self,img,imageBands,imageOrder):
        eeMin = 0.03
        eeMax = 0.4
        eeimg = ee.Image(img).select([1,2,3,4,5,6,'BQA'],['blue','green','red','nir','swir1','swir2','BQA'])
        if(imageBands == 'ndvi,'):
            eeMin = 0.1
            eeMax = 0.9
            imageBands = ['NDVI']
            eeimg = eeimg.normalizedDifference(['nir','red']).rename('NDVI')
        else:
            if(imageBands == 'red,green,blue'):
                eeMin = 0.05
                eeMax = 0.12
            imageBands = imageBands.split(',')
        
        visGeomR = ee.Image(0).toByte().paint(self.geeGeometry,255,4)
        visGeomG = ee.Image(0).toByte()
        visGeomB = ee.Image(0).toByte()
        imageGeom = ee.Image.rgb(visGeomR.rename('R'),visGeomG.rename('G'),visGeomB.rename('G')).updateMask(visGeomR.eq(255))
        
        geometryIMG = ee.Feature(self.geeGeometry).getMapId({'color':'red'})['image']


        if(self.featureArea < 800):
            self.featureArea = self.featureArea * 1.5
        #print('Area'+str(self.featureArea));
        imageThumb = eeimg.visualize(imageBands,None,None,eeMin,eeMax).blend(imageGeom)
        imageThumb = imageThumb.getThumbURL({
            'name':img,
            'bands':['vis-red','vis-green','vis-blue'],#imageBands,
            'min':0,
            'max':255,
            'dimensions':[320,320],
            'region':self.geeGeometry.centroid(1).buffer(self.featureArea).bounds(1),
            'format':'png'
        })

        mapid = eeimg.getMapId({'bands': imageBands, 'min': eeMin, 'max': eeMax})
        return {'order':imageOrder,'thumb' : imageThumb, 'tile' : mapid['tile_fetcher'].url_format, 'imgID':img,'date':ee.Image(img).get('DATE_ACQUIRED').getInfo()}

    def on_post(self, req, resp):
        imageName = req.get_param('image',False)
        imageOrder = req.get_param('order',False)
        imageBands =  req.get_param('bands',False)
        polygon = json.loads(req.get_param('polygon',False)  or req.params['polygon'])  #get via GET or POST
        self.geeGeometry = ee.Geometry.MultiPolygon(polygon['coordinates'],'EPSG:4326',True)
        self.featureArea = ee.Number(self.geeGeometry.area()).sqrt().getInfo()*2.5
        imageThumbLink = self.imageToThumb(imageName,imageBands,imageOrder) 
        resp.status = falcon.HTTP_200 
        resp.media = imageThumbLink

    def on_get(self, req, resp):
        imageName = req.get_param('image',False)
        polygon = json.loads(req.get_param('polygon',False)  or req.params['polygon'])  #get via GET or POST
        self.geeGeometry = ee.Geometry.MultiPolygon(polygon['coordinates'],'EPSG:4326',True)
        self.featureArea = ee.Number(self.geeGeometry.area()).sqrt().getInfo()
        self.imageToThumb(imageName) 
        resp.status = falcon.HTTP_200 
        resp.media = 'quote'

class getImageList:
    ee.Initialize()
    landsat8 = ee.ImageCollection("LANDSAT/LC08/C01/T1_TOA")
    EE_TILES = 'https://earthengine.googleapis.com/map/{mapid}/{{z}}/{{x}}/{{y}}?token={token}'
    geeGeometry = ''
    featureArea = 0
    
    def on_post(self, req, resp):
        """Handles POST requests"""
        resp.status = falcon.HTTP_200 
        print(req.params)
        polygon = json.loads(req.get_param('polygon',False)  or req.params['polygon'])  #get via GET or POST
        if(polygon != ''):
            self.geeGeometry = ee.Geometry.MultiPolygon(polygon['coordinates'],'EPSG:4326',True)
            self.featureArea = ee.Number(self.geeGeometry.area()).sqrt().getInfo()
            landsatList = self.landsat8.filterDate('2019-01-01','2030-01-01').filterBounds(self.geeGeometry).limit(25,'system:time_end',False).aggregate_array('system:id').getInfo()
            print(landsatList)
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
#api = falcon.API()
api = falcon.App(cors_enable=True)
api.req_options.auto_parse_form_urlencoded = True #Enable POST parameters receive
ee.Initialize()
api.add_route('/getImageList', getImageList())
api.add_route('/getThumb', getThumbs())

if __name__ == '__main__':
    with make_server('', 9000, api) as httpd:
        print('Serving on port 9000...')

        # Serve until process is killed
        httpd.serve_forever()