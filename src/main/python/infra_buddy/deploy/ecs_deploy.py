from infra_buddy.aws.ecs import ECSBuddy
from infra_buddy.deploy.deploy import Deploy
from infra_buddy.utility import print_utility


class ECSDeploy(Deploy):
    def __init__(self, artifact_id, artifact_location, deploy_ctx):
        super(ECSDeploy, self).__init__(deploy_ctx)
        self.artifact_id = artifact_id
        self.artifact_location = artifact_location
        self.ecs_buddy = ECSBuddy(self.deploy_ctx)

    def _internal_deploy(self, dry_run):
        self.ecs_buddy.set_container_image(self.artifact_location, self.artifact_id)
        if dry_run:
            print_utility.warn("ECS Deploy would update service {} to use image {}".format(self.ecs_buddy.ecs_service,
                                                                                           self.ecs_buddy.new_image))
            return None
        if self.ecs_buddy.requires_update():
            self.ecs_buddy.perform_update()

            print_utility.progress("ECS Deploy updated service {} to use image {}".format(self.ecs_buddy.ecs_service,
                                                                                           self.ecs_buddy.new_image))
            return True
        else:
            print_utility.progress("ECS already using image - "
                               "{artifact_location}:{artifact_id}".
                               format(artifact_location=self.artifact_location,
                                      artifact_id=self.artifact_id))
            return False

    def __str__(self):
       return "{} - {}:{}".format(self.__class__.__name__,self.artifact_location,self.artifact_id)


