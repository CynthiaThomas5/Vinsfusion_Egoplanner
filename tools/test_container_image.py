import copy
import unittest
from check_container_image import content_sha256, verify_image

class ContainerImageTests(unittest.TestCase):
    def setUp(self):
        self.image={'Id':'sha256:index','Architecture':'amd64','Os':'linux','Config':{'Env':['PATH=/bin'],'Cmd':['bash'],'User':''},'RootFS':{'Type':'layers','Layers':['sha256:a','sha256:b']}}
        self.runtime={'image':'fixed:tag','image_id':self.image['Id'],'image_content_sha256':content_sha256(self.image)}
    def test_transport_metadata_changes_preserve_identity(self):
        image=copy.deepcopy(self.image);image.update(Id='sha256:config',Descriptor=None,GraphDriver={'Name':'vfs'})
        self.assertEqual(verify_image(image,self.runtime)['content_sha256'],self.runtime['image_content_sha256'])
    def test_changed_layer_config_or_architecture_rejected(self):
        for field,value in [('RootFS',{'Type':'layers','Layers':['sha256:other']}),('Config',{'Env':['PATH=/evil']}),('Architecture','arm64')]:
            with self.subTest(field=field):
                image=copy.deepcopy(self.image);image[field]=value
                with self.assertRaises(ValueError):verify_image(image,self.runtime)
    def test_legacy_contract_still_requires_exact_id(self):
        runtime=dict(self.runtime);runtime.pop('image_content_sha256');image=dict(self.image);image['Id']='sha256:other'
        with self.assertRaises(ValueError):verify_image(image,runtime)
