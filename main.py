import falcon
from wsgiref.simple_server import make_server
import ee

from datetime import datetime,timedelta
import time
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
        eeMin = 0.02
        eeMax = 0.55
        gain = None
        gama = 1
        if("LANDSAT" in img):
            print('L8')
            eeimg = ee.Image(img).select([1,2,3,4,5,6,'BQA'],['blue','green','red','nir','swir1','swir2','BQA'])
            gain = None
            gama = 1.15
        if("S2_SR" in img):
            print('S2')
            eeimg = ee.Image(img).select([1,2,3,8,11,12],['blue','green','red','nir','swir1','swir2'])
            gain = None
            gama = 0.80
        if("S1_GRD" in img):
            print('S1')
            eeimg = ee.Image(img).select(['VH','VH','VH','VH','VH','VH'],['blue','green','red','nir','swir1','swir2'])
        if("S2" in img):
            # print("S2")
            eeMin = 0
            eeMax = 5000
        if(imageBands == 'ndvi,' and "S1_GRD" not in img):
            eeMin = 0.1
            eeMax = 0.8
            gain = None
            gama = 1
            if("S2_SR" in img):
                gain = None
                gama = 1
                eeMin = -0.15
                eeMax = 0.9
            imageBands = ['NDVI']
            eeimg = eeimg.normalizedDifference(['nir','red']).rename('NDVI')
        else:
            if(imageBands == 'red,green,blue'):
                eeMin = 0.04
                eeMax = 0.25
                if("S2" in img):
                    # print("S2")
                    eeMin = 415
                    eeMax = 1374
            imageBands = imageBands.split(',')
        if("S1_GRD" in img):
            # print("S1")
            eeMin = -29
            eeMax = -12
        
        visGeomR = ee.Image(0).toByte().paint(self.geeGeometry,255,4)
        visGeomG = ee.Image(0).toByte()
        visGeomB = ee.Image(0).toByte()
        imageGeom = ee.Image.rgb(visGeomR.rename('R'),visGeomG.rename('G'),visGeomB.rename('G')).updateMask(visGeomR.eq(255))
        
        geometryIMG = ee.Feature(self.geeGeometry).getMapId({'color':'red'})['image']


        if(self.featureArea < 800):
            self.featureArea = self.featureArea * 1.5
        #print('Area'+str(self.featureArea));
        print(eeMin)
        print(eeMax)
        print(gain)
        print(gama)
        imageThumb = eeimg.visualize(imageBands,gain,None,eeMin,eeMax,gama).blend(imageGeom)
        imageThumb = imageThumb.getThumbURL({
            'name':img,
            'bands':['vis-red','vis-green','vis-blue'],#imageBands,
            'min':0,
            'max':255,
            'dimensions':[320,320],
            'region':self.geeGeometry.centroid(1).buffer(self.featureArea).bounds(1),
            'format':'png'
        })

        mapid = eeimg.getMapId({'bands': imageBands, 'min': eeMin, 'max': eeMax,'gain':gain,'gamma':gama})
        date = ee.Image(img).get('DATE_ACQUIRED').getInfo()
        if("COPERNICUS" in img):
            date = datetime.fromtimestamp(ee.Image(img).get('system:time_start').getInfo()/1000).strftime("%Y-%m-%d")   
        return {'order':imageOrder,'thumb' : imageThumb, 'tile' : mapid['tile_fetcher'].url_format, 'imgID':img,'date':date}

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

    # def on_get(self, req, resp):
    #     imageName = req.get_param('image',False)
    #     polygon = json.loads(req.get_param('polygon',False)  or req.params['polygon'])  #get via GET or POST
    #     self.geeGeometry = ee.Geometry.MultiPolygon(polygon['coordinates'],'EPSG:4326',True)
    #     self.featureArea = ee.Number(self.geeGeometry.area()).sqrt().getInfo()
    #     self.imageToThumb(imageName) 
    #     resp.status = falcon.HTTP_200 
    #     resp.media = 'quote'

class getImageList:
    ee.Initialize()
    landsat8 = ee.ImageCollection("LANDSAT/LC08/C01/T1_TOA")
    sentinel2 = ee.ImageCollection("COPERNICUS/S2_SR")
    sentinel1 = ee.ImageCollection("COPERNICUS/S1_GRD")
    EE_TILES = 'https://earthengine.googleapis.com/map/{mapid}/{{z}}/{{x}}/{{y}}?token={token}'
    geeGeometry = ''
    featureArea = 0
    
    def on_post(self, req, resp):
        """Handles POST requests"""
        resp.status = falcon.HTTP_200 
        print(req.params)
        polygon = json.loads(req.get_param('polygon',False)  or req.params['polygon'])  #get via GET or POST
        satellite = req.get_param('satellite',False)  or req.params['satellite']
        dateAfter = req.get_param('date',False)  or req.params['date']
        dateBefore = (datetime.fromisoformat(dateAfter[:-1])  - timedelta(days=(1.5*365))).strftime("%Y-%m-%d")   
        dateAfter = (datetime.fromisoformat(dateAfter[:-1]) + timedelta(days=(60))).strftime("%Y-%m-%d")
        
        if(polygon != ''):
            self.geeGeometry = ee.Geometry.MultiPolygon(polygon['coordinates'],'EPSG:4326',True)
            self.featureArea = ee.Number(self.geeGeometry.area()).sqrt().getInfo()
            if('All' in satellite):
                landsatListL8 = self.landsat8.filterDate(dateBefore,dateAfter).filterBounds(self.geeGeometry).limit(30,'system:time_end',False).aggregate_array('system:id').getInfo()
                landsatListS2 = self.sentinel2.filterDate(dateBefore,dateAfter).filterBounds(self.geeGeometry).limit(30,'system:time_end',False).aggregate_array('system:id').getInfo()
                landsatListS1 = self.sentinel1.filterDate(dateBefore,dateAfter).filterBounds(self.geeGeometry).limit(30,'system:time_end',False).aggregate_array('system:id').getInfo()
                landsatList = [*landsatListL8,*landsatListS2,*landsatListS1]
            if('L8' in satellite):
                 landsatList = self.landsat8.filterDate(dateBefore,dateAfter).filterBounds(self.geeGeometry).limit(100,'system:time_end',False).aggregate_array('system:id').getInfo()
            if('S2' in satellite):
                landsatList = self.sentinel2.filterDate(dateBefore,dateAfter).filterBounds(self.geeGeometry).limit(100,'system:time_end',False).aggregate_array('system:id').getInfo()
            if('S1' in satellite):
                landsatList = self.sentinel1.filterDate(dateBefore,dateAfter).filterBounds(self.geeGeometry).limit(100,'system:time_end',False).aggregate_array('system:id').getInfo()
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