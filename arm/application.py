""" An application is defined by a template file and a parameters
"""
import json
import os
import arm
from arm.resource_group import InstanceGroup
from arm.storage import InstanceStorage
import logging
from azure.mgmt.resource.resources.models import Deployment
from azure.mgmt.resource.resources.models import DeploymentProperties
from azure.mgmt.resource.resources.models import DeploymentMode

logger = logging.getLogger(__name__)

class Application(object):

    def __init__(   self, name, location, template_file,
                    parameters_file, packer_file):

        self.name=name
        self.location=location

        # Initialise the related resource group
        self.group = InstanceGroup(
            self.name,
            self.location
        )

        # Read parameters file
        with open(packer_file) as f:
            packer = json.load(f)

        with open(template_file) as f:
            self.template = json.load(f)

        with open(parameters_file) as f:
            self.parameters = json.load(f)

        pk_group = packer["packerGroup"]
        pk_storage = packer["packerStorage"]
        pk_container = packer["packerImagesContainer"]
        pk_folder = packer["packerImagesPath"]

        images_to_copy = set()
        for k,v in self.parameters["parameters"].iteritems():
            logger.debug("%s : %s" % (k,v["value"]))
            if k.endswith("Image"):
                images_to_copy.add( os.path.join(pk_folder, v["value"]) )

        image_storage = InstanceStorage(
                    pk_group,
                    create_if_not_exist=False
        )

        # Check if the images does not already exist in the application storage
        logger.debug("container : %s/%s" % (image_storage.name, pk_container))
        for blob in self.group.storage.blob.list_blobs(
                self.group.storage.sources_container,
                prefix=pk_folder):

            if blob in images_to_copy:
                logger.debug(str(blob) + " already exists")
                images_to_copy.remove(blob)

        # Launch the copies of the images to the application storage
        logger.debug("container : %s/%s" % (image_storage.name, pk_container))
        for blob in images_to_copy:
            self.group.storage.copy_source_images_from(
                image_storage,
                pk_container,
                blob
            )

    # Launch the deployment with deployment
    def deploy(self):
        # Befaore launching the deployment, the parameters has to be
        # completed with the newly created group


        parameters = self.parameters["parameters"]
        parameters["instanceName"] = { "value" : self.group.name }
        parameters["storage"] = {"value": "http://%s.blob.core.windows.net" % (
                                            self.group.storage.name) }
        parameters["imagesContainer"] = { "value":self.group.storage.sources_container }
        parameters["vhdContainer"] = {"value":self.group.storage.vhds_container}
        # FIXME
        parameters["environment"] = {"value": "dev"}

        rm = arm.instance().resource
        result = rm.deployments.create_or_update(
            self.group.name,
            "%s-deployment" % self.group.name,
            Deployment(
                properties=DeploymentProperties(
                    mode=DeploymentMode.incremental,
                    template=self.template,
                    parameters=parameters
                )
            )
        )
        res = result.result()
        logging.debug(res.__class__)

