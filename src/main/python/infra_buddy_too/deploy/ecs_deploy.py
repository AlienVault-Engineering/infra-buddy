from infra_buddy_too.aws.ecs import ECSBuddy
from infra_buddy_too.deploy.deploy import Deploy
from infra_buddy_too.utility import print_utility


class ECSDeploy(Deploy):
    def __init__(self, artifact_id, artifact_location, deploy_ctx):
        super(ECSDeploy, self).__init__(deploy_ctx)
        self.run_task = deploy_ctx.is_task_run_service()
        self.artifact_id = artifact_id
        self.artifact_location = artifact_location
        self.ecs_buddy = ECSBuddy(self.deploy_ctx, run_task=self.run_task)

    def _internal_deploy(self, dry_run):
        self.ecs_buddy.set_container_image(self.artifact_location, self.artifact_id)
        if dry_run:
            print_utility.warn(f"[Dry Run] ECS Deploy intends to: {self.ecs_buddy.what_is_your_plan()}")
            return None
        if self.ecs_buddy.requires_update():
            if not self.ecs_buddy.perform_update():
                print_utility.error(f"Failed to: {self.ecs_buddy.what_is_your_plan()}",raise_exception=True)
            print_utility.progress(self.ecs_buddy.what_is_your_plan())
            return True
        else:
            print_utility.progress(f"ECS does not require update - {self.artifact_location}:{self.artifact_id}")
            return False

    def __str__(self):
        return f"{self.__class__.__name__} - {self.artifact_location}:{self.artifact_id}"
