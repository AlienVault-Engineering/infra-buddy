import os
import tempfile

from infra_buddy_too.aws import s3 as s3util
from infra_buddy_too.aws.cloudformation import CloudFormationBuddy
from infra_buddy_too.aws.s3 import S3Buddy
from infra_buddy_too.deploy.deploy import Deploy
from infra_buddy_too.utility import print_utility


class S3Deploy(Deploy):
    def __init__(self, artifact_id, location, ctx):
        super(S3Deploy, self).__init__(ctx)
        self.location = location
        self.artifact_id = artifact_id
        self.cloud_formation_buddy = CloudFormationBuddy(self.deploy_ctx)
        if self.deploy_ctx.s3_deploy_bucket:
            self.destination_bucket = self.deploy_ctx.s3_deploy_bucket
        else:
            self.destination_bucket = \
                self.cloud_formation_buddy.get_export_value( param=self.deploy_ctx.s3_deploy_bucket_export)
        if not self.destination_bucket:
            print_utility.error("Could not find s3 deploy bucket")


    def _internal_deploy(self, dry_run):
        mkdtemp = tempfile.mkdtemp()
        if not self.artifact_id.endswith(".zip" ):
            self.artifact_id = "{}.zip".format(self.artifact_id)
        artifact_download = "s3://{location}/{artifact_id}".format(location=self.location,artifact_id=self.artifact_id)
        s3util.download_zip_from_s3_url(artifact_download,destination=mkdtemp)

        to_upload = self.get_filepaths(mkdtemp)
        if dry_run:
            print_utility.banner_warn("Dry Run: Uploading files to - {}".format( self.destination_bucket),
                                      str(to_upload))
        else:
            split = self.destination_bucket.split("/")
            if len(split)>1:
                path = "/".join(split[1:])
            else:
                path = ''
            s3 = S3Buddy(self.deploy_ctx, path, split[0])
            print_utility.progress("S3 Deploy: Uploading files to - {}".format( self.destination_bucket))
            for s3_key, path in to_upload.items():
                print_utility.info("{} - {}".format( self.destination_bucket, s3_key))
                s3.upload(key_name=s3_key, file=path)

    def get_filepaths(self, local_directory):
        rel_paths = {}
        for root, dirs, files in os.walk(local_directory):
            for filename in files:
                # construct the full local path
                local_path = os.path.join(root, filename)
                # construct the full Dropbox path
                relative_path = os.path.relpath(local_path, local_directory)
                # s3_path = os.path.join(destination, relative_path)
                rel_paths[relative_path] = local_path
        return rel_paths

    def __str__(self):
       return "{} - {}:{}".format(self.__class__.__name__,self.location,self.artifact_id)


