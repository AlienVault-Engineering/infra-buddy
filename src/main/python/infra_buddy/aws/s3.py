import os

import boto3
import botocore

from infra_buddy.utility import print_utility


class S3Buddy(object):
    def __init__(self, deploy_ctx):
        super(S3Buddy, self).__init__()
        self.deploy_ctx = deploy_ctx
        self.s3 = boto3.resource('s3', region_name=self.deploy_ctx.region)
        self.cf_bucket = self.s3.Bucket(deploy_ctx.cf_bucket_name)
        try:
            self.cf_bucket.create(CreateBucketConfiguration={'LocationConstraint': self.deploy_ctx.region})
        except (botocore.exceptions.ValidationError, botocore.exceptions.ClientError) as err:
            pass
        self.url_base = deploy_ctx.cf_bucket_url
        self.s3_bucket_deploy_directory = deploy_ctx.cf_deploy_resource_path

    def upload(self, file, file_name=None):
        key_name = self._get_upload_bucket_key_name(file, file_name)
        self.cf_bucket.put_object(Key=key_name, Body=open(file, 'rb'))
        print_utility.info("Uploaded file to S3 - Bucket: {} Key: {}".format(self.cf_bucket, key_name))
        return "{}/{}".format(self.url_base, key_name)

    def _get_upload_bucket_key_name(self, file, file_name):
        key_name = "{path}/{key_name}".format(path=self.s3_bucket_deploy_directory,
                                              key_name=(file_name if file_name else os.path.basename(file)))
        return key_name

    def get_file_as_string(self, filename):
        key_name = self._get_upload_bucket_key_name(file=None,file_name=filename)
        return self.s3.meta.client.get_object(Bucket=self.deploy_ctx.cf_bucket_name,Key=key_name)['Body'].read()


def download_zip_from_s3_url(s3_url):
    return None