import os
import tempfile

from infra_buddy.aws import s3 as s3util
from infra_buddy.aws.cloudformation import CloudFormationBuddy
from infra_buddy.aws.s3 import S3Buddy
from infra_buddy.deploy.deploy import Deploy
from infra_buddy.utility import print_utility


class S3Deploy(Deploy):
    def __init__(self, artifact_id, location, ctx):
        super(S3Deploy, self).__init__(ctx)
        self.location = location
        self.artifact_id = artifact_id

    def _internal_deploy(self,dry_run):
        mkdtemp = tempfile.mkdtemp()
        artifact_download = "s3://{location}/{artifact_id}.zip"
        destination_bucket = CloudFormationBuddy(self.deploy_ctx).get_export_value(param="WWW-Files")
        s3util.download_zip_from_s3_url(artifact_download.format(location=self.location,
                                                   artifact_id=self.artifact_id),
                                    destination=mkdtemp)

        to_upload = self.get_filepaths(mkdtemp)
        if dry_run:
            print_utility.banner_warn("Dry Run: Uploading files to - {}".format(destination_bucket),
                                      str(to_upload))
        else:
            s3 = S3Buddy(self.deploy_ctx,'',destination_bucket)
            print_utility.info("Uploading files to - {}".format(destination_bucket))
            for s3_key,path in to_upload.iteritems():
                print_utility.info("{} - {}".format(destination_bucket,s3_key))
                s3.upload(key_name=s3_key, file=path)

    def get_filepaths(self,local_directory):
        rel_paths= {}
        for root, dirs, files in os.walk(local_directory):
          for filename in files:
            # construct the full local path
            local_path = os.path.join(root, filename)
            # construct the full Dropbox path
            relative_path = os.path.relpath(local_path, local_directory)
            # s3_path = os.path.join(destination, relative_path)
            rel_paths[relative_path] = local_path
        return rel_paths
        
#
#  react-build-artifacts/react/web/web-dist-200.zip
# set -e
# WEB_DIST_SOURCENAME=$(cat web-dist.txt)
# ENVIRONMENT=${bamboo.deploy.environment}
# aws s3 cp s3://${WEB_DIST_SOURCENAME} .
# FILE=$(basename ${WEB_DIST_SOURCENAME})
# unzip ${FILE}
# cd dist
# aws s3 sync . s3://${ENVIRONMENT}-www-files